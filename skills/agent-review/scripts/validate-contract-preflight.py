#!/usr/bin/env python3
"""Validate Grill Me contracts and evidence before independent review."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import struct
import zlib
from pathlib import Path
from typing import Any

HEX64 = re.compile(r"[0-9a-f]{64}$")
FEATURE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*$")
ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]*$")


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        fail(f"{label} must use exactly: {', '.join(sorted(keys))}")
    return value


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def artifact(root: Path, value: Any, label: str, suffixes: set[str] | None = None) -> tuple[Path, str]:
    item = exact(value, {"path", "sha256"}, label)
    relative, expected = item["path"], item["sha256"]
    if not nonempty(relative) or not HEX64.fullmatch(str(expected)):
        fail(f"{label} requires a repository-relative path and SHA-256")
    normalized = posixpath.normpath(relative.replace("\\", "/"))
    if normalized in {".", ".."} or normalized.startswith("/") or normalized.startswith("../"):
        fail(f"{label} escapes the repository")
    current = root
    for part in Path(normalized).parts:
        current /= part
        if current.is_symlink():
            fail(f"{label} cannot traverse a symbolic link")
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        fail(f"{label} escapes the repository")
    if not candidate.is_file() or digest(candidate) != expected:
        fail(f"{label} is missing or stale: {normalized}")
    if suffixes and candidate.suffix.lower() not in suffixes:
        fail(f"{label} has an unsupported file type")
    return candidate, normalized


def json_artifact(root: Path, value: Any, label: str) -> tuple[dict[str, Any], str]:
    path, relative = artifact(root, value, label, {".json"})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    except json.JSONDecodeError as error:
        fail(f"{label} is invalid JSON: {error}")
    if not isinstance(payload, dict):
        fail(f"{label} must contain a JSON object")
    return payload, relative


def discovered(root: Path, feature: str, kind: str, filename: str) -> list[str]:
    base = root / "var" / feature / kind
    if not base.is_dir():
        return []
    return sorted(path.parent.name for path in base.glob(f"*/{filename}") if path.is_file() and not path.is_symlink())


def select_lane(root: Path, feature: str, value: Any, label: str, actual: list[str], kind: str, filename: str) -> tuple[str | None, dict[str, str] | None, Path | None]:
    lane = exact(value, {"candidates", "selected", "selectionBasis", "selectionEvidence", "reason", "contract"}, label)
    if lane["candidates"] != actual:
        fail(f"{label}.candidates does not match discovered sessions")
    if not actual:
        if lane["selected"] is not None or lane["selectionBasis"] != "none" or lane["selectionEvidence"] is not None or lane["contract"] is not None or not nonempty(lane["reason"]):
            fail(f"{label} must explicitly document no applicable session")
        return None, None, None
    selected = lane["selected"]
    if selected not in actual:
        fail(f"{label}.selected must name a discovered session")
    if len(actual) > 1:
        if lane["selectionBasis"] != "explicit-user":
            fail(f"{label} is ambiguous and requires explicit-user selection")
        selection, _ = json_artifact(root, lane["selectionEvidence"], f"{label}.selectionEvidence")
        if selection != {"featureName": feature, "kind": kind, "selected": selected}:
            fail(f"{label}.selectionEvidence does not select this feature, kind, and session")
    elif lane["selectionBasis"] != "single-candidate" or lane["selectionEvidence"] is not None:
        fail(f"{label} single candidate selection is invalid")
    expected = f"var/{feature}/{kind}/{selected}/{filename}"
    contract_path, relative = artifact(root, lane["contract"], f"{label}.contract", {".md"})
    if relative != expected:
        fail(f"{label}.contract must be {expected}")
    return selected, lane["contract"], contract_path


def table_ids(text: str, heading: str) -> set[str]:
    marker = f"## {heading}"
    count = text.count(marker)
    if count > 1:
        fail(f"contract repeats the {heading} heading")
    if count == 0:
        return set()
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    result: set[str] = set()
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        first = cells[0] if cells else ""
        if first.lower() == "id" or (first and set(first) <= {"-", ":"}):
            continue
        if not ID.fullmatch(first):
            fail(f"{heading} contains a malformed branch row: {line.strip()}")
        if first in result:
            fail(f"{heading} contains duplicate branch ID {first}")
        result.add(first)
    return result


def contract_inventory(path: Path, label: str) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    open_ids = table_ids(text, "Open branches")
    blocked_ids = table_ids(text, "Blocked (needs user)")
    if open_ids or blocked_ids:
        unresolved = sorted(open_ids | blocked_ids)
        fail(f"{label} still has unresolved branches: {', '.join(unresolved)}")
    resolved = table_ids(text, "Resolved branches")
    deferred = table_ids(text, "Deferred")
    if not resolved and not deferred:
        fail(f"{label} has no resolved or deferred branches")
    overlap = resolved & deferred
    if overlap:
        fail(f"{label} repeats branch IDs across resolved and deferred sections")
    return {**{item: "resolved" for item in resolved}, **{item: "deferred" for item in deferred}}


def validate_decisions(root: Path, values: Any, fingerprint: str, contract: dict[str, str] | None, inventory: dict[str, str] | None) -> tuple[int, int]:
    if inventory is None:
        if values != []:
            fail("grillDecisions require a selected Grill Me session")
        return 0, 0
    if not isinstance(values, list):
        fail("grillDecisions must be a list")
    mapped: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(values):
        item = exact(raw, {"id", "status", "contract", "functionality"}, f"grillDecisions[{index}]")
        if item["id"] in mapped:
            fail("grillDecisions contains duplicate IDs")
        mapped[item["id"]] = item
    if {key: value["status"] for key, value in mapped.items()} != inventory:
        fail("grillDecisions must exactly cover resolved and deferred contract branches")
    for decision_id, item in mapped.items():
        if item["contract"] != contract:
            fail(f"Grill Me decision {decision_id} is not bound to the selected contract")
        if item["status"] == "deferred":
            if item["functionality"] is not None:
                fail("deferred Grill Me decisions cannot claim passing evidence")
            continue
        evidence = exact(item["functionality"], {"status", "fingerprint", "summary", "evidence"}, f"functionality {decision_id}")
        if evidence["status"] != "pass" or evidence["fingerprint"] != fingerprint or not nonempty(evidence["summary"]) or not isinstance(evidence["evidence"], list) or not evidence["evidence"]:
            fail(f"resolved Grill Me decision {decision_id} lacks current passing evidence")
        for index, reference in enumerate(evidence["evidence"]):
            report, _ = json_artifact(root, reference, f"functionality {decision_id} evidence[{index}]")
            report = exact(report, {"status", "fingerprint", "decisionId", "command", "exitCode", "output"}, f"functionality report {decision_id}")
            if report["status"] != "pass" or report["fingerprint"] != fingerprint or report["decisionId"] != decision_id or not nonempty(report["command"]) or isinstance(report["exitCode"], bool) or report["exitCode"] != 0:
                fail(f"functionality report {decision_id} is not a current passing run")
            artifact(root, report["output"], f"functionality report {decision_id} output")
    resolved = sum(status == "resolved" for status in inventory.values())
    return resolved, len(inventory) - resolved


def valid_viewport(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"width", "height"}
        and all(isinstance(value[key], int) and not isinstance(value[key], bool) and 0 < value[key] <= 16384 for key in ("width", "height"))
        and value["width"] * value["height"] <= 50_000_000
    )


def png_size(path: Path, label: str) -> tuple[int, int]:
    if path.stat().st_size > 50 * 1024 * 1024:
        fail(f"{label} exceeds the PNG size limit")
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        fail(f"{label} is not a valid PNG")
    offset, width, height, bit_depth, color_type, compressed, ended, seen_header, seen_idat, idat_closed = 8, 0, 0, 0, 0, bytearray(), False, False, False, False
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            fail(f"{label} has a truncated PNG chunk")
        payload = data[offset + 8:offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length:end])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected_crc:
            fail(f"{label} has an invalid PNG checksum")
        if kind not in {b"IHDR", b"PLTE", b"IDAT", b"IEND"} and kind[:1].isupper():
            fail(f"{label} contains an unknown critical PNG chunk")
        if seen_idat and kind not in {b"IDAT", b"IEND"}:
            idat_closed = True
        if offset == 8 and kind != b"IHDR":
            fail(f"{label} does not start with a PNG header chunk")
        if kind == b"IHDR" and length == 13:
            if seen_header:
                fail(f"{label} repeats its PNG header")
            seen_header = True
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if width <= 0 or height <= 0 or width > 16384 or height > 16384 or width * height > 50_000_000:
                fail(f"{label} exceeds PNG dimension limits")
            if bit_depth != 8 or color_type not in {2, 6} or compression != 0 or filtering != 0 or interlace != 0:
                fail(f"{label} uses an unsupported PNG encoding")
        elif kind == b"IDAT":
            if not width or idat_closed:
                fail(f"{label} contains misplaced PNG image data")
            seen_idat = True
            compressed.extend(payload)
        elif kind == b"IEND":
            if length != 0 or not compressed or end != len(data):
                fail(f"{label} has an invalid PNG end chunk")
            ended = True
            break
        offset = end
    bytes_per_pixel = 3 if color_type == 2 else 4
    expected_size = height * (1 + width * bytes_per_pixel)
    try:
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(bytes(compressed), expected_size + 1)
        if decoder.unconsumed_tail:
            fail(f"{label} expands beyond its declared dimensions")
        pixels += decoder.flush(max(1, expected_size + 1 - len(pixels)))
    except zlib.error:
        fail(f"{label} has invalid PNG image data")
    row_size = 1 + width * bytes_per_pixel
    if (
        width <= 0 or height <= 0 or not ended or not decoder.eof or decoder.unused_data
        or len(pixels) != expected_size
        or any(pixels[index * row_size] > 4 for index in range(height))
    ):
        fail(f"{label} has invalid PNG dimensions or scanlines")
    return width, height


def validate_branches(root: Path, feature: str, values: Any, fingerprint: str, session_slug: str | None, contract: dict[str, str] | None, inventory: dict[str, str] | None) -> tuple[int, int]:
    if inventory is None:
        if values != []:
            fail("uiBranches require a selected UI/UX session")
        return 0, 0
    if not isinstance(values, list):
        fail("uiBranches must be a list")
    mapped: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(values):
        item = exact(raw, {"id", "status", "contract", "visualParity"}, f"uiBranches[{index}]")
        if item["id"] in mapped:
            fail("uiBranches contains duplicate IDs")
        mapped[item["id"]] = item
    if {key: value["status"] for key, value in mapped.items()} != inventory:
        fail("uiBranches must exactly cover resolved and deferred contract branches")
    parity_keys = {"status", "fingerprint", "route", "viewport", "fixture", "interactionState", "theme", "container", "selectedSource", "selectedSourceArtifact", "requiredBehavior", "accessibility", "userModifications", "selectedScreenshot", "implementedScreenshot", "selectionEvidence", "comparisonReport", "userModificationsHonored"}
    for branch_id, item in mapped.items():
        if item["contract"] != contract:
            fail(f"UI/UX branch {branch_id} is not bound to the selected contract")
        if item["status"] == "deferred":
            if item["visualParity"] is not None:
                fail("deferred UI/UX branches cannot claim passing evidence")
            continue
        parity = exact(item["visualParity"], parity_keys, f"visualParity {branch_id}")
        if (
            parity["status"] != "pass"
            or parity["fingerprint"] != fingerprint
            or parity["userModificationsHonored"] is not True
            or not valid_viewport(parity["viewport"])
            or not all(nonempty(parity[key]) for key in ("route", "fixture", "interactionState", "theme", "container"))
            or not isinstance(parity["selectedSource"], dict)
            or set(parity["selectedSource"]) != {"kind", "path", "viewport", "route"}
            or parity["selectedSource"].get("kind") not in {"live-route", "mockup-html"}
            or not nonempty(parity["selectedSource"].get("path"))
            or not nonempty(parity["selectedSource"].get("viewport"))
            or (
                parity["selectedSource"].get("kind") == "live-route"
                and parity["selectedSource"].get("route") != parity["route"]
            )
            or (
                parity["selectedSource"].get("kind") == "mockup-html"
                and parity["selectedSource"].get("route") is not None
            )
            or not isinstance(parity["userModifications"], str)
            or not isinstance(parity["requiredBehavior"], list) or not parity["requiredBehavior"]
            or not isinstance(parity["accessibility"], list) or not parity["accessibility"]
            or any(not nonempty(item) for item in [*parity["requiredBehavior"], *parity["accessibility"]])
        ):
            fail(f"resolved UI/UX branch {branch_id} lacks current exact-state parity")
        source_kind = parity["selectedSource"]["kind"]
        if source_kind == "mockup-html":
            source_path = parity["selectedSource"]["path"].replace("\\", "/")
            if source_path.startswith("/") or source_path.startswith("../") or posixpath.normpath(source_path) != source_path:
                fail("selected mockup source must stay inside the UI/UX session")
            _, source_relative = artifact(root, parity["selectedSourceArtifact"], "selectedSourceArtifact")
            expected_source = f"var/{feature}/ui-ux-grill-me/{session_slug}/{source_path}"
            if source_relative != posixpath.normpath(expected_source):
                fail("selectedSourceArtifact does not bind the selected mockup source")
        elif parity["selectedSourceArtifact"] is not None:
            fail("live-route selected sources cannot claim a file artifact")
        selected, _ = artifact(root, parity["selectedScreenshot"], "selectedScreenshot", {".png"})
        implemented, _ = artifact(root, parity["implementedScreenshot"], "implementedScreenshot", {".png"})
        if selected == implemented:
            fail("selected and implemented screenshots must be distinct")
        expected_size = (parity["viewport"]["width"], parity["viewport"]["height"])
        if png_size(selected, "selectedScreenshot") != expected_size or png_size(implemented, "implementedScreenshot") != expected_size:
            fail("screenshots do not match the exact viewport")
        selection, _ = json_artifact(root, parity["selectionEvidence"], "selectionEvidence")
        visual_contract = selection.get("visualContract") or {}
        selected_contract = visual_contract.get("contract") or {}
        expected_contract = {
            "route": parity["route"], "fixture": parity["fixture"],
            "interactionState": parity["interactionState"], "theme": parity["theme"],
            "container": parity["container"], "requiredBehavior": parity["requiredBehavior"],
            "accessibility": parity["accessibility"],
        }
        source_viewport = str(parity["selectedSource"]["viewport"]).lower().replace("×", "x").replace(" ", "")
        expected_viewport = f"{parity['viewport']['width']}x{parity['viewport']['height']}"
        selected_relative = parity["selectedScreenshot"]["path"]
        session_prefix = f"var/{feature}/ui-ux-grill-me/{session_slug}/"
        contract_screenshot = str(visual_contract.get("screenshot", "")).replace("\\", "/").lstrip("./")
        if (
            selection.get("questionId") != branch_id
            or selection.get("sessionSlug") != session_slug
            or selection.get("submissionType") != "selection"
            or not nonempty(selection.get("selected"))
            or not nonempty(selection.get("label"))
            or selection.get("why") != parity["userModifications"]
            or visual_contract.get("branch") != branch_id
            or visual_contract.get("variantId") != selection.get("selected")
            or visual_contract.get("label") != selection.get("label")
            or visual_contract.get("source") != parity["selectedSource"]
            or visual_contract.get("sourceArtifact") != parity["selectedSourceArtifact"]
            or selected_contract != expected_contract
            or source_viewport != expected_viewport
            or not selected_relative.startswith(session_prefix)
            or selected_relative[len(session_prefix):] != contract_screenshot
        ):
            fail("selectionEvidence does not bind the selected UI branch, source, viewport, and screenshot")
        comparison, _ = json_artifact(root, parity["comparisonReport"], "comparisonReport")
        comparison = exact(comparison, {"status", "fingerprint", "branchId", "route", "viewport", "fixture", "interactionState", "theme", "container", "selectedSource", "selectedSourceArtifact", "requiredBehavior", "accessibility", "userModifications", "selectedScreenshot", "implementedScreenshot", "userModificationsHonored"}, "comparisonReport")
        if comparison != {
            "status": "pass", "fingerprint": fingerprint, "branchId": branch_id,
            "route": parity["route"], "viewport": parity["viewport"],
            "fixture": parity["fixture"], "interactionState": parity["interactionState"],
            "theme": parity["theme"], "container": parity["container"],
            "selectedSource": parity["selectedSource"],
            "selectedSourceArtifact": parity["selectedSourceArtifact"],
            "requiredBehavior": parity["requiredBehavior"],
            "accessibility": parity["accessibility"],
            "userModifications": parity["userModifications"],
            "selectedScreenshot": parity["selectedScreenshot"],
            "implementedScreenshot": parity["implementedScreenshot"],
            "userModificationsHonored": True,
        }:
            fail("comparisonReport does not bind a passing exact-state comparison")
    resolved = sum(status == "resolved" for status in inventory.values())
    return resolved, len(inventory) - resolved


def validate_user_live(root: Path, value: Any) -> str:
    item = exact(value, {"status", "reason", "evidence"}, "userLiveTest")
    if item["status"] not in {"pass", "pending", "not-required"} or not nonempty(item["reason"]):
        fail("userLiveTest status or reason is invalid")
    if item["status"] == "pass":
        artifact(root, item["evidence"], "userLiveTest.evidence")
    elif item["evidence"] is not None:
        fail("pending or not-required userLiveTest cannot claim pass evidence")
    return item["status"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--feature-name", required=True)
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir() or not (root / ".git").exists() or not FEATURE.fullmatch(args.feature_name) or not HEX64.fullmatch(args.fingerprint):
        fail("repository, feature name, or fingerprint is invalid")
    canonical = (root / "var" / args.feature_name / "implement" / "contract-review-pack.json").resolve()
    requested = Path(args.pack)
    pack_path = (requested if requested.is_absolute() else Path.cwd() / requested).resolve()
    if pack_path != canonical or not pack_path.is_file() or pack_path.is_symlink():
        fail("contract pack must use the canonical implementation-run path")
    try:
        pack = json.loads(pack_path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    except json.JSONDecodeError as error:
        fail(f"contract pack is invalid JSON: {error}")
    pack = exact(pack, {"version", "reviewFingerprint", "featureName", "discovery", "grillDecisions", "uiBranches", "userLiveTest"}, "contract pack")
    if pack["version"] != 1 or pack["featureName"] != args.feature_name or pack["reviewFingerprint"] != args.fingerprint:
        fail("contract pack identity or fingerprint is stale")
    discovery = exact(pack["discovery"], {"grillMe", "uiUxGrillMe", "ambiguities"}, "discovery")
    if discovery["ambiguities"] != []:
        fail("contract discovery has unresolved ambiguities")
    grill_slug, grill_ref, grill_path = select_lane(root, args.feature_name, discovery["grillMe"], "discovery.grillMe", discovered(root, args.feature_name, "grill-me", "decision-tree.md"), "grill-me", "decision-tree.md")
    ui_slug, ui_ref, ui_path = select_lane(root, args.feature_name, discovery["uiUxGrillMe"], "discovery.uiUxGrillMe", discovered(root, args.feature_name, "ui-ux-grill-me", "visual-decision-tree.md"), "ui-ux-grill-me", "visual-decision-tree.md")
    grill_inventory = contract_inventory(grill_path, "selected Grill Me contract") if grill_path else None
    ui_inventory = contract_inventory(ui_path, "selected UI/UX contract") if ui_path else None
    grill_resolved, grill_deferred = validate_decisions(root, pack["grillDecisions"], args.fingerprint, grill_ref, grill_inventory)
    ui_resolved, ui_deferred = validate_branches(root, args.feature_name, pack["uiBranches"], args.fingerprint, ui_slug, ui_ref, ui_inventory)
    result = {
        "valid": True,
        "version": 1,
        "reviewFingerprint": args.fingerprint,
        "featureName": args.feature_name,
        "sessions": {"grillMe": grill_slug, "uiUxGrillMe": ui_slug},
        "decisions": {"grillResolved": grill_resolved, "grillDeferred": grill_deferred, "uiResolved": ui_resolved, "uiDeferred": ui_deferred},
        "userLiveTest": validate_user_live(root, pack["userLiveTest"]),
        "pack": {"path": pack_path.relative_to(root).as_posix(), "sha256": digest(pack_path)},
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
