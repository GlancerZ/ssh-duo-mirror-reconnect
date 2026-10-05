"""Offline behavioral tests; no real SSH connections, MFA, or user cache."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/ssh-duo-mirror-reconnect/scripts/check_connection.py"
SPEC = importlib.util.spec_from_file_location("connection_probe", SCRIPT)
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)

FAKE_SSH = r'''#!/bin/sh
stage=remote
[ "$1" = "-G" ] && stage=config
[ "$1" = "-O" ] && stage=master
printf '%s\n' "$stage" >> "$TEST_CALL_LOG"
if [ "$stage" = config ]; then
  if [ "$TEST_CASE" = config_bad ]; then
    printf 'fictional-private-diagnostic\n' >&2
    exit 255
  fi
  control=auto
  [ "$TEST_CASE" = no_multiplex ] && control=false
  printf 'hostname login.example.org\nuser researcher\ncontrolmaster %s\ncontrolpath /tmp/example-control\ncontrolpersist %s\n' "$control" "$TEST_REV"
  exit 0
fi
if [ "$stage" = master ]; then
  case "$TEST_CASE" in
    missing) printf 'Control socket connect: No such file or directory\n' >&2; exit 255 ;;
    denied) printf 'Control socket connect: Operation not permitted\n' >&2; exit 255 ;;
    unknown_master) printf 'fictional-private-diagnostic\n' >&2; exit 255 ;;
  esac
  printf 'Master running (pid=12345)\n' >&2
  exit 0
fi
case "$TEST_CASE" in
  reset) printf 'Connection reset by peer: fictional-private-diagnostic\n' >&2; exit 255 ;;
  host_key) printf 'Host key verification failed: fictional-private-diagnostic\n' >&2; exit 255 ;;
  auth) printf 'Permission denied (keyboard-interactive): fictional-private-diagnostic\n' >&2; exit 255 ;;
  banner_only) printf 'fictional-private-banner\n'; exit 0 ;;
  duplicate) printf '__SDMR_V2__:ok\n__SDMR_V2__:ok\n'; exit 0 ;;
  wrong_marker) printf '__SDMR_V2__:ssh\n'; exit 0 ;;
esac
case " $* " in *' BatchMode=yes '*) ;; *) exit 92 ;; esac
case " $* " in *' StrictHostKeyChecking=yes '*) ;; *) exit 93 ;; esac
for argument do remote_command=$argument; done
printf 'fictional-private-banner\n'
/bin/sh -c "$remote_command"
'''

FAKE_CODEX = r'''#!/bin/sh
if [ "$1" = --version ]; then
  [ "$TEST_CASE" = version_failed ] && exit 1
  printf 'codex-cli example\n'
  exit 0
fi
case "$TEST_CASE" in
  logged_out) printf 'Not logged in: fictional-private-diagnostic\n' >&2; exit 1 ;;
  unknown_login) printf 'Unexpected future format\n'; exit 0 ;;
esac
printf 'Logged in using ChatGPT\n'
'''


class HealthCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ssh-duo-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, contents in (("ssh", FAKE_SSH), ("codex", FAKE_CODEX)):
            executable = self.bin / name
            executable.write_text(contents, encoding="utf-8")
            executable.chmod(0o700)
        self.log = self.root / "calls"
        self.cache = self.root / "private-cache"

    def invoke(self, case="healthy", codex=True, extra=(), rev="604800", alias="hpc-dev"):
        command = [sys.executable, str(SCRIPT), alias, "--cache-dir", str(self.cache)]
        if codex:
            command.append("--codex")
        command.extend(extra)
        completed = subprocess.run(command, capture_output=True, text=True, timeout=3, env=dict(
            os.environ, PATH=str(self.bin) + ":/usr/bin:/bin", TEST_CASE=case,
            TEST_CALL_LOG=str(self.log), TEST_REV=rev,
        ))
        self.assertEqual(completed.stderr, "")
        self.assertNotIn("fictional-private", completed.stdout)
        self.assertNotIn("researcher", completed.stdout)
        self.assertNotIn("login.example.org", completed.stdout)
        self.assertNotIn("Logged in", completed.stdout)
        self.assertLess(len(completed.stdout), 400)
        return completed.returncode, json.loads(completed.stdout)

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_healthy_codex_is_one_remote_probe(self):
        code, result = self.invoke()
        self.assertEqual((code, result["ssh"], result["codex"], result["action"]), (0, "ok", "ok", "verify_app"))
        self.assertEqual(self.calls(), ["config", "master", "remote"])
        self.assertFalse(self.cache.exists())

    def test_ssh_only_does_not_require_codex(self):
        (self.bin / "codex").unlink()
        code, result = self.invoke(codex=False)
        self.assertEqual((code, result["action"], result["codex"]), (0, "done", "not_checked"))

    def test_missing_master_never_attempts_network_or_mfa(self):
        code, result = self.invoke("missing")
        self.assertEqual((code, result["master"], result["action"]), (1, "missing", "interactive_login"))
        self.assertEqual(self.calls(), ["config", "master"])

    def test_sandbox_denial_is_not_mfa_failure(self):
        _, result = self.invoke("denied")
        self.assertEqual(result["action"], "check_permissions")
        self.assertNotIn("remote", self.calls())

    def test_unknown_master_error_does_not_trigger_mfa(self):
        _, result = self.invoke("unknown_master")
        self.assertEqual(result["action"], "inspect_master")
        self.assertNotIn("remote", self.calls())

    def test_disabled_multiplexing_never_attempts_network(self):
        code, result = self.invoke("no_multiplex")
        self.assertEqual((code, result["master"], result["action"]), (2, "not_configured", "check_config"))
        self.assertEqual(self.calls(), ["config"])

    def test_invalid_config_is_compact(self):
        code, result = self.invoke("config_bad")
        self.assertEqual((code, result["action"]), (2, "check_config"))

    def test_transport_reset(self):
        _, result = self.invoke("reset")
        self.assertEqual(result["action"], "inspect_transport")

    def test_host_key_failure_is_not_an_auth_retry(self):
        _, result = self.invoke("host_key")
        self.assertEqual(result["action"], "verify_host_key")

    def test_authentication_failure(self):
        _, result = self.invoke("auth")
        self.assertEqual(result["action"], "interactive_login")

    def test_missing_codex(self):
        (self.bin / "codex").unlink()
        code, result = self.invoke()
        self.assertEqual((code, result["codex"], result["action"]), (1, "missing", "fix_codex"))

    def test_failed_codex_version(self):
        _, result = self.invoke("version_failed")
        self.assertEqual(result["codex"], "failed")

    def test_logged_out_codex(self):
        _, result = self.invoke("logged_out")
        self.assertEqual(result["codex"], "not_logged_in")

    def test_unknown_login_format_is_not_success(self):
        code, result = self.invoke("unknown_login")
        self.assertEqual((code, result["codex"]), (1, "unknown"))

    def test_banner_only_is_not_success(self):
        _, result = self.invoke("banner_only")
        self.assertEqual(result["action"], "inspect_remote_output")

    def test_duplicate_markers_are_not_success(self):
        _, result = self.invoke("duplicate")
        self.assertEqual(result["action"], "inspect_remote_output")

    def test_wrong_marker_is_not_codex_success(self):
        _, result = self.invoke("wrong_marker")
        self.assertEqual(result["action"], "inspect_remote_output")

    def test_invalid_arguments_never_invoke_ssh(self):
        for alias, extra in (("-bad", ()), ("user@host", ()), ("a;touch-file", ()), ("hpc-dev", ("--bad",)), ("hpc-dev", ("--remember-app", "incomplete"))):
            with self.subTest(alias=alias, extra=extra):
                code, result = self.invoke(alias=alias, extra=extra)
                self.assertEqual((code, result["action"]), (2, "check_arguments"))
        self.assertEqual(self.calls(), [])

    def remember(self):
        code, result = self.invoke(extra=("--remember-app", "remote-ssh-discovered:hpc-dev", "example-thread"))
        self.assertEqual((code, result), (0, {"cache": "saved"}))
        return next(self.cache.glob("*.json"))

    def test_private_cache_round_trip_and_mode(self):
        path = self.remember()
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        _, result = self.invoke()
        self.assertEqual(result["app_ref"], {"host_id": "remote-ssh-discovered:hpc-dev", "thread_id": "example-thread"})

    def test_effective_config_change_invalidates_cache(self):
        self.remember()
        _, result = self.invoke(rev="60")
        self.assertNotIn("app_ref", result)

    def test_cache_from_another_alias_is_not_reused(self):
        self.remember()
        _, result = self.invoke(alias="other-dev")
        self.assertNotIn("app_ref", result)

    def test_world_readable_cache_is_not_used(self):
        path = self.remember()
        path.chmod(0o644)
        _, result = self.invoke()
        self.assertNotIn("app_ref", result)

    def test_corrupt_cache_does_not_block_recovery(self):
        path = self.remember()
        path.write_text("not-json", encoding="utf-8")
        _, result = self.invoke()
        self.assertEqual(result["action"], "verify_app")
        self.assertNotIn("app_ref", result)

    def test_symlink_cache_is_not_used(self):
        path = self.remember()
        target = self.root / "saved.json"
        path.rename(target)
        path.symlink_to(target)
        _, result = self.invoke()
        self.assertNotIn("app_ref", result)

    def test_subprocess_deadline_is_real_and_sanitized(self):
        started = time.monotonic()
        code, output, error = PROBE.run([sys.executable, "-c", "import time; time.sleep(5)"], 0.05)
        self.assertEqual((code, output, error), (-1, "", "timeout"))
        self.assertLess(time.monotonic() - started, 1)

    def test_execution_unavailable_is_sanitized(self):
        code, output, error = PROBE.run([str(self.root / "nonexistent")], 1)
        self.assertEqual((code, output, error), (-2, "", "execution_unavailable"))

    def test_probe_call_has_bounded_deadlines(self):
        calls = []

        def fake_run(command, timeout):
            calls.append((command, timeout))
            if command[1] == "-G":
                return 0, "controlmaster auto\ncontrolpath /tmp/example-control\n", ""
            if command[1] == "-O":
                return 0, "", "Master running"
            return 0, "__SDMR_V2__:ok\n", ""

        with patch.object(PROBE, "run", fake_run), patch.object(PROBE, "emit", lambda result, code: code):
            self.assertEqual(PROBE.main(["hpc-dev", "--codex", "--cache-dir", str(self.cache)]), 0)
        self.assertEqual([timeout for _, timeout in calls], [5, 5, 20])
        self.assertIn("StrictHostKeyChecking=yes", calls[-1][0])
        self.assertIn("BatchMode=yes", calls[-1][0])


if __name__ == "__main__":
    unittest.main()
