# Manhattan iPhone stock watch

Checks **iPhone Duo 256GB Star White, unlocked** at all seven Manhattan Apple Stores. Python standard library only; no AI calls or recurring model tokens.

## GitHub Mobile alerts

The workflow creates an issue as github-actions[bot] and directly mentions the verified repository owner's account. No ntfy app or subscription, personal access token, Apple credentials, or payment information is required. Issues and stock logs are public.

On your phone:
1. Install GitHub Mobile and sign into the repository owner's account.
2. Allow iOS notifications for GitHub.
3. GitHub Mobile → Profile → Settings → Notifications → enable **Direct mentions**. Check Working Hours so they do not silence wanted alerts.
4. Phone delivery was verified during setup. There is no test-alert mode: only confirmed pickup stock generates mentions.

Email alerts can also be enabled in GitHub's participating-notification settings. App installation alone does not configure every notification preference.

Workflow: https://github.com/v28mz9d29s-blip/manhattan-iphone-stock/actions/workflows/stock.yml

## Schedule and cost

Scheduled at minutes 2, 7, 12, ..., 57 each hour. GitHub's minimum interval is five minutes. Standard runners are free for public repositories; no paid runner or AI service is configured. Private repositories have minute quotas.

GitHub may delay or drop runs; brief restocks can be missed. Public schedules disable after 60 days without repository activity. Review the Actions page periodically. The tiny state cache suppresses repeat alerts, but cache eviction can cause duplicates. Leave default cache storage limits in place.

HTTP errors, missing stores, mismatched products and unknown statuses are failures, never evidence of no stock. Failures back off silently and are recorded in run logs/state. Out-of-stock results, errors, and recovery never create alert issues. No reservations or purchases are made. The separate hourly AI watch is paused.

## Permissions and verification

The workflow has read access to contents and write access to issues **in this repository**, allowing its short-lived automatic token to create alerts. That token is supplied only to the checker step. No personal token or access to other repositories is required. Actions dependencies are pinned. Only scheduled and manual triggers are enabled.

A full GitHub run on October 24, 2026 at 8:25 PM America/New_York retrieved the exact product at all seven stores and saved state. All seven were unavailable then. Notification delivery has since switched to GitHub mentions; confirm a new GitHub test issue reaches your device.

Pause: Actions → Manhattan iPhone stock → three-dot menu → Disable workflow.

Local tests: python -m unittest -v test_monitor.py
Live stock without alerts: python monitor.py --probe
Stock-only alerts require the workflow token, repository, and NOTIFY_LOGIN.

## Sources

- Schedule: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- Billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- Mobile notifications: https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications
- Product: https://www.apple.com/shop/buy-iphone/iphone-duo/7.6-inch-display-256gb-star-white-unlocked
