#!/usr/bin/env python3
"""Bounded, noninteractive SSH/Codex health checks with compact output.

Python standard library only. Never approves MFA, changes SSH settings,
terminates a master, or prints raw command output.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def emit(result, code):
    print(json.dumps(result, separators=(",", ":")))
    return code


def run(command, timeout):
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout,
            env=dict(os.environ, LC_ALL="C"),
        )
        return completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except OSError:
        return -2, "", "execution_unavailable"


def parse_args(args):
    if not args or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args[0]):
        raise ValueError
    alias, codex, remember = args[0], False, None
    cache_dir = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "ssh-duo-mirror-reconnect"
    index = 1
    while index < len(args):
        option = args[index]
        if option == "--codex":
            codex = True
            index += 1
        elif option == "--cache-dir" and index + 1 < len(args):
            cache_dir = Path(args[index + 1]).expanduser()
            index += 2
        elif option == "--remember-app" and index + 2 < len(args):
            remember = args[index + 1:index + 3]
            if any(not re.fullmatch(r"[A-Za-z0-9:._-]{1,256}", value) for value in remember):
                raise ValueError
            index += 3
        else:
            raise ValueError
    return alias, codex, remember, cache_dir


def cache_path(cache_dir, alias):
    return cache_dir / (hashlib.sha256(alias.encode()).hexdigest() + ".json")


def load_ref(path, alias, signature):
    try:
        if path.is_symlink() or path.stat().st_mode & 0o077:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("alias") == alias and value.get("signature") == signature:
            host_id, thread_id = value.get("host_id"), value.get("thread_id")
            if all(isinstance(item, str) and re.fullmatch(r"[A-Za-z0-9:._-]{1,256}", item) for item in (host_id, thread_id)):
                return {"host_id": host_id, "thread_id": thread_id}
    except (OSError, ValueError, AttributeError):
        pass
    return None


def save_ref(path, alias, signature, remember):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise OSError("unsafe_cache_directory")
    value = dict(alias=alias, signature=signature, host_id=remember[0], thread_id=remember[1])
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".state-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, separators=(",", ":"))
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(args=None):
    try:
        alias, codex, remember, cache_dir = parse_args(sys.argv[1:] if args is None else args)
    except ValueError:
        return emit({"action": "check_arguments", "error": "invalid_arguments"}, 2)

    code, config, error = run(["ssh", "-G", alias], 5)
    if code:
        action = "check_environment" if code == -2 else "check_config"
        return emit({"action": action, "error": "config_unavailable"}, 2)
    settings = dict(line.split(None, 1) for line in config.splitlines() if len(line.split(None, 1)) == 2)
    signature = hashlib.sha256(config.encode()).hexdigest()
    state_path = cache_path(cache_dir, alias)
    if remember is not None:
        try:
            save_ref(state_path, alias, signature, remember)
        except OSError:
            return emit({"action": "check_cache", "error": "cache_write_failed"}, 2)
        return emit({"cache": "saved"}, 0)

    result = {"master": "unknown", "ssh": "not_checked", "codex": "not_checked"}
    if codex:
        app_ref = load_ref(state_path, alias, signature)
        if app_ref:
            result["app_ref"] = app_ref
    if settings.get("controlpath", "none") == "none" or settings.get("controlmaster", "false") in ("false", "no"):
        result.update(master="not_configured", action="check_config")
        return emit(result, 2)

    code, output, error = run(["ssh", "-O", "check", alias], 5)
    if code:
        combined = (output + error).lower()
        if code == -2:
            result.update(master="unavailable", action="check_environment")
        elif any(term in combined for term in ("operation not permitted", "permission denied", "not allowed")):
            result.update(master="unavailable", action="check_permissions")
        elif any(term in combined for term in ("no such file", "connection refused", "connection reset", "broken pipe")):
            result.update(master="missing", action="interactive_login")
        else:
            result.update(master="unknown", action="inspect_master")
        return emit(result, 1)
    result["master"] = "running"

    if codex:
        remote_command = """state=missing
if command -v codex >/dev/null 2>&1; then
  state=failed
  if codex --version >/dev/null 2>&1; then
    state=not_logged_in
    if login_state=$(codex login status 2>&1); then
      case "$login_state" in
        "Logged in"*) state=ok ;;
        *) state=unknown ;;
      esac
    fi
  fi
fi
printf '__SDMR_V2__:%s\\n' "$state"
"""
    else:
        remote_command = "printf '__SDMR_V2__:ssh\\n'"
    code, output, error = run([
        "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
        "-o", "ConnectTimeout=8", "-o", "ConnectionAttempts=1",
        alias, remote_command,
    ], 20)
    if code:
        result["ssh"] = "failed"
        combined = error.lower()
        if "host key verification failed" in combined or "remote host identification has changed" in combined:
            result["action"] = "verify_host_key"
        elif "permission denied" in combined or "authentication" in combined:
            result["action"] = "interactive_login"
        elif code == -2:
            result["action"] = "check_environment"
        else:
            result["action"] = "inspect_transport"
        return emit(result, 1)
    markers = re.findall(r"^__SDMR_V2__:(ssh|ok|missing|failed|not_logged_in|unknown)$", output, re.MULTILINE)
    if len(markers) != 1 or (not codex and markers[0] != "ssh") or (codex and markers[0] == "ssh"):
        result.update(ssh="unverified", action="inspect_remote_output")
        return emit(result, 1)
    result["ssh"] = "ok"
    if codex:
        result["codex"] = markers[0]
        result["action"] = "verify_app" if markers[0] == "ok" else "fix_codex"
    else:
        result["action"] = "done"
    return emit(result, 0 if result["action"] in ("verify_app", "done") else 1)


if __name__ == "__main__":
    sys.exit(main())
