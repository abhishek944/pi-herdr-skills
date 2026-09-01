#!/usr/bin/env python3
"""Regression checks for contract-aware review preflight."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

VALIDATOR = Path(__file__).resolve().with_name("validate-contract-preflight.py")
FINGERPRINT = "a" * 64


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def ref(root: Path, relative: str) -> dict[str, str]:
    return {"path": relative, "sha256": hashlib.sha256((root / relative).read_bytes()).hexdigest()}


def png(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    rows = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def write_bytes(root: Path, relative: str, content: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def lane(candidates, selected, basis, reason, contract=None, selection=None):
    return {"candidates": candidates, "selected": selected, "selectionBasis": basis, "selectionEvidence": selection, "reason": reason, "contract": contract}


def run(root: Path, feature: str, pack: dict, passes: bool) -> subprocess.CompletedProcess[str]:
    pack_path = root / "var" / feature / "implement" / "contract-review-pack.json"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(json.dumps(pack, indent=2) + "\n")
    result = subprocess.run(
        ["python3", str(VALIDATOR), "--pack", str(pack_path), "--repo-root", str(root), "--feature-name", feature, "--fingerprint", FINGERPRINT],
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if passes and result.returncode:
        raise AssertionError(result.stderr + result.stdout)
    if not passes and not result.returncode:
        raise AssertionError("invalid pack unexpectedly passed")
    return result


def no_contract(feature: str) -> dict:
    return {
        "version": 1,
        "reviewFingerprint": FINGERPRINT,
        "featureName": feature,
        "discovery": {
            "grillMe": lane([], None, "none", "No Grill Me session applies."),
            "uiUxGrillMe": lane([], None, "none", "No UI/UX session applies."),
            "ambiguities": [],
        },
        "grillDecisions": [],
        "uiBranches": [],
        "userLiveTest": {"status": "not-required", "reason": "No live test applies.", "evidence": None},
    }


def applicable(root: Path, feature: str) -> dict:
    grill = f"var/{feature}/grill-me/g1/decision-tree.md"
    ui = f"var/{feature}/ui-ux-grill-me/u1/visual-decision-tree.md"
    evidence = f"var/{feature}/evidence"
    write(root, grill, "# Decisions\n\n## Open branches\n\n| ID | Branch | Status |\n|---|---|---|\n\n## Resolved branches\n\n| ID | Decision |\n|---|---|\n| G1 | Fast checkout |\n\n## Deferred\n\n| ID | Reason |\n|---|---|\n| G2 | Later |\n")
    write(root, ui, "# Visual decisions\n\n## Open branches\n\n| ID | Branch | Status |\n|---|---|---|\n\n## Resolved branches\n\n| ID | Choice |\n|---|---|\n| V1 | Compact layout |\n\n## Deferred\n\n| ID | Reason |\n|---|---|\n")
    write(root, f"{evidence}/functional-output.txt", "checkout passed\n")
    functional_report = {"status": "pass", "fingerprint": FINGERPRINT, "decisionId": "G1", "command": "test checkout", "exitCode": 0, "output": ref(root, f"{evidence}/functional-output.txt")}
    write(root, f"{evidence}/functional.json", json.dumps(functional_report))
    selected_relative = f"var/{feature}/ui-ux-grill-me/u1/screenshots/selected.png"
    write_bytes(root, selected_relative, png(4, 3, (255, 0, 0)))
    write_bytes(root, f"{evidence}/implemented.png", png(4, 3, (254, 0, 0)))
    selected_source = {"kind": "mockup-html", "path": "variants/B.html", "viewport": "4x3", "route": None}
    write(root, f"var/{feature}/ui-ux-grill-me/u1/variants/B.html", "<!doctype html><title>B</title>")
    source_artifact = ref(root, f"var/{feature}/ui-ux-grill-me/u1/variants/B.html")
    selected_contract = {"route": "/checkout", "fixture": "two-items", "interactionState": "payment-open", "theme": "light", "container": "full viewport", "requiredBehavior": ["Total remains visible"], "accessibility": ["Keyboard reachable"]}
    selection = {"questionId": "V1", "sessionSlug": "u1", "selected": "B", "label": "Compact", "submissionType": "selection", "why": "Keep total visible", "visualContract": {"branch": "V1", "variantId": "B", "label": "Compact", "screenshot": "screenshots/selected.png", "source": selected_source, "sourceArtifact": source_artifact, "contract": selected_contract}, "timestamp": "2026-01-01T00:00:00Z"}
    write(root, f"{evidence}/selection.json", json.dumps(selection))
    grill_ref, ui_ref = ref(root, grill), ref(root, ui)
    visual = {
        "status": "pass", "fingerprint": FINGERPRINT, "route": "/checkout", "viewport": {"width": 4, "height": 3},
        "fixture": "two-items", "interactionState": "payment-open", "theme": "light", "container": "full viewport",
        "selectedSource": selected_source, "selectedSourceArtifact": source_artifact, "requiredBehavior": ["Total remains visible"], "accessibility": ["Keyboard reachable"],
        "userModifications": "Keep total visible", "selectedScreenshot": ref(root, selected_relative), "implementedScreenshot": ref(root, f"{evidence}/implemented.png"),
        "selectionEvidence": ref(root, f"{evidence}/selection.json"), "comparisonReport": None, "userModificationsHonored": True,
    }
    comparison = {key: visual[key] for key in ("status", "fingerprint", "route", "viewport", "fixture", "interactionState", "theme", "container", "selectedSource", "selectedSourceArtifact", "requiredBehavior", "accessibility", "userModifications", "selectedScreenshot", "implementedScreenshot", "userModificationsHonored")}
    comparison["branchId"] = "V1"
    write(root, f"{evidence}/comparison.json", json.dumps(comparison))
    visual["comparisonReport"] = ref(root, f"{evidence}/comparison.json")
    return {
        "version": 1,
        "reviewFingerprint": FINGERPRINT,
        "featureName": feature,
        "discovery": {
            "grillMe": lane(["g1"], "g1", "single-candidate", "Only candidate", grill_ref),
            "uiUxGrillMe": lane(["u1"], "u1", "single-candidate", "Only candidate", ui_ref),
            "ambiguities": [],
        },
        "grillDecisions": [
            {"id": "G1", "status": "resolved", "contract": grill_ref, "functionality": {"status": "pass", "fingerprint": FINGERPRINT, "summary": "Checkout behavior passed", "evidence": [ref(root, f"{evidence}/functional.json")]}},
            {"id": "G2", "status": "deferred", "contract": grill_ref, "functionality": None},
        ],
        "uiBranches": [{
            "id": "V1",
            "status": "resolved",
            "contract": ui_ref,
            "visualParity": visual,
        }],
        "userLiveTest": {"status": "pending", "reason": "User-owned live test remains.", "evidence": None},
    }


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="contract-preflight-"))
    try:
        (root / ".git").mkdir()
        run(root, "no-contract", no_contract("no-contract"), True)
        pack = applicable(root, "checkout")
        result = json.loads(run(root, "checkout", pack, True).stdout)
        assert result["decisions"] == {"grillResolved": 1, "grillDeferred": 1, "uiResolved": 1, "uiDeferred": 0}

        wrong_feature = copy.deepcopy(pack)
        wrong_feature["featureName"] = "alias"
        run(root, "checkout", wrong_feature, False)

        omitted = copy.deepcopy(pack)
        omitted["grillDecisions"] = omitted["grillDecisions"][:1]
        run(root, "checkout", omitted, False)

        stale = copy.deepcopy(pack)
        write(root, "var/checkout/evidence/functional.json", "{\"status\": \"fail\"}\n")
        run(root, "checkout", stale, False)

        pack = applicable(root, "checkout")
        write(root, "var/checkout/grill-me/g2/decision-tree.md", "# Another session\n")
        ambiguous = copy.deepcopy(pack)
        ambiguous["discovery"]["grillMe"]["candidates"] = ["g1", "g2"]
        run(root, "checkout", ambiguous, False)
        write(root, "var/checkout/evidence/user-selection.json", json.dumps({"featureName": "checkout", "kind": "grill-me", "selected": "g1"}))
        explicit = copy.deepcopy(ambiguous)
        explicit["discovery"]["grillMe"]["selectionBasis"] = "explicit-user"
        explicit["discovery"]["grillMe"]["selectionEvidence"] = ref(root, "var/checkout/evidence/user-selection.json")
        run(root, "checkout", explicit, True)
        write(root, "var/checkout/evidence/user-selection.json", json.dumps({"featureName": "checkout", "kind": "grill-me", "selected": "g2"}))
        mismatched = copy.deepcopy(explicit)
        mismatched["discovery"]["grillMe"]["selectionEvidence"] = ref(root, "var/checkout/evidence/user-selection.json")
        run(root, "checkout", mismatched, False)

        duplicate = applicable(root, "duplicate-branches")
        tree_path = root / "var/duplicate-branches/grill-me/g1/decision-tree.md"
        tree_path.write_text(tree_path.read_text().replace("| G1 | Fast checkout |", "| G1 | Fast checkout |\n| G1 | Duplicate |"))
        tree_ref = ref(root, "var/duplicate-branches/grill-me/g1/decision-tree.md")
        duplicate["discovery"]["grillMe"]["contract"] = tree_ref
        for decision in duplicate["grillDecisions"]:
            decision["contract"] = tree_ref
        run(root, "duplicate-branches", duplicate, False)

        boolean_exit = applicable(root, "boolean-exit")
        report_path = root / "var/boolean-exit/evidence/functional.json"
        report = json.loads(report_path.read_text())
        report["exitCode"] = False
        report_path.write_text(json.dumps(report))
        boolean_exit["grillDecisions"][0]["functionality"]["evidence"] = [ref(root, "var/boolean-exit/evidence/functional.json")]
        run(root, "boolean-exit", boolean_exit, False)

        blocked = applicable(root, "blocked-branches")
        blocked_tree = root / "var/blocked-branches/grill-me/g1/decision-tree.md"
        blocked_tree.write_text(blocked_tree.read_text() + "\n## Blocked (needs user)\n\n| ID | Blocker |\n|---|---|\n| B9 | User decision |\n")
        blocked_ref = ref(root, "var/blocked-branches/grill-me/g1/decision-tree.md")
        blocked["discovery"]["grillMe"]["contract"] = blocked_ref
        for decision in blocked["grillDecisions"]:
            decision["contract"] = blocked_ref
        run(root, "blocked-branches", blocked, False)

        spec = importlib.util.spec_from_file_location("contract_validator", VALIDATOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        malformed = root / "malformed.png"
        malformed.write_bytes(png(1, 1, (1, 2, 3))[:33] + png(1, 1, (1, 2, 3))[-12:])
        try:
            module.png_size(malformed, "malformed")
            raise AssertionError("malformed PNG unexpectedly passed")
        except SystemExit:
            pass
        print("PASS: feature binding, strict branches, structured evidence, ambiguity selection, blocked branches, and PNG gates")
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    main()
