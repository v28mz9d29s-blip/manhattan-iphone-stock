import json
from pathlib import Path
import tempfile
import unittest
import io
from unittest.mock import patch
from urllib.error import HTTPError
import monitor as m


def fixture():
    return {'head': {'status': '200'}, 'body': {'stores': [
        {'storeNumber': sid, 'storeName': sid, 'partsAvailability': {m.PART: {
            'pickupDisplay': 'unavailable', 'pickupSearchQuote': 'Currently unavailable',
            'messageTypes': {'regular': {'storePickupProductTitle': m.PRODUCT}}}}}
        for sid in sorted(m.STORES)]}}


class MonitorTests(unittest.TestCase):
    def test_alert_routes_to_verified_github_recipient(self):
        with patch.dict(m.os.environ, {'GITHUB_TOKEN': 'test-token', 'GITHUB_REPOSITORY': 'v28mz9d29s-blip/manhattan-iphone-stock', 'NOTIFY_LOGIN': 'v28mz9d29s-blip'}):
            with patch.object(m.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"html_url":"https://github.com/example/issue"}')) as send:
                m.notify('TEST', 'Test only')
                request = send.call_args.args[0]
                self.assertEqual(request.full_url, 'https://api.github.com/repos/v28mz9d29s-blip/manhattan-iphone-stock/issues')
                payload = json.loads(request.data)
                self.assertTrue(payload['body'].startswith('@v28mz9d29s-blip\n'))
                self.assertNotIn('test-token', request.data.decode())

    def test_exact_configuration_and_coverage(self):
        d = fixture()
        self.assertEqual(len(m.parse_inventory(d)), 7)
        d['body']['stores'][0]['partsAvailability'][m.PART]['messageTypes']['regular']['storePickupProductTitle'] = 'iPhone Duo 512GB Star White'
        with self.assertRaises(ValueError): m.parse_inventory(d)
        d = fixture();d['body']['stores'].pop()
        with self.assertRaises(ValueError): m.parse_inventory(d)

    def test_unknown_is_not_unavailable(self):
        d = fixture();d['body']['stores'][0]['partsAvailability'][m.PART]['pickupDisplay'] = 'unknown'
        with self.assertRaises(ValueError): m.parse_inventory(d)
        with self.assertRaises(ValueError): m.parse_inventory({})

    def test_dedup_and_restock(self):
        self.assertEqual(len(m.newly_available({}, {'a': {'available': True}})), 1)
        self.assertEqual(m.newly_available({'a': {'available': True}}, {'a': {'available': True}}), [])
        self.assertEqual(len(m.newly_available({'a': {'available': False}}, {'a': {'available': True}})), 1)

    def test_delivery_failure_retries_stock(self):
        d = m.parse_inventory(fixture());d[next(iter(d))]['available'] = True
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'state.json'
            with patch.object(m, 'inventory', return_value=d), patch.object(m, 'notify', side_effect=RuntimeError('delivery failed')):
                with self.assertRaises(RuntimeError): m.run(p, 100000)
                self.assertFalse(p.exists())

    def test_failure_preserves_stock_and_backs_off(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'state.json'; m.save(p, {'stores': {'old': {'available': True}}})
            with patch.object(m, 'inventory', side_effect=HTTPError('https://www.apple.com',429,'limited',{'Retry-After':'1800'},None)), patch.object(m, 'notify') as alert:
                self.assertEqual(m.run(p, 100000), 0)
                alert.assert_not_called()
                state = json.loads(p.read_text())
                self.assertEqual(state['next_attempt'], 101800)
                self.assertTrue(state['stores']['old']['available'])
                self.assertEqual(m.run(p, 100300), 0)


    def test_no_stock_and_recovery_are_silent(self):
        current = m.parse_inventory(fixture())
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'state.json'
            m.save(p, {'failures': 2, 'stores': current})
            with patch.object(m, 'inventory', return_value=current), patch.object(m, 'notify') as alert:
                self.assertEqual(m.run(p, 200000), 0)
                self.assertEqual(m.run(p, 200300), 0)
                alert.assert_not_called()

    def test_stock_alert_once_until_observed_restock(self):
        current = m.parse_inventory(fixture())
        sid = next(iter(current))
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'state.json'
            with patch.object(m, 'inventory', side_effect=lambda: current), patch.object(m, 'notify') as alert:
                m.run(p, 200000)
                alert.assert_not_called()
                current[sid]['available'] = True
                m.run(p, 200300)
                m.run(p, 200600)
                self.assertEqual(alert.call_count, 1)
                self.assertEqual(alert.call_args.args[0], 'iPhone Duo available in Manhattan')
                current[sid]['available'] = False
                m.run(p, 200900)
                current[sid]['available'] = True
                m.run(p, 201200)
                self.assertEqual(alert.call_count, 2)


if __name__ == '__main__': unittest.main()
