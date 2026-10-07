# SSH Duo Mirror Reconnect

A reusable Codex skill for recovering an existing Duo-protected SSH connection on macOS, approving a fresh Duo Push through iPhone Mirroring, and checking that remote Codex actually works again.

中文：这是一个脱敏后的 SSH 重连 skill。它可以在已经配对的 iPhone 镜像中处理本次登录的 Duo Push，并验证远程 Codex；它不是绕过 MFA，也不是常驻后台的断线监控程序。

## What it does

1. Run one compact, bounded health check; reuse healthy SSH instead of opening the mirror or issuing another Push.
2. When needed, restore the alias through one interactive SSH session and approve only its matching Duo Push through the already paired mirror.
3. Verify remote Codex with a current read-only operation, filtering responses before they enter model context.
4. Reuse private routing hints and load troubleshooting only for an actual failure.
5. Prioritize time to a usable connection. If mirroring drops during MFA, check the existing SSH session before more phone work and allow approval of the same Push directly on the phone.

Each reconnect ends with a brief review of observed delays. With the user's ongoing maintenance authorization, the agent makes a small, evidence-backed local skill improvement when useful; it does not require a cosmetic rewrite after every run. Connection readiness is reported before maintenance. Reviews do not generate test Pushes, interrupt a healthy master, store private traces or automatically publish changes.

## Requirements and limits

- A supported Mac/iPhone combination with iPhone Mirroring already paired and Duo Mobile already enrolled.
- An awake, unlocked Mac and a locked, nearby iPhone with Wi-Fi and Bluetooth available.
- A configured SSH alias, a known host key, and SSH credentials already set up.
- Python 3.8+ and OpenSSH. The helper needs only the Python standard library; a supported bundled Python runtime can be used.
- An agent environment with persistent PTY shell access and native Computer Use. Installing the skill does not grant these tools or authorize phone access.
- Authorization for the intended SSH destination and mirror-based MFA approval. First-time pairing, authenticator enrollment, credential changes, and security-setting changes are outside ordinary recovery.

The skill cannot recover while the computer is offline or asleep. It does not create a continuous monitor, and mobile work with the phone away from the Mac cannot use this mirroring workflow. `ControlPersist 7d` is an idle-master lifetime, not a seven-day MFA exemption.

## Install

Copy the `skills/ssh-duo-mirror-reconnect` directory into a skill directory supported by your Codex installation. See the [current Codex skill documentation](https://learn.chatgpt.com/docs/build-skills) for supported locations and discovery behavior.

If your installation has `$skill-installer`, ask it:

> Install the skill from this GitHub repository, using the path `skills/ssh-duo-mirror-reconnect`.

Then start a new Codex session if necessary and invoke:

```text
Use $ssh-duo-mirror-reconnect to reconnect my existing hpc-dev SSH alias.
You may approve the matching fresh Duo Push through my already configured
iPhone Mirroring session. Verify remote Codex after SSH is restored.
```

`hpc-dev` is a fictional example. The skill reads the user's existing configuration instead of shipping a real server, username, key path, or control socket.

## Files

- [SKILL.md](skills/ssh-duo-mirror-reconnect/SKILL.md): the recovery procedure, verification criteria, retry limits, and privacy boundaries.
- [agents/openai.yaml](skills/ssh-duo-mirror-reconnect/agents/openai.yaml): display metadata and a default invocation prompt.
- [check_connection.py](skills/ssh-duo-mirror-reconnect/scripts/check_connection.py): bounded health checks with compact JSON and an optional private app-reference cache.
- [compact-output.md](skills/ssh-duo-mirror-reconnect/references/compact-output.md): response filtering when constructing an unfamiliar app-verification call.
- [troubleshooting.md](skills/ssh-duo-mirror-reconnect/references/troubleshooting.md): conditional diagnostics and fault-test guidance.
- [tests](tests/test_check_connection.py): offline behavioral tests; no real SSH, MFA, or user cache access.

## Efficient v2 workflow

The ordinary entrypoint stays short. Do not load the helper source, tests, README or every reference at runtime. The helper reads effective configuration, checks the control socket and, only if the master exists, performs one noninteractive remote probe. It cannot approve MFA or terminate a connection.

```sh
python3 skills/ssh-duo-mirror-reconnect/scripts/check_connection.py hpc-dev --codex
```

Example status:

```json
{"master":"running","ssh":"ok","codex":"ok","action":"verify_app"}
```

`verify_app` is not final desktop-readiness proof: the agent still performs a current matching remote read. Other actions identify the failing layer without printing raw SSH banners, credentials or conversations. Deadlines are 5 seconds for configuration, 5 for the master and 20 for the remote probe. Exit codes are `0` for healthy SSH/CLI, `1` for recovery needed and `2` for arguments/configuration/environment issues.

An optional mode-600 cache lives outside this repository, under the user's cache directory. It holds only alias/configuration signature and observed host/thread IDs, not secrets. Effective configuration changes invalidate it; failed cached reads fall back to one discovery. Never commit runtime cache data.

Run the offline tests from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

## Validation status

The original interactive workflow was tested in a private deployment: a simulated SSH master loss was followed by a new Duo Push, mirror approval, successful login, restored multiplexing, and read-only remote Codex verification. Relaunching the already configured mirror also worked there.

For v2, all 27 offline behavioral tests passed. They exercise missing masters, sandbox denial, host-key/authentication/transport failures, Codex login states, output redaction, deadlines and private-cache invalidation. A read-only live test also confirmed healthy SSH/CLI, a matching remote Codex read and private-cache reuse; the existing connection was not interrupted and no extra Push was generated.

The entrypoint decreased from 1,688 to 676 text tokens using `o200k_base` (60% smaller). In one live app-verification sample, a 29,310-character tool response was filtered to a 36-character success/status result. These measure entrypoint text and emitted response size, not total model billing, image tokens or end-to-end speed. Conditional references and first-use tool documentation can still add context.

This is deployment-specific evidence, not a guarantee for other devices or organizations. Actual Wi-Fi loss/restoration and a continuous background reconnection trigger were not tested or implemented. The published skill is an instruction package, not executable monitoring software.

## Privacy and security

This repository contains only generalized instructions and fictional examples. It excludes personal usernames, real SSH hosts and IPs, home directories, key names/fingerprints, device identities, session/task IDs, authentication codes, screenshots, and private logs.

The skill keeps host-key verification enabled, does not extract Duo enrollment secrets, and never approves unrelated or ambiguous Push requests. Use it only where the account owner and the organization's policies authorize this workflow.

## Official references

- [Apple: iPhone Mirroring requirements and use](https://support.apple.com/en-us/120421)
- [Duo: macOS authentication](https://duo.com/docs/macos)
- [Codex: skills](https://learn.chatgpt.com/docs/build-skills)
- [Codex: remote connections](https://learn.chatgpt.com/docs/remote-connections)
