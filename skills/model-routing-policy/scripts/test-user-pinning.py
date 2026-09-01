#!/usr/bin/env python3
"""Regression checks for explicit user-pinned model routing."""

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
            "'opencode-go deepseek-v4-flash 128k'\n",
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
        assert pinned["policyVersion"] == 3
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
        assert automatic["piArgs"] == [
            "--provider",
            "opencode-go",
            "--model",
            "deepseek-v4-flash",
            "--thinking",
            "high",
        ]

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
        print("PASS: automatic and user-pinned routing, rejection, no-fallback, review escalation, and launch verification")
    finally:
        shutil.rmtree(temp)


if __name__ == "__main__":
    main()
