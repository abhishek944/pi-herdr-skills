#!/usr/bin/env python3
"""Regression checks for automatic fallback and explicit user-pinned routing."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROUTER = Path(__file__).resolve().with_name("model-routing.py")
CATALOG = ROOT / "model-routing-policy" / "models.json"


def write_bound(path: Path, value: dict[str, object]) -> str:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], env: dict[str, str], *, ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, env=env, text=True, capture_output=True)
    if ok and result.returncode != 0:
        raise AssertionError(f"command failed: {result.stderr}\n{result.stdout}")
    if not ok and result.returncode == 0:
        raise AssertionError(f"command unexpectedly passed: {' '.join(command)}")
    return result


def main() -> None:
    temp_root = Path(tempfile.gettempdir()).resolve()
    temp = Path(tempfile.mkdtemp(prefix="model-routing-pin-", dir=temp_root))
    try:
        home = temp / "home"
        trusted = home / ".pi" / "agent" / "skills" / "model-routing-policy" / "models.json"
        trusted.parent.mkdir(parents=True)
        shutil.copy2(CATALOG, trusted)

        binary = temp / "bin"
        binary.mkdir()
        pi = binary / "pi"
        pi.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' 'Provider Model Context Window' "
            "'openai-codex gpt-5.6-sol 272k' "
            "'opencode-go deepseek-v4-flash 128k' "
            "'opencode-go glm-5.3 128k'\n",
            encoding="utf-8",
        )
        pi.chmod(pi.stat().st_mode | stat.S_IXUSR)

        env = os.environ.copy()
        env.update(
            {
                "HOME": str(home),
                "PATH": f"{binary}{os.pathsep}{env['PATH']}",
                "PI_PROVIDER": "openai-codex",
                "PI_MODEL": "gpt-5.6-sol",
                "PI_REASONING_LEVEL": "medium",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        base = [
            "python3",
            str(ROUTER),
            "resolve",
            "--catalog",
            str(trusted),
            "--task-class",
            "focused-edit",
            "--input",
            "text",
        ]
        pinned_command = [
            *base,
            "--thinking",
            "low",
            "--user-model",
            "opencode-go/deepseek-v4-flash",
            "--user-model-authority",
            "latest-user-request",
        ]
        pinned = json.loads(run(pinned_command, env).stdout)
        assert pinned["policyVersion"] == 5
        assert pinned["request"]["selectionMode"] == "user-pinned"
        assert pinned["request"]["userModelAuthority"] == "latest-user-request"
        assert pinned["selection"]["provider"] == "opencode-go"
        assert pinned["selection"]["modelId"] == "deepseek-v4-flash"
        assert pinned["selection"]["thinkingLevel"] == "low"
        assert pinned["piArgs"] == [
            "--provider",
            "opencode-go",
            "--model",
            "deepseek-v4-flash",
            "--thinking",
            "low",
        ]

        automatic = json.loads(run(base, env).stdout)
        assert automatic["request"]["selectionMode"] == "automatic"
        assert automatic["request"]["userModel"] is None
        assert automatic["selection"]["provider"] == "opencode-go"
        assert automatic["selection"]["modelId"] == "deepseek-v4-flash"
        assert automatic["selection"]["thinkingLevel"] == "high"
        assert automatic["request"]["excludedModels"] == []
        assert automatic["piArgs"] == [
            "--provider",
            "opencode-go",
            "--model",
            "deepseek-v4-flash",
            "--thinking",
            "high",
        ]

        automatic_path = temp / "automatic.json"
        automatic_digest = write_bound(automatic_path, automatic)
        automatic_start = temp / "automatic-start.json"
        write_bound(
            automatic_start,
            {
                "id": "cli:agent:start",
                "result": {
                    "type": "agent_started",
                    "argv": ["pi", *automatic["piArgs"]],
                    "agent": {
                        "agent": "pi",
                        "agent_status": "idle",
                        "interactive_ready": True,
                        "name": "automatic-test",
                        "pane_id": "w1:p2",
                        "tab_id": "w1:t1",
                        "agent_session": {
                            "agent": "pi",
                            "source": "herdr:pi",
                            "kind": "path",
                            "value": "session-one",
                        },
                    },
                },
            },
        )
        launch_one_path = temp / "launch-one.json"
        run(
            [
                "python3",
                str(ROUTER),
                "verify-launch",
                "--resolution",
                str(automatic_path),
                "--resolution-digest",
                automatic_digest,
                "--herdr-start",
                str(automatic_start),
                "--output",
                str(launch_one_path),
            ],
            env,
        )
        launch_one_digest = hashlib.sha256(launch_one_path.read_bytes()).hexdigest()
        output_one_path = temp / "output-one.json"
        output_one_digest = write_bound(output_one_path, {"error": "quota"})
        close_one_path = temp / "close-one.json"
        close_one_digest = write_bound(
            close_one_path,
            {"id": "cli:pane:close", "result": {"type": "ok"}},
        )
        absent_one_path = temp / "absent-one.json"
        absent_one_digest = write_bound(
            absent_one_path,
            {
                "id": "cli:pane:get",
                "error": {
                    "code": "pane_not_found",
                    "message": "pane w1:p2 not found",
                },
            },
        )
        failure_path = temp / "failure.json"
        failure_digest = write_bound(
            failure_path,
            {
                "classification": "model-specific-no-contribution",
                "reasonCode": "quota",
                "failedModel": "opencode-go/deepseek-v4-flash",
                "agentSessionId": "session-one",
                "paneId": "w1:p2",
                "usableContribution": False,
                "sideEffects": False,
                "launchVerification": {
                    "path": str(launch_one_path),
                    "digest": launch_one_digest,
                },
                "runtimeOutput": {
                    "path": str(output_one_path),
                    "digest": output_one_digest,
                },
            },
        )
        cleanup_path = temp / "cleanup.json"
        cleanup_digest = write_bound(
            cleanup_path,
            {
                "agentSessionId": "session-one",
                "paneId": "w1:p2",
                "agentStopped": True,
                "paneClosed": True,
                "remainingActive": False,
                "closureResponse": {
                    "path": str(close_one_path),
                    "digest": close_one_digest,
                },
                "absenceResponse": {
                    "path": str(absent_one_path),
                    "digest": absent_one_digest,
                },
            },
        )
        fallback_flags = [
            "--fallback-from",
            str(automatic_path),
            "--fallback-from-digest",
            automatic_digest,
            "--failure-evidence",
            str(failure_path),
            "--failure-evidence-digest",
            failure_digest,
            "--cleanup-evidence",
            str(cleanup_path),
            "--cleanup-evidence-digest",
            cleanup_digest,
        ]
        pi.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' 'Provider Model Context Window' "
            "'openai-codex gpt-5.6-sol 272k' "
            "'opencode-go glm-5.3 128k'\n",
            encoding="utf-8",
        )
        fallback = json.loads(run([*base, *fallback_flags], env).stdout)
        pi.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' 'Provider Model Context Window' "
            "'openai-codex gpt-5.6-sol 272k' "
            "'opencode-go deepseek-v4-flash 128k' "
            "'opencode-go glm-5.3 128k'\n",
            encoding="utf-8",
        )
        assert fallback["request"]["selectionMode"] == "automatic"
        assert fallback["request"]["excludedModels"] == [
            "opencode-go/deepseek-v4-flash"
        ]
        assert fallback["request"]["fallbackFrom"]["previousResolution"]["digest"] == automatic_digest
        assert fallback["selection"]["provider"] == "opencode-go"
        assert fallback["selection"]["modelId"] == "glm-5.3"
        assert fallback["selection"]["thinkingLevel"] == "high"

        wrong_absence_path = temp / "wrong-pane-absent.json"
        wrong_absence_digest = write_bound(
            wrong_absence_path,
            {
                "id": "cli:pane:get",
                "error": {
                    "code": "pane_not_found",
                    "message": "pane w1:p999 not found",
                },
            },
        )
        wrong_failure_path = temp / "wrong-pane-failure.json"
        wrong_failure_digest = write_bound(
            wrong_failure_path,
            {
                **json.loads(failure_path.read_text()),
                "paneId": "w1:p999",
            },
        )
        wrong_cleanup_path = temp / "wrong-pane-cleanup.json"
        wrong_cleanup_digest = write_bound(
            wrong_cleanup_path,
            {
                **json.loads(cleanup_path.read_text()),
                "paneId": "w1:p999",
                "absenceResponse": {
                    "path": str(wrong_absence_path),
                    "digest": wrong_absence_digest,
                },
            },
        )
        run(
            [
                *base,
                "--fallback-from",
                str(automatic_path),
                "--fallback-from-digest",
                automatic_digest,
                "--failure-evidence",
                str(wrong_failure_path),
                "--failure-evidence-digest",
                wrong_failure_digest,
                "--cleanup-evidence",
                str(wrong_cleanup_path),
                "--cleanup-evidence-digest",
                wrong_cleanup_digest,
            ],
            env,
            ok=False,
        )

        fallback_path = temp / "fallback.json"
        fallback_digest = write_bound(fallback_path, fallback)
        fallback_start_for_chain = temp / "fallback-start-for-chain.json"
        write_bound(
            fallback_start_for_chain,
            {
                "id": "cli:agent:start",
                "result": {
                    "type": "agent_started",
                    "argv": ["pi", *fallback["piArgs"]],
                    "agent": {
                        "agent": "pi",
                        "agent_status": "idle",
                        "interactive_ready": True,
                        "name": "fallback-chain-test",
                        "pane_id": "w1:p3",
                        "tab_id": "w1:t1",
                        "agent_session": {
                            "agent": "pi",
                            "source": "herdr:pi",
                            "kind": "path",
                            "value": "session-two",
                        },
                    },
                },
            },
        )
        launch_two_path = temp / "launch-two.json"
        run(
            [
                "python3",
                str(ROUTER),
                "verify-launch",
                "--resolution",
                str(fallback_path),
                "--resolution-digest",
                fallback_digest,
                "--herdr-start",
                str(fallback_start_for_chain),
                "--output",
                str(launch_two_path),
            ],
            env,
        )
        launch_two_digest = hashlib.sha256(launch_two_path.read_bytes()).hexdigest()
        output_two_path = temp / "output-two.json"
        output_two_digest = write_bound(output_two_path, {"error": "capacity"})
        close_two_path = temp / "close-two.json"
        close_two_digest = write_bound(
            close_two_path,
            {"id": "cli:pane:close", "result": {"type": "ok"}},
        )
        absent_two_path = temp / "absent-two.json"
        absent_two_digest = write_bound(
            absent_two_path,
            {
                "id": "cli:pane:get",
                "error": {
                    "code": "pane_not_found",
                    "message": "pane w1:p3 not found",
                },
            },
        )
        failure_two_path = temp / "failure-two.json"
        failure_two_digest = write_bound(
            failure_two_path,
            {
                "classification": "model-specific-no-contribution",
                "reasonCode": "capacity",
                "failedModel": "opencode-go/glm-5.3",
                "agentSessionId": "session-two",
                "paneId": "w1:p3",
                "usableContribution": False,
                "sideEffects": False,
                "launchVerification": {
                    "path": str(launch_two_path),
                    "digest": launch_two_digest,
                },
                "runtimeOutput": {
                    "path": str(output_two_path),
                    "digest": output_two_digest,
                },
            },
        )
        cleanup_two_path = temp / "cleanup-two.json"
        cleanup_two_digest = write_bound(
            cleanup_two_path,
            {
                "agentSessionId": "session-two",
                "paneId": "w1:p3",
                "agentStopped": True,
                "paneClosed": True,
                "remainingActive": False,
                "closureResponse": {
                    "path": str(close_two_path),
                    "digest": close_two_digest,
                },
                "absenceResponse": {
                    "path": str(absent_two_path),
                    "digest": absent_two_digest,
                },
            },
        )
        exhausted = run(
            [
                *base,
                "--fallback-from",
                str(fallback_path),
                "--fallback-from-digest",
                fallback_digest,
                "--failure-evidence",
                str(failure_two_path),
                "--failure-evidence-digest",
                failure_two_digest,
                "--cleanup-evidence",
                str(cleanup_two_path),
                "--cleanup-evidence-digest",
                cleanup_two_digest,
            ],
            env,
            ok=False,
        )
        assert "no remaining catalog model" in exhausted.stderr

        changed_zone = run([*base, "--input", "image", *fallback_flags], env, ok=False)
        assert "routing zone does not match" in changed_zone.stderr

        changed_caller_env = dict(env)
        changed_caller_env["PI_MODEL"] = "gpt-5.6-terra"
        changed_caller = run([*base, *fallback_flags], changed_caller_env, ok=False)
        assert "caller baseline does not match" in changed_caller.stderr

        partial_failure = json.loads(failure_path.read_text())
        partial_failure["usableContribution"] = True
        partial_digest = write_bound(failure_path, partial_failure)
        rejected_partial = run(
            [
                *base,
                *[
                    partial_digest if value == failure_digest else value
                    for value in fallback_flags
                ],
            ],
            env,
            ok=False,
        )
        assert "does not prove a no-contribution failure" in rejected_partial.stderr
        failure_digest = write_bound(
            failure_path,
            {
                "classification": "model-specific-no-contribution",
                "reasonCode": "quota",
                "failedModel": "opencode-go/deepseek-v4-flash",
                "agentSessionId": "session-one",
                "paneId": "w1:p2",
                "usableContribution": False,
                "sideEffects": False,
                "launchVerification": {
                    "path": str(launch_one_path),
                    "digest": launch_one_digest,
                },
                "runtimeOutput": {
                    "path": str(output_one_path),
                    "digest": output_one_digest,
                },
            },
        )
        fallback_flags[fallback_flags.index("--failure-evidence-digest") + 1] = failure_digest

        pinned_fallback = run([*pinned_command, *fallback_flags], env, ok=False)
        assert "user-pinned routing cannot fall back" in pinned_fallback.stderr

        missing_authority = run(
            [*base, "--user-model", "opencode-go/deepseek-v4-flash"], env, ok=False
        )
        assert "requires --user-model-authority" in missing_authority.stderr

        missing_model = run(
            [
                *base,
                "--user-model",
                "opencode-go/not-a-model",
                "--user-model-authority",
                "latest-user-request",
            ],
            env,
            ok=False,
        )
        assert "not in the catalog" in missing_model.stderr

        incompatible = run(
            [
                *base,
                "--input",
                "image",
                "--user-model",
                "opencode-go/deepseek-v4-flash",
                "--user-model-authority",
                "latest-user-request",
            ],
            env,
            ok=False,
        )
        assert "does not satisfy" in incompatible.stderr

        unavailable = run(
            [
                *base,
                "--user-model",
                "opencode-go/deepseek-v4-pro",
                "--user-model-authority",
                "latest-user-request",
            ],
            env,
            ok=False,
        )
        assert "unavailable; no fallback" in unavailable.stderr

        review_pin = run(
            [
                "python3",
                str(ROUTER),
                "resolve",
                "--catalog",
                str(trusted),
                "--task-class",
                "review",
                "--input",
                "text",
                "--no-contributor",
                "--thinking",
                "medium",
                "--user-model",
                "openai-codex/gpt-5.6-sol",
                "--user-model-authority",
                "latest-user-request",
            ],
            env,
            ok=False,
        )
        assert "stronger-reviewer requirements" in review_pin.stderr

        resolution = temp / "resolution.json"
        resolution.write_text(json.dumps(pinned, indent=2, sort_keys=True) + "\n")
        digest = hashlib.sha256(resolution.read_bytes()).hexdigest()
        start = temp / "start.json"
        start.write_text(
            json.dumps(
                {
                    "id": "cli:agent:start",
                    "result": {
                        "type": "agent_started",
                        "argv": ["pi", *pinned["piArgs"]],
                        "agent": {
                            "agent": "pi",
                            "agent_status": "idle",
                            "interactive_ready": True,
                            "name": "pin-test",
                            "pane_id": "w1:p2",
                            "tab_id": "w1:t1",
                            "agent_session": {
                                "agent": "pi",
                                "source": "herdr:pi",
                                "kind": "path",
                                "value": "/tmp/pin-test-session.jsonl",
                            },
                        },
                    },
                },
                indent=2,
            )
            + "\n"
        )
        verified = json.loads(
            run(
                [
                    "python3",
                    str(ROUTER),
                    "verify-launch",
                    "--resolution",
                    str(resolution),
                    "--resolution-digest",
                    digest,
                    "--herdr-start",
                    str(start),
                ],
                env,
            ).stdout
        )
        assert verified["verified"] is True
        assert verified["expected"]["model"] == "deepseek-v4-flash"

        fallback_start = temp / "fallback-start.json"
        fallback_start.write_text(
            json.dumps(
                {
                    "id": "cli:agent:start",
                    "result": {
                        "type": "agent_started",
                        "argv": ["pi", *fallback["piArgs"]],
                        "agent": {
                            "agent": "pi",
                            "agent_status": "idle",
                            "interactive_ready": True,
                            "name": "fallback-test",
                            "pane_id": "w1:p3",
                            "tab_id": "w1:t1",
                            "agent_session": {
                                "agent": "pi",
                                "source": "herdr:pi",
                                "kind": "path",
                                "value": "/tmp/fallback-test-session.jsonl",
                            },
                        },
                    },
                },
                indent=2,
            )
            + "\n"
        )
        fallback_verified = json.loads(
            run(
                [
                    "python3",
                    str(ROUTER),
                    "verify-launch",
                    "--resolution",
                    str(fallback_path),
                    "--resolution-digest",
                    fallback_digest,
                    "--herdr-start",
                    str(fallback_start),
                ],
                env,
            ).stdout
        )
        assert fallback_verified["verified"] is True
        assert fallback_verified["expected"]["model"] == "glm-5.3"
        print("PASS: chained automatic fallback, fail-closed pins and partial work, review escalation, and launch verification")
    finally:
        shutil.rmtree(temp)


if __name__ == "__main__":
    main()
