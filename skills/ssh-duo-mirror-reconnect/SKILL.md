---
name: ssh-duo-mirror-reconnect
description: "Recover a Duo-protected SSH connection on macOS using Duo Push through an already configured iPhone Mirroring session. Use when reconnecting an existing SSH alias, restoring its multiplexed connection, or verifying a remote Codex connection after a disconnect."
---

# SSH Duo Mirror Reconnect

Restore an existing SSH connection and verify the application that uses it. Prefer Duo Push; this is an interactive recovery procedure, not an MFA bypass or a background watcher.

## Inputs and prerequisites

- Identify the existing SSH alias from the user's request or previously verified configuration. Ask only if the intended destination is ambiguous. Examples below use the fictional alias `hpc-dev`.
- Use shell tools with a persistent PTY for interactive SSH and Computer Use for iPhone Mirroring. If either capability is unavailable, explain the missing capability and hand off only that step.
- Use an already enrolled Duo account and already paired iPhone Mirroring session. The Mac must be awake and unlocked; the iPhone must be locked, nearby, and available for mirroring with Wi-Fi and Bluetooth enabled. Check [Apple's current requirements](https://support.apple.com/en-us/120421) when setup compatibility is uncertain.
- Confirm that the user has authorized reconnecting this destination and, if needed, approving its MFA request through the mirror. A reconnect request alone does not authorize new phone pairing, enrolling authenticators, changing credentials, or changing authentication settings.
- Do not install Duo for macOS to obtain SSH codes: [Duo macOS authentication](https://duo.com/docs/macos) protects Mac logins; it is not Duo Mobile on the iPhone.

## 1. Inspect and reuse the SSH alias

Inspect effective settings without dumping the entire SSH configuration or private key material:

```sh
SSH_ALIAS=hpc-dev
ssh -G "$SSH_ALIAS" | rg '^(hostname|user|controlmaster|controlpath|controlpersist|serveraliveinterval|serveralivecountmax) '
ssh -O check "$SSH_ALIAS"
```

Use the same alias for all connections so the expected ControlMaster socket is reused. Treat resolved hostnames, usernames, paths, and logs as private runtime data.

If the master is running, test a noninteractive command first:

```sh
ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 "$SSH_ALIAS" 'hostname'
```

If this works, proceed to application verification without issuing another Push. If no master exists, first check that iPhone Mirroring is usable, then begin a fresh interactive connection. Do not terminate a healthy master during ordinary recovery.

`ControlPersist 7d` retains an idle master for up to seven days after its last client exits. It cannot keep a dead connection alive or eliminate MFA after a reset. Preserve the user's existing settings; edit configuration only when configuration repair is requested.

## 2. Initiate one fresh Duo Push

Start SSH in a PTY that can remain open while Computer Use operates the mirror:

```sh
ssh -o ConnectTimeout=10 -o ConnectionAttempts=1 "$SSH_ALIAS"
```

Read the actual authentication menu. Select the displayed Duo Push option rather than assuming it is always option `1`. Keep exactly one pending authentication attempt. If a password, pairing step, or credential change is required and cannot be completed within the authorized workflow, hand that step to the user without requesting secrets in chat.

## 3. Approve the matching request through iPhone Mirroring

1. Read the current Computer Use documentation, then open or select iPhone Mirroring using its documented app API. Inspect fresh state after each transition.
2. Open Duo Mobile using observed UI elements. When the mirrored screen has no useful accessibility text, use a fresh screenshot and current coordinates; never reuse device-specific coordinates from another session.
3. Wait for the new Push. If the request is not visible, refresh Duo's request list using the observed control. Do not confuse request refresh with passcode refresh.
4. Match the request to the SSH attempt just initiated: expected organization/service, account, and current timing. Inspect source/location information where available; unexpected details require clarification, not automatic approval.
5. Approve only this matching request when mirror-based approval is authorized. Leave unrelated or ambiguous requests untouched. Never bulk-approve pending requests.
6. Return to the PTY and verify explicit authentication success and an actual remote shell prompt. A tap on Approve alone is not proof of login.

Do not copy OTPs, account screenshots, enrollment data, or phone contents into chat, files, commits, or diagnostics. If the mirror requires unlocking/pairing or the phone is away, pause at that step and let the user approve the current Push themselves.

## 4. Preserve the master and verify the application

Close the foreground remote shell with ordinary `exit`, then check that a configured persistent master remains. Do **not** use `ssh -O exit` here: that command terminates the master.

```sh
ssh -O check "$SSH_ALIAS"
ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 "$SSH_ALIAS" 'hostname'
```

When remote Codex is in scope, also verify:

```sh
ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 "$SSH_ALIAS" 'codex --version; codex login status'
```

Check both command outputs; the compound command's exit status alone is insufficient. Use the desktop's available read-only remote-status tools or focused logs to verify its App Server is `connected` for the same alias. Then list/read an existing remote task or perform an equivalent read-only remote workspace operation. Derive host IDs from observed app metadata; never hardcode another user's IDs.

If only SSH is verified, report "SSH restored; remote application not yet verified." Port 22 being reachable, a successful shell, or a remote CLI version alone does not prove desktop Codex is usable. Do not create, modify, or message remote tasks merely to validate connectivity.

## Bounded troubleshooting

- Limit one recovery run to three SSH connection attempts and at most two Duo Push requests. Resolve or cancel the old attempt before a new one. Stop on explicit MFA denial, unexpected account details, or an authentication policy block.
- Distinguish a reset before the SSH banner from an MFA rejection. For a pre-authentication reset, inspect current DNS resolution and service status before retrying.
- When DNS provides multiple verified endpoints for the intended service, a temporary command-line endpoint override may help. Use an endpoint observed in current DNS, retain the original hostname as `HostKeyAlias`, and require known host-key verification:

```sh
# Set these from the current alias configuration and verified DNS, not this example.
ssh -o HostName="$VERIFIED_ENDPOINT" -o HostKeyAlias="$EXPECTED_HOSTNAME" \
    -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 "$SSH_ALIAS"
```

- Never use `StrictHostKeyChecking=no`, delete known-host records to silence a mismatch, or permanently pin an endpoint during ordinary recovery. A missing/mismatched host key requires trusted verification.
- If SSH works but Codex is still disconnected, allow its normal bootstrap/reconnect to finish. Use bounded status checks for up to two minutes, provide a concise progress update, and report the exact remaining layer if it does not recover. Avoid rapid polling or killing unrelated processes.

## Testing and completion

Only simulate connection loss when explicitly requested. Check for active sessions/jobs first and explain that `ssh -O exit "$SSH_ALIAS"` disconnects all clients sharing that master. Confirm the mirror is ready before terminating it. Do not disable Wi-Fi or other network settings for an SSH-only test.

Report the verified result, which layers passed, and any remaining condition. Clearly distinguish:

- recovery while this skill is actively running;
- a simulated lost SSH master;
- a real network outage and restoration;
- a separately implemented continuous background monitor.

This skill alone does not schedule future runs, operate while the Mac is offline/asleep, or make iPhone Mirroring available when the phone is away. Never claim unattended, continuous recovery based only on a successful interactive test.
