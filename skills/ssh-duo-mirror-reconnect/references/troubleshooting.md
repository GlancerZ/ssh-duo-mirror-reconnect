# Read only the relevant failure section

The health helper uses only noninteractive checks and never generates a Push. Exit codes: `0` healthy SSH/CLI (Codex still requires app verification), `1` recovery needed, `2` arguments/configuration/environment need attention. `--cache-dir PATH` overrides the private cache directory. Python 3.8+ and OpenSSH are required.

## check_permissions / check_environment

A sandbox-blocked socket is not a missing master. Request the product's narrowly scoped shell/network permission for this existing alias and retry the same helper. Do not recreate SSH configuration or issue MFA because of a local permission failure. Use an available bundled Python if system Python requires unavailable developer tools.

## check_config / inspect_master

Inspect only hostname, user, ControlMaster, ControlPath, ControlPersist and keepalive fields from `ssh -G ALIAS`. Multiplexing must be configured for persistent reuse. Preserve current settings unless configuration repair is requested. Investigate unknown master errors; do not silently terminate a healthy master.

`ControlPersist 7d` is an idle-master lifetime after its last client exits. It cannot survive a killed/reset connection or exempt later logins from MFA.

## interactive_login

Use one SSH PTY and the currently displayed Duo menu, with the mirror ready first. A supported, already paired mirror requires an awake unlocked Mac and a locked nearby phone with Wi-Fi/Bluetooth available. If it cannot connect, let the user approve the current request on the phone; do not change pairing or authentication settings. [Apple requirements](https://support.apple.com/en-us/120421).

On a fresh Computer Use session establish the app binding through the documented entry point; do not assume a prior session's variable exists. Reuse the binding within that session. Follow required observations after actions, using screenshots where mirrored controls lack accessibility text. Do not capture/save unrelated phone contents or reveal passcodes.

For a paused/disconnected existing mirror, try its currently visible Continue/Connect/Retry control once and inspect the result; do not repeat unchanged observations or start a pairing flow. After a Push is pending, a mirror interruption is not proof that Duo delivery or SSH failed. Poll the same SSH PTY first. If login has succeeded, skip all further phone work and verify SSH/Codex. Otherwise promptly offer direct approval of that same request on the phone. Use only one pending authentication session; cancel a timed-out/abandoned pre-authentication PTY before an authorized retry. A closed PTY requires a fresh session/menu, not blind input into the old one.

Selecting Push is not login success. Match expected service/account/current attempt, approve under existing authorization, and verify the remote prompt. Stop on denial, ambiguous requests or an authentication policy block. [Duo macOS authentication](https://duo.com/docs/macos) is not Duo Mobile and will not supply SSH codes.

## inspect_transport / verify_host_key / inspect_remote_output

Distinguish pre-banner resets, TCP/DNS failure and MFA rejection. Resolve current DNS only after a transport failure. If it supplies several verified endpoints for this service, a temporary override can be used:

```sh
ssh -o HostName="$VERIFIED_ENDPOINT" -o HostKeyAlias="$EXPECTED_HOSTNAME" \
    -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 "$SSH_ALIAS"
```

Use values from the current alias and DNS; never publish/pin a real endpoint. A missing/mismatched host key requires trusted verification, not deleted known-host records or disabled checking. The helper's 20-second remote deadline can also indicate a slow login filesystem/shell; retry within the run budget rather than assuming MFA failure.

The remote probe emits an exact marker. Missing/duplicate markers remain unverified even when SSH exits zero. Do not turn a successful TCP connection or banner into an application-readiness claim.

## fix_codex / application still unavailable

`missing`, `failed`, `not_logged_in` and `unknown` remain distinct. Inspect only the relevant CLI failure; complete a required user sign-in without copying credentials. No enrollment or installation is implied by routine reconnect authorization. For product configuration changes, consult current official guidance as needed. [Codex remote connections](https://learn.chatgpt.com/docs/remote-connections).

Allow normal App Server bootstrap/reconnect. Use bounded checks for up to two minutes; stop after a successful current matching app read. Avoid historical log evidence, rapid polling and unrelated process termination. If recovery remains incomplete, report the failing layer.

## Explicit fault tests

Prefer mocked missing-master/failure tests and a read-only live probe. Terminate a real shared master only when the user specifically asks for that fault simulation, after checking active clients and mirror readiness. `ssh -O exit ALIAS` disconnects all its clients. Do not disable Wi-Fi for an SSH-only test.
