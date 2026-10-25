import json
from pathlib import Path
import tempfile
import unittest
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
            with patch.object(m, 'inventory', side_effect=HTTPError('https://www.apple.com',429,'limited',{'Retry-After':'1800'},None)), patch.object(m, 'notify'):
                self.assertEqual(m.run(p, 100000), 1)
                state = json.loads(p.read_text())
                self.assertEqual(state['next_attempt'], 101800)
                self.assertTrue(state['stores']['old']['available'])
                self.assertEqual(m.run(p, 100300), 0)


if __name__ == '__main__': unittest.main()
