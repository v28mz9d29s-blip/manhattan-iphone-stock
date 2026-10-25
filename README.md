# Free GitHub iPhone stock watch

Python standard library only. No pip dependencies, AI calls, model tokens, or OpenAI API key.
Checks iPhone Duo **256GB Star White, unlocked** at all seven Manhattan Apple Stores.

## Status: prepared and tested locally, not deployed

The working Apple endpoint was verified from the development environment on October 24, 2026: all seven Manhattan stores returned the exact product and were unavailable. This does not establish GitHub-runner access. After uploading, run the workflow with `probe_only` checked and verify its result. Run it separately with `test_alert` checked and confirm delivery on your phone before relying on the monitor.

## Schedule and limits

- Runs at minutes 2, 7, 12, 17, ..., 57 every hour. Five minutes is GitHub's minimum supported scheduled interval; three minutes is not supported.
- GitHub provides no exact start-time guarantee: jobs may be delayed or dropped. Stock appearing briefly between successful checks may be missed.
- A **public repository on standard Ubuntu GitHub-hosted runners** has free Actions compute. Only generic monitoring code and non-sensitive stock results should be public. The notification topic stays in an Actions secret, never in source.
- Private repositories use plan minutes (GitHub Free: 2,000/month), so do not assume a five-minute private monitor is free. This schedule can run about 8,640 times per 30 days.
- Public schedules automatically disable after 60 days without repository activity. GitHub can also pause/rate-limit workflows; check the Actions page periodically.
- A tiny state cache reduces repeat notifications. Caches are best effort: eviction can cause a repeat alert for stock already present. Cache storage is separate from Actions compute; leave default storage limits in place. This workload should remain far below the default included 10GB.
- HTTP failures, wrong products, missing stores, unknown schemas, and timeouts are not reported as out of stock. Exponential backoff and HTTP Retry-After reduce polling on failures.
- No reservations or purchases are made. Five-minute polling is approximate, not an immediate-stock guarantee.

## One-time setup

1. Create a new **public** repository, for example `manhattan-iphone-stock`. Upload this folder's contents, **including `.github/workflows/stock.yml`**, to the default branch. Do not upload this folder as an extra parent directory.
2. Install the free ntfy app on your iPhone. Generate a random 40+ character topic (for example `openssl rand -hex 24`) and subscribe on the default `https://ntfy.sh` server. Allow notifications. Anyone who knows a free public topic can publish or subscribe; keep it random and secret. Do not use personal information in the topic.
3. Repository Settings → Secrets and variables → Actions → New repository secret. Name: `NTFY_TOPIC`. Value: the exact topic you subscribed to. No GitHub PAT or OpenAI API key is required for routine checks.
4. Open Actions → Manhattan iPhone stock → Run workflow. First run with `probe_only` checked to verify current Apple inventory from GitHub. Then run with `test_alert` checked and verify your phone receives the test. Finally run with neither checked for a complete check, and verify scheduled runs subsequently appear.
5. Only after live inventory and phone delivery both work, disable the separate hourly ChatGPT stock watch to eliminate its AI usage.

The workflow is triggered only by its schedule or a manual run, never pull requests. It has read-only repository contents permission, uses a separate stock-state cache, and never commits state changes to your repository.

## Pause or stop

Actions → Manhattan iPhone stock → three-dot menu → Disable workflow. Enable it again to resume. Delete the repository or workflow to remove it.

## Local commands

`python -m unittest -v test_monitor.py`

`python monitor.py --probe` reads live inventory without sending alerts or modifying state.

`python monitor.py --test-alert` sends a clearly labelled test using NTFY_TOPIC from the environment.

## Sources

- Schedule minimum, delays/dropped jobs, inactivity: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- Free public runner compute, private quotas, cache storage: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- Phone notifications: https://docs.ntfy.sh/subscribe/phone/
- Exact product: https://www.apple.com/shop/buy-iphone/iphone-duo/7.6-inch-display-256gb-star-white-unlocked
