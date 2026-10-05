# SSH Duo Mirror Reconnect

A reusable Codex skill for recovering an existing Duo-protected SSH connection on macOS, approving a fresh Duo Push through iPhone Mirroring, and checking that remote Codex actually works again.

中文：这是一个脱敏后的 SSH 重连 skill。它可以在已经配对的 iPhone 镜像中处理本次登录的 Duo Push，并验证远程 Codex；它不是绕过 MFA，也不是常驻后台的断线监控程序。

## What it does

1. Inspect an existing SSH alias and reuse a healthy OpenSSH ControlMaster.
2. Start a bounded interactive SSH reconnect when needed.
3. Approve only the fresh Duo Push matching that authorized login through the already configured phone mirror.
4. Preserve the multiplexed master and verify SSH, remote CLI login, desktop App Server state, and a read-only remote operation.
5. Distinguish network failures, authentication failures, and application bootstrap failures.

## Requirements and limits

- A supported Mac/iPhone combination with iPhone Mirroring already paired and Duo Mobile already enrolled.
- An awake, unlocked Mac and a locked, nearby iPhone with Wi-Fi and Bluetooth available.
- A configured SSH alias, a known host key, and SSH credentials already set up.
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

## Validation status

The workflow was tested interactively in a private deployment: a simulated SSH master loss was followed by a new Duo Push, approval through iPhone Mirroring, successful SSH login, restored multiplexing, and read-only remote Codex verification. Relaunching the already configured mirror also worked in that deployment.

This is deployment-specific evidence, not a guarantee for other devices or organizations. Actual Wi-Fi loss/restoration and a continuous background reconnection trigger were not tested or implemented. The published skill is an instruction package, not executable monitoring software.

## Privacy and security

This repository contains only generalized instructions and fictional examples. It excludes personal usernames, real SSH hosts and IPs, home directories, key names/fingerprints, device identities, session/task IDs, authentication codes, screenshots, and private logs.

The skill keeps host-key verification enabled, does not extract Duo enrollment secrets, and never approves unrelated or ambiguous Push requests. Use it only where the account owner and the organization's policies authorize this workflow.

## Official references

- [Apple: iPhone Mirroring requirements and use](https://support.apple.com/en-us/120421)
- [Duo: macOS authentication](https://duo.com/docs/macos)
- [Codex: skills](https://learn.chatgpt.com/docs/build-skills)
- [Codex: remote connections](https://learn.chatgpt.com/docs/remote-connections)
