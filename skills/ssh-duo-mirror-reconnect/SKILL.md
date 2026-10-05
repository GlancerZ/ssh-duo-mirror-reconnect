---
name: ssh-duo-mirror-reconnect
description: "Efficiently restore an existing Duo-protected SSH alias on macOS using an already paired iPhone mirror, and verify remote Codex. Use for routine disconnect recovery, not initial setup or background monitoring."
---

# SSH Duo Mirror Reconnect

Use the existing authorized alias. Resolve ambiguity once; reuse current context thereafter. Keep private deployment details out of public files.

## Fast path

1. Run the bundled helper with an available Python 3 interpreter (prefer a supplied runtime when system Python is unavailable):

   ```sh
   python3 scripts/check_connection.py hpc-dev --codex
   ```

   Replace the fictional alias and resolve the script relative to this skill. It returns compact JSON without banners or credentials. `verify_app` skips SSH recovery and the mirror; `interactive_login` needs MFA; other actions route to troubleshooting. If Codex is not requested, omit `--codex` and stop when SSH is healthy.

2. For MFA, establish/reuse a valid Computer Use app handle and follow its current documentation. Ensure the already paired iPhone mirror is usable before starting one SSH PTY:

   ```sh
   ssh -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 hpc-dev
   ```

   Observe the actual Duo menu and choose Push once. Reuse Duo if already open; otherwise use the observed Home shortcut/icon rather than exploratory searches. Inspect fresh UI after transitions; screenshot only when necessary to locate controls or match the request. Refresh the request list once if needed. Approve only the fresh request matching this account, service and attempt, under the user's authorization. Hand off unavailable mirroring, pairing or unexpected verification; do not change authentication settings.

3. Verify SSH success, exit the foreground shell normally, then rerun the helper. Never terminate a healthy master or use `ssh -O exit` during ordinary recovery.

4. For Codex, verify its current App Server connection and one existing remote read. Cached `app_ref` IDs are routing hints, not connection evidence. Reuse verified context/cache; discover IDs only if missing, invalidated or rejected. Filter tool results **before** emitting them: return only success/error and status, never full conversations or project lists. Require the returned thread's host and ID to match. Cache newly observed IDs with `--remember-app HOST_ID THREAD_ID`; caches stay outside the repository. Read [compact-output.md](references/compact-output.md) only when constructing an unfamiliar tool-response filter.

## Budget and exceptions

- At most three SSH attempts, two non-overlapping Pushes and two minutes of application recovery. Stop on explicit denial, mismatched MFA details or host-key failure.
- Do not load helper source, tests, README, unrelated skills or all references on ordinary runs. Read [troubleshooting.md](references/troubleshooting.md) only for the returned failure action, transport errors or an explicitly requested fault test. Required skill/tool documentation still applies.
- Do not retain OTPs, enrollment secrets, phone screenshots or raw authentication logs. Preserve host-key checks and existing SSH settings.
- Report SSH and application readiness separately; finish once verified. This procedure is not a continuous watcher and requires an awake Mac plus an available nearby phone for mirroring.
