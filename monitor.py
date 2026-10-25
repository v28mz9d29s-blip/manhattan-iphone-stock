"""A stock checker using Python's standard library; no AI calls or API key."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

PRODUCT = 'iPhone Duo 256GB Star White'
PART = 'MK1E4LL/A'
BUY = 'https://www.apple.com/shop/buy-iphone/iphone-duo/7.6-inch-display-256gb-star-white-unlocked'
STORES = {'R582', 'R251', 'R095', 'R415', 'R250', 'R032', 'R654'}
ENDPOINT = 'https://www.apple.com/shop/retail/pickup-message'


def parse_inventory(data):
    if str(data.get('head', {}).get('status')) != '200':
        raise ValueError('Apple returned an unsuccessful inventory response')
    body = data.get('body', {})
    stores = body.get('stores', body.get('content', {}).get('pickupMessage', {}).get('stores'))
    if not isinstance(stores, list):
        raise ValueError('Apple inventory schema changed')
    result = {}
    for store in stores:
        sid = store.get('storeNumber')
        if sid not in STORES:
            continue
        part = store.get('partsAvailability', {}).get(PART, {})
        regular = part.get('messageTypes', {}).get('regular', {})
        if regular.get('storePickupProductTitle') != PRODUCT:
            raise ValueError('Unexpected product or missing product title')
        if part.get('pickupDisplay') not in ('available', 'unavailable'):
            raise ValueError('Unknown pickup status at ' + store.get('storeName', sid))
        result[sid] = dict(name=store['storeName'], available=part['pickupDisplay'] == 'available',
                           quote=part.get('pickupSearchQuote') or regular.get('storePickupQuote', ''))
    if missing := STORES - result.keys():
        raise ValueError('Missing Manhattan stores: ' + ', '.join(sorted(missing)))
    return result


def inventory():
    query = urllib.parse.urlencode({'pl': 'true', 'cppart': 'UNLOCKED/US',
                                   'parts.0': PART, 'location': '10028'})
    request = urllib.request.Request(ENDPOINT + '?' + query,
                                    headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=25) as response:
        return parse_inventory(json.load(response))


def notify(title, message):
    topic = os.environ.get('NTFY_TOPIC', '')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{32,}', topic):
        raise ValueError('Set the NTFY_TOPIC Actions secret to a random topic, at least 32 characters')
    data = json.dumps(dict(topic=topic, title=title, message=message, priority=4, click=BUY)).encode()
    request = urllib.request.Request('https://ntfy.sh', data=data,
                                    headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=20) as response:
        response.read()


def newly_available(previous, current):
    return [v for k, v in current.items() if v['available'] and not previous.get(k, {}).get('available')]


def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(state, sort_keys=True))
    temp.replace(path)


def run(path, now=None):
    now = time.time() if now is None else now
    state = json.loads(path.read_text()) if path.exists() else {}
    if now < state.get('next_attempt', 0):
        print('Backing off after an inventory failure; stock is unknown.')
        return 0
    try:
        current = inventory()
    except Exception as error:
        failures = state.get('failures', 0) + 1
        delay = min(3600, 300 * 2 ** min(failures - 1, 4))
        if isinstance(error, urllib.error.HTTPError) and error.headers:
            retry = error.headers.get('Retry-After', '')
            if retry.isdigit():
                delay = max(delay, int(retry))
            elif retry:
                from email.utils import parsedate_to_datetime
                try:
                    delay = max(delay, parsedate_to_datetime(retry).timestamp() - now)
                except (ValueError, TypeError, OverflowError):
                    pass
        # Do not log URLs from a notification provider or secret values.
        description = f'Apple inventory HTTP {error.code}' if isinstance(error, urllib.error.HTTPError) else type(error).__name__
        state.update(failures=failures, next_attempt=now + delay, last_error=description)
        if now - state.get('last_error_alert', 0) >= 21600:
            try:
                notify('iPhone monitor needs attention', description + '. Stock is UNKNOWN, not out of stock. Checks will retry with backoff.')
                state['last_error_alert'] = now
            except Exception:
                print('Failure notification could not be delivered.', file=sys.stderr)
        save(path, state)
        print(description + '; stock is unknown.', file=sys.stderr)
        return 1
    fresh = newly_available(state.get('stores', {}), current)
    if fresh:
        timestamp = datetime.fromtimestamp(now, ZoneInfo('America/New_York')).isoformat()
        notify('iPhone Duo available in Manhattan', PRODUCT + ' (unlocked)\n' +
               '\n'.join(s['name'] + ': ' + s['quote'] for s in fresh) + '\nChecked ' + timestamp + '\n' + BUY)
    # Delivery must succeed before consuming the transition; otherwise retry next run.
    if state.get('failures'):
        notify('iPhone monitoring restored', 'Apple pickup inventory checks are working again.')
    save(path, dict(stores=current, last_success=now, failures=0))
    print(json.dumps({'checked_at': datetime.fromtimestamp(now, ZoneInfo('America/New_York')).isoformat(),
                      'stores': current, 'new_alerts': len(fresh)}, indent=2))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', action='store_true', help='Read live inventory once without sending alerts or changing state')
    parser.add_argument('--test-alert', action='store_true', help='Send a clearly labelled phone notification test')
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(inventory(), indent=2))
    elif args.test_alert:
        notify('iPhone stock watch test', 'Test notification only; this does not mean any iPhone is available.')
    else:
        if not re.fullmatch(r'[a-zA-Z0-9_-]{32,}', os.environ.get('NTFY_TOPIC', '')):
            sys.exit('Configure NTFY_TOPIC before enabling the monitor.')
        try:
            sys.exit(run(Path(os.environ.get('STATE_PATH', '.monitor-state/state.json'))))
        except Exception as error:
            # Only disclose the error type to avoid accidentally logging an alert secret.
            print('Monitoring or phone delivery failed: ' + type(error).__name__, file=sys.stderr)
            sys.exit(1)
