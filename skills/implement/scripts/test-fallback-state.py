#!/usr/bin/env python3
"""Focused regression checks for evidence-bound implementation fallback state."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("state-store.py")
SPEC = importlib.util.spec_from_file_location("implement_state_store", MODULE_PATH)
assert SPEC and SPEC.loader
store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(store)


def write(path: Path, value: dict[str, object]) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return {
        "path": path.relative_to(path.parents[1]).as_posix(),
        "digest": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="implement-fallback-state-"))
    try:
        run = root / "var" / "fallback-test" / "implement"
        outputs = run / "outputs"
        state = {
            "feature_name": "fallback-test",
            "run": {"repo_root": str(root)},
            "tasks": {},
        }
        zone = {
            "taskClass": "exploration",
            "inputTypes": ["text"],
            "minimumQualityRank": 1,
            "thinking": None,
            "noContributor": False,
            "strongerThan": [],
            "strongerThanThinking": [],
            "selectionMode": "automatic",
            "userModel": None,
            "userModelAuthority": None,
        }
        previous_payload = {
            "request": {**zone, "excludedModels": [], "fallbackFrom": None},
            "selection": {"provider": "provider-a", "modelId": "model-a"},
        }
        previous = write(outputs / "previous.json", previous_payload)
        launch = write(
            outputs / "launch.json",
            {
                "verified": True,
                "expected": {
                    "provider": "provider-a",
                    "model": "model-a",
                    "thinking": "high",
                },
                "evidence": {
                    "sessionIdentity": "session-a",
                    "resolutionArtifact": {"digest": previous["digest"]},
                },
            },
        )
        runtime_output = write(outputs / "runtime-output.json", {"error": "quota"})
        closure_response = write(
            outputs / "pane-close.json",
            {"id": "cli:pane:close", "result": {"type": "ok"}},
        )
        absence_response = write(
            outputs / "pane-absent.json",
            {
                "id": "cli:pane:get",
                "error": {
                    "code": "pane_not_found",
                    "message": "pane w1:p2 not found",
                },
            },
        )
        failure_payload = {
            "classification": "model-specific-no-contribution",
            "reasonCode": "quota",
            "failedModel": "provider-a/model-a",
            "agentSessionId": "session-a",
            "paneId": "w1:p2",
            "usableContribution": False,
            "sideEffects": False,
            "launchVerification": {
                "path": str((run / launch["path"]).resolve()),
                "digest": launch["digest"],
            },
            "runtimeOutput": {
                "path": str((run / runtime_output["path"]).resolve()),
                "digest": runtime_output["digest"],
            },
        }
        failure = write(outputs / "failure.json", failure_payload)
        cleanup_payload = {
            "agentSessionId": "session-a",
            "paneId": "w1:p2",
            "agentStopped": True,
            "paneClosed": True,
            "remainingActive": False,
            "closureResponse": {
                "path": str((run / closure_response["path"]).resolve()),
                "digest": closure_response["digest"],
            },
            "absenceResponse": {
                "path": str((run / absence_response["path"]).resolve()),
                "digest": absence_response["digest"],
            },
        }
        cleanup = write(outputs / "cleanup.json", cleanup_payload)
        fallback_payload = {
            "request": {
                **zone,
                "excludedModels": ["provider-a/model-a"],
                "fallbackFrom": {
                    "previousResolution": {
                        "path": str((run / previous["path"]).resolve()),
                        "digest": previous["digest"],
                    },
                    "failureEvidence": {
                        "path": str((run / failure["path"]).resolve()),
                        "digest": failure["digest"],
                    },
                    "cleanupEvidence": {
                        "path": str((run / cleanup["path"]).resolve()),
                        "digest": cleanup["digest"],
                    },
                },
            }
        }
        fallback = write(outputs / "fallback.json", fallback_payload)
        task = {
            "id": "task-0002",
            "attempts": 1,
            "active_resolution": previous,
            "active_model": {
                "provider": "provider-a",
                "model_id": "model-a",
            },
            "runtime": {
                "agent_instance_id": "session-a",
                "pane_id": "w1:p2",
                "launch_verification": launch,
                "output_path": runtime_output["path"],
                "output_digest": runtime_output["digest"],
            },
        }
        state["tasks"] = {
            "task-0001": {
                "runtime_intents": [
                    {
                        "id": "intent-pane-a",
                        "target_task_id": "task-0002",
                        "attempt": 1,
                    }
                ],
                "runtime_resources": [
                    {
                        "intent_id": "intent-pane-a",
                        "status": "closed",
                        "closure_artifact": closure_response["path"],
                        "closure_digest": closure_response["digest"],
                    }
                ],
            },
            "task-0002": {**task, "runtime_intents": [], "runtime_resources": []},
        }
        failure_ref, cleanup_ref = store.validate_fallback_evidence(
            state, task, fallback
        )
        assert failure_ref == failure
        assert cleanup_ref == cleanup
        assert store.HARD_LIMITS["max_retries_per_task"] == 31

        changed_zone = json.loads(json.dumps(fallback_payload))
        changed_zone["request"]["taskClass"] = "review"
        changed_zone_ref = write(outputs / "changed-zone.json", changed_zone)
        try:
            store.validate_fallback_evidence(state, task, changed_zone_ref)
        except SystemExit:
            pass
        else:
            raise AssertionError("changed routing zone was accepted")

        partial = dict(failure_payload)
        partial["usableContribution"] = True
        partial_ref = write(outputs / "partial.json", partial)
        partial_resolution = json.loads(json.dumps(fallback_payload))
        partial_resolution["request"]["fallbackFrom"]["failureEvidence"] = {
            "path": str((run / partial_ref["path"]).resolve()),
            "digest": partial_ref["digest"],
        }
        partial_resolution_ref = write(outputs / "partial-resolution.json", partial_resolution)
        try:
            store.validate_fallback_evidence(state, task, partial_resolution_ref)
        except SystemExit:
            pass
        else:
            raise AssertionError("partial contribution was accepted for fallback")

        print("PASS: implementation fallback state binds zone, failure, cleanup, session, and attempt budget")
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    main()
