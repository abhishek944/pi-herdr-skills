#!/usr/bin/env python3
"""Validate a versioned agent catalog, resolve a Pi launch, and verify provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

TASK_CLASSES = {
    "coordination",
    "architecture",
    "implementation",
    "exploration",
    "focused-edit",
    "multimodal",
    "integration",
    "review",
}
INPUT_TYPES = {"text", "image", "video", "audio", "pdf"}
THINKING_LEVELS = ("off", "minimal", "low", "medium", "high", "xhigh", "max")
THINKING_RANK = {value: index for index, value in enumerate(THINKING_LEVELS)}
REVIEW_TIER_RANK = {"basic": 1, "standard": 2, "strong": 3}
GLOBAL_MODEL_CATALOG = (
    Path.home() / ".pi" / "agent" / "skills" / "model-routing-policy" / "models.json"
)
CATALOG_VERSION_RE = re.compile(r"\d{4}-\d{2}-\d{2}$")


def fail(message: str, code: int = 1) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(code)


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def read_bound_bytes(path_value: str, digest: str, label: str) -> tuple[Path, bytes]:
    path = Path(path_value).expanduser().resolve()
    if not valid_digest(digest):
        fail(f"{label} requires a SHA-256 digest")
    try:
        if path.is_symlink() or not path.is_file():
            fail(f"{label} must be a regular non-symlink file")
        content = path.read_bytes()
        if not content or hashlib.sha256(content).hexdigest() != digest:
            fail(f"{label} is empty or its digest does not match")
    except OSError as error:
        fail(f"could not read {label}: {error}")
    return path, content


def read_bound_json(path_value: str, digest: str, label: str) -> tuple[Path, dict[str, Any]]:
    path, content = read_bound_bytes(path_value, digest, label)
    try:
        value = json.loads(content, object_pairs_hook=strict_object)
    except json.JSONDecodeError as error:
        fail(f"could not read {label}: {error}")
    if not isinstance(value, dict):
        fail(f"{label} must contain a JSON object")
    return path, value


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            fail(f"catalog contains duplicate JSON key: {key}")
        value[key] = item
    return value


def string_list(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not nonempty(item) for item in value)
    ):
        fail(f"{label} must be a non-empty string list")
    return value


def catalog_versions(data: dict[str, Any]) -> tuple[int, str]:
    schema_version = data.get("schemaVersion")
    catalog_version = data.get("catalogVersion")
    if schema_version != 1:
        fail("catalog schemaVersion must be 1")
    if not nonempty(catalog_version) or not CATALOG_VERSION_RE.fullmatch(
        catalog_version
    ):
        fail("catalog catalogVersion must use YYYY-MM-DD")
    return schema_version, catalog_version


def normalize_model(raw: Any, index: int) -> dict[str, Any]:
    label = f"models[{index}]"
    model_keys = {
        "provider",
        "modelId",
        "family",
        "independenceGroup",
        "capabilities",
        "thinking",
        "routing",
    }
    if not isinstance(raw, dict) or set(raw) != model_keys:
        fail(f"{label} must use exactly the canonical model fields")
    provider = raw["provider"]
    model_id = raw["modelId"]
    family = raw["family"]
    independence_group = raw["independenceGroup"]
    if not all(
        nonempty(value) for value in (provider, model_id, family, independence_group)
    ):
        fail(f"{label} requires provider, modelId, family, and independenceGroup")

    capabilities = raw["capabilities"]
    if not isinstance(capabilities, dict) or set(capabilities) != {
        "inputTypes",
        "taskClasses",
        "taskClassScores",
    }:
        fail(f"{label}.capabilities must use exactly the canonical fields")
    task_classes = string_list(
        capabilities["taskClasses"], f"{label}.capabilities.taskClasses"
    )
    if len(task_classes) != len(set(task_classes)) or any(
        value not in TASK_CLASSES for value in task_classes
    ):
        fail(
            f"{label}.capabilities.taskClasses contains duplicates or unsupported classes"
        )
    input_types = string_list(
        capabilities["inputTypes"], f"{label}.capabilities.inputTypes"
    )
    if len(input_types) != len(set(input_types)) or any(
        value not in INPUT_TYPES for value in input_types
    ):
        fail(
            f"{label}.capabilities.inputTypes contains duplicates or unsupported inputs"
        )
    class_scores = capabilities["taskClassScores"]
    if (
        not isinstance(class_scores, dict)
        or set(class_scores) != set(task_classes)
        or any(
            isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5
            for value in class_scores.values()
        )
    ):
        fail(
            f"{label}.capabilities.taskClassScores must rank every declared task class from 1 to 5"
        )

    thinking = raw["thinking"]
    if not isinstance(thinking, dict) or set(thinking) != {
        "supportedLevels",
        "recommendedLevel",
    }:
        fail(f"{label}.thinking must use exactly the canonical fields")
    levels = string_list(
        thinking["supportedLevels"], f"{label}.thinking.supportedLevels"
    )
    if len(levels) != len(set(levels)) or any(
        level not in THINKING_RANK for level in levels
    ):
        fail(
            f"{label}.thinking.supportedLevels contains duplicates or unsupported Pi levels"
        )
    default_level = thinking["recommendedLevel"]
    if default_level not in levels:
        fail(f"{label}.thinking.recommendedLevel must be supported")

    routing = raw["routing"]
    if (
        not isinstance(routing, dict)
        or set(routing) != {"reviewTier"}
        or routing["reviewTier"] not in REVIEW_TIER_RANK
    ):
        fail(
            f"{label}.routing.reviewTier must be the only routing field and use basic, standard, or strong"
        )

    return {
        "provider": provider,
        "modelId": model_id,
        "family": family,
        "independenceGroup": independence_group,
        "taskClasses": task_classes,
        "inputTypes": input_types,
        "qualityRank": REVIEW_TIER_RANK[routing["reviewTier"]],
        "reviewTier": routing["reviewTier"],
        "catalogOrder": index,
        "taskClassScores": class_scores,
        "thinkingLevels": levels,
        "defaultThinking": default_level,
        "thinkingByTaskClass": {},
    }


def trusted_catalog_path(path: Path) -> Path:
    requested = path.expanduser()
    if requested != GLOBAL_MODEL_CATALOG:
        fail(f"catalog path must be {GLOBAL_MODEL_CATALOG}")
    current = Path(requested.anchor)
    for part in requested.parts[1:]:
        current = current / part
        if current.is_symlink():
            fail("catalog path cannot contain symbolic links")
    return requested


def read_catalog_bytes(path: Path) -> bytes:
    trusted = trusted_catalog_path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = None
    try:
        descriptor = os.open(trusted, flags)
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            return handle.read()
    except OSError as error:
        fail(f"could not read catalog: {error}")
    finally:
        if descriptor is not None:
            os.close(descriptor)


def load_catalog(path: Path) -> dict[str, Any]:
    try:
        content = read_catalog_bytes(path)
        data = json.loads(content, object_pairs_hook=strict_object)
    except OSError as error:
        fail(f"could not read catalog: {error}")
    except json.JSONDecodeError as error:
        fail(f"catalog is invalid JSON: {error}")
    if not isinstance(data, dict) or set(data) != {
        "schemaVersion",
        "catalogVersion",
        "models",
    }:
        fail("catalog must use exactly schemaVersion, catalogVersion, and models")
    schema_version, catalog_version = catalog_versions(data)
    raw_models = data.get("models")
    if not isinstance(raw_models, list) or not raw_models:
        fail("catalog models must be a non-empty list")
    models = [normalize_model(item, index) for index, item in enumerate(raw_models)]
    refs = [(item["provider"], item["modelId"]) for item in models]
    if len(refs) != len(set(refs)):
        fail("catalog contains duplicate provider/model entries")
    return {
        "schemaVersion": schema_version,
        "catalogVersion": catalog_version,
        "digest": hashlib.sha256(content).hexdigest(),
        "models": models,
    }


def available_models(
    replay: list[str] | None = None,
) -> tuple[set[tuple[str, str]], str]:
    if replay is not None:
        available = {parse_ref(value) for value in replay}
        if not available or len(available) != len(replay):
            fail("preserved availability snapshot is empty or duplicated")
        return available, "pi --list-models returned the selected provider/model"
    try:
        output = subprocess.check_output(
            ["pi", "--list-models"], text=True, stderr=subprocess.STDOUT
        )
    except (OSError, subprocess.CalledProcessError) as error:
        fail(f"could not query Pi model availability: {error}")
    available: set[tuple[str, str]] = set()
    for line in output.splitlines()[1:]:
        columns = line.split()
        if len(columns) >= 2:
            available.add((columns[0], columns[1]))
    if not available:
        fail("Pi reported no available models")
    return available, "pi --list-models returned the selected provider/model"


def parse_ref(value: str) -> tuple[str, str]:
    if "/" not in value:
        fail(f"model reference must be provider/model: {value}")
    provider, model_id = value.split("/", 1)
    if not provider or not model_id:
        fail(f"model reference must be provider/model: {value}")
    return provider, model_id


def validate_preserved_fallback_chain(
    resolution: dict[str, Any], catalog_digest: str, seen: set[str] | None = None
) -> None:
    seen = set() if seen is None else seen
    request = resolution.get("request") or {}
    excluded = request.get("excludedModels")
    fallback = request.get("fallbackFrom")
    if (
        resolution.get("policyVersion") != 5
        or resolution.get("launchAllowed") is not True
        or (resolution.get("catalog") or {}).get("digest") != catalog_digest
        or request.get("selectionMode") != "automatic"
        or not isinstance(excluded, list)
        or len(excluded) != len(set(excluded))
    ):
        fail("previous fallback chain has invalid routing provenance")
    selected_now = resolution.get("selection") or {}
    selected_now_ref = f"{selected_now.get('provider')}/{selected_now.get('modelId')}"
    availability_models = (resolution.get("availability") or {}).get("models")
    if (
        not isinstance(availability_models, list)
        or selected_now_ref not in availability_models
        or resolution.get("piArgs")
        != [
            "--provider",
            selected_now.get("provider"),
            "--model",
            selected_now.get("modelId"),
            "--thinking",
            selected_now.get("thinkingLevel"),
        ]
    ):
        fail("previous fallback chain has invalid selection or availability provenance")
    if fallback is None:
        if excluded:
            fail("initial fallback-chain resolution must not exclude models")
        return
    if not isinstance(fallback, dict) or set(fallback) != {
        "previousResolution",
        "failureEvidence",
        "cleanupEvidence",
    }:
        fail("previous fallback chain is incomplete")
    previous_ref = fallback["previousResolution"]
    if not isinstance(previous_ref, dict) or set(previous_ref) != {"path", "digest"}:
        fail("previous fallback chain has an invalid resolution reference")
    if previous_ref["digest"] in seen:
        fail("previous fallback chain contains a cycle")
    seen.add(previous_ref["digest"])
    _, previous = read_bound_json(
        previous_ref.get("path"), previous_ref.get("digest"), "chained previous resolution"
    )
    validate_preserved_fallback_chain(previous, catalog_digest, seen)
    previous_request = previous.get("request") or {}
    zone_keys = {
        "taskClass",
        "inputTypes",
        "minimumQualityRank",
        "thinking",
        "noContributor",
        "strongerThan",
        "strongerThanThinking",
        "selectionMode",
        "userModel",
        "userModelAuthority",
    }
    if (
        any(request.get(key) != previous_request.get(key) for key in zone_keys)
        or resolution.get("caller") != previous.get("caller")
    ):
        fail("previous fallback chain changes its routing zone or caller baseline")
    selected = previous.get("selection") or {}
    expected = list(previous_request.get("excludedModels") or []) + [
        f"{selected.get('provider')}/{selected.get('modelId')}"
    ]
    if excluded != expected:
        fail("previous fallback chain contains an unproven exclusion")
    failure_ref = fallback["failureEvidence"]
    cleanup_ref = fallback["cleanupEvidence"]
    for artifact, label in (
        (failure_ref, "chained failure evidence"),
        (cleanup_ref, "chained cleanup evidence"),
    ):
        if not isinstance(artifact, dict) or set(artifact) != {"path", "digest"}:
            fail(f"{label} reference is invalid")
    _, failure = read_bound_json(
        failure_ref.get("path"), failure_ref.get("digest"), "chained failure evidence"
    )
    _, cleanup = read_bound_json(
        cleanup_ref.get("path"), cleanup_ref.get("digest"), "chained cleanup evidence"
    )
    failed_model = f"{selected.get('provider')}/{selected.get('modelId')}"
    if (
        set(failure) != {
            "classification",
            "reasonCode",
            "failedModel",
            "agentSessionId",
            "paneId",
            "usableContribution",
            "sideEffects",
            "launchVerification",
            "runtimeOutput",
        }
        or failure.get("classification") != "model-specific-no-contribution"
        or failure.get("reasonCode") not in {
            "quota",
            "capacity",
            "rate-limit",
            "authentication",
            "availability",
        }
        or failure.get("failedModel") != failed_model
        or failure.get("usableContribution") is not False
        or failure.get("sideEffects") is not False
        or not nonempty(failure.get("agentSessionId"))
        or not nonempty(failure.get("paneId"))
    ):
        fail("historical fallback failure evidence is invalid")
    launch_ref = failure.get("launchVerification") or {}
    output_ref = failure.get("runtimeOutput") or {}
    _, launch = read_bound_json(
        launch_ref.get("path"), launch_ref.get("digest"), "historical launch verification"
    )
    read_bound_bytes(
        output_ref.get("path"), output_ref.get("digest"), "historical runtime output"
    )
    start_ref = (launch.get("evidence") or {}).get("startResponseArtifact") or {}
    verified_launch = verify_command(
        argparse.Namespace(
            resolution=previous_ref.get("path"),
            resolution_digest=previous_ref.get("digest"),
            herdr_start=start_ref.get("path"),
            runtime_env=None,
            output=None,
            _capture=True,
        )
    )
    if (
        launch != verified_launch
        or (launch.get("evidence") or {}).get("sessionIdentity")
        != failure.get("agentSessionId")
        or (launch.get("evidence") or {}).get("paneIdentity")
        != failure.get("paneId")
    ):
        fail("historical fallback launch binding is invalid")
    if (
        set(cleanup) != {
            "agentSessionId",
            "paneId",
            "agentStopped",
            "paneClosed",
            "remainingActive",
            "closureResponse",
            "absenceResponse",
        }
        or cleanup.get("agentSessionId") != failure.get("agentSessionId")
        or cleanup.get("paneId") != failure.get("paneId")
        or cleanup.get("agentStopped") is not True
        or cleanup.get("paneClosed") is not True
        or cleanup.get("remainingActive") is not False
    ):
        fail("historical fallback cleanup evidence is invalid")
    closure_ref = cleanup.get("closureResponse") or {}
    absence_ref = cleanup.get("absenceResponse") or {}
    _, closure = read_bound_json(
        closure_ref.get("path"), closure_ref.get("digest"), "historical closure response"
    )
    _, absence = read_bound_json(
        absence_ref.get("path"), absence_ref.get("digest"), "historical pane absence response"
    )
    if (
        closure.get("id") not in {"cli:pane:close", "cli:tab:close"}
        or (closure.get("result") or {}).get("type") != "ok"
        or absence.get("id") != "cli:pane:get"
        or (absence.get("error") or {}).get("code") != "pane_not_found"
        or (absence.get("error") or {}).get("message")
        != f"pane {failure.get('paneId')} not found"
    ):
        fail("historical fallback closure or absence proof is invalid")


def normalize_thinking(level: str | None, label: str) -> str:
    if level == "none":
        level = "off"
    if level not in THINKING_RANK:
        fail(f"{label} thinking level is missing or unsupported: {level!r}")
    return level


def choose_thinking(
    model: dict[str, Any], task_class: str, requested: str | None
) -> str:
    level = (
        requested
        or model["thinkingByTaskClass"].get(task_class)
        or model["defaultThinking"]
    )
    if level not in model["thinkingLevels"]:
        fail(
            f"resolved thinking level {level!r} is unsupported by {model['provider']}/{model['modelId']}"
        )
    return level


def current_caller(by_ref: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    provider = os.environ.get("PI_PROVIDER")
    model_id = os.environ.get("PI_MODEL")
    thinking = normalize_thinking(os.environ.get("PI_REASONING_LEVEL"), "caller")
    reference = (provider, model_id)
    if not all(nonempty(value) for value in reference) or reference not in by_ref:
        fail(
            "the current Pi caller must expose a provider/model present in the Pi-global catalog"
        )
    model = by_ref[reference]
    if thinking not in model["thinkingLevels"]:
        fail(
            "the current Pi caller thinking level is not supported by its catalog entry"
        )
    return {
        "provider": provider,
        "modelId": model_id,
        "thinkingLevel": thinking,
        "qualityRank": model["qualityRank"],
        "reviewTier": model["reviewTier"],
    }


def review_thinking(
    model: dict[str, Any],
    task_class: str,
    requested: str | None,
    baseline_quality: int,
    baseline_thinking_rank: int,
    *,
    require_strict: bool,
) -> str | None:
    if model["qualityRank"] < baseline_quality:
        return None
    minimum_rank = baseline_thinking_rank
    if require_strict and model["qualityRank"] == baseline_quality:
        minimum_rank += 1
    supported = sorted(model["thinkingLevels"], key=THINKING_RANK.get)
    candidates = [level for level in supported if THINKING_RANK[level] >= minimum_rank]
    if requested:
        return requested if requested in candidates else None
    if not candidates:
        return None
    preferred = choose_thinking(model, task_class, None)
    if preferred in candidates:
        return preferred
    return candidates[0]


def write_json(value: dict[str, Any], output: str | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


def validate_command(args: argparse.Namespace) -> None:
    catalog = load_catalog(Path(args.catalog).expanduser())
    write_json(
        {
            "valid": True,
            "catalog": {
                key: catalog[key]
                for key in ("schemaVersion", "catalogVersion", "digest")
            },
            "modelCount": len(catalog["models"]),
        },
        args.output,
    )


def resolve_command(args: argparse.Namespace) -> dict[str, Any]:
    catalog_path = trusted_catalog_path(Path(args.catalog))
    catalog = load_catalog(catalog_path)
    required_inputs = set(args.input or ["text"])
    available, availability_evidence = available_models(
        getattr(args, "_availability_override", None)
    )
    by_ref = {(item["provider"], item["modelId"]): item for item in catalog["models"]}
    caller = current_caller(by_ref)

    user_pin = parse_ref(args.user_model) if args.user_model else None
    fallback_values = [
        args.fallback_from,
        args.fallback_from_digest,
        args.failure_evidence,
        args.failure_evidence_digest,
        args.cleanup_evidence,
        args.cleanup_evidence_digest,
    ]
    has_fallback = any(value is not None for value in fallback_values)
    if has_fallback and not all(value is not None for value in fallback_values):
        fail("fallback routing requires prior resolution, failure, cleanup, and all digests")
    if user_pin and has_fallback:
        fail("user-pinned routing cannot fall back to another model", 5)
    excluded_refs: list[tuple[str, str]] = []
    fallback_record: dict[str, Any] | None = None
    if has_fallback:
        previous_path, previous = read_bound_json(
            args.fallback_from, args.fallback_from_digest, "previous resolution"
        )
        validate_preserved_fallback_chain(previous, catalog["digest"])
        previous_request = previous.get("request") or {}
        expected_request = {
            "taskClass": args.task_class,
            "inputTypes": sorted(required_inputs),
            "minimumQualityRank": args.minimum_quality_rank,
            "thinking": args.thinking,
            "noContributor": args.no_contributor,
            "strongerThan": args.stronger_than,
            "strongerThanThinking": args.stronger_than_thinking,
            "selectionMode": "automatic",
            "userModel": None,
            "userModelAuthority": None,
        }
        if any(previous_request.get(key) != value for key, value in expected_request.items()):
            fail("fallback routing zone does not match the previous resolution")
        if previous.get("caller") != caller:
            fail("fallback caller baseline does not match the previous resolution")
        previous_excluded = previous_request.get("excludedModels")
        if not isinstance(previous_excluded, list) or len(previous_excluded) != len(set(previous_excluded)):
            fail("previous resolution has invalid fallback exclusions")
        excluded_refs = [parse_ref(value) for value in previous_excluded]
        previous_selected = previous.get("selection") or {}
        selected_ref = (
            previous_selected.get("provider"),
            previous_selected.get("modelId"),
        )
        if selected_ref not in by_ref or selected_ref in excluded_refs:
            fail("previous resolution has an invalid selected fallback candidate")
        if (previous.get("catalog") or {}).get("digest") != catalog["digest"]:
            fail("fallback cannot cross a model catalog change")
        previous_pi_args = previous.get("piArgs")
        if previous_pi_args != [
            "--provider",
            selected_ref[0],
            "--model",
            selected_ref[1],
            "--thinking",
            previous_selected.get("thinkingLevel"),
        ]:
            fail("previous resolution has non-canonical launch arguments")

        failure_path, failure = read_bound_json(
            args.failure_evidence, args.failure_evidence_digest, "fallback failure evidence"
        )
        required_failure = {
            "classification",
            "reasonCode",
            "failedModel",
            "agentSessionId",
            "paneId",
            "usableContribution",
            "sideEffects",
            "launchVerification",
            "runtimeOutput",
        }
        if set(failure) != required_failure or failure.get("classification") != "model-specific-no-contribution":
            fail("fallback failure evidence has an invalid schema or classification")
        if failure.get("reasonCode") not in {
            "quota",
            "capacity",
            "rate-limit",
            "authentication",
            "availability",
        }:
            fail("fallback failure reason is not model-specific and retryable")
        selected_text = f"{selected_ref[0]}/{selected_ref[1]}"
        if (
            failure.get("failedModel") != selected_text
            or failure.get("usableContribution") is not False
            or failure.get("sideEffects") is not False
            or not nonempty(failure.get("agentSessionId"))
            or not nonempty(failure.get("paneId"))
        ):
            fail("fallback failure evidence does not prove a no-contribution failure for the prior selection")
        launch_artifact = failure.get("launchVerification")
        output_artifact = failure.get("runtimeOutput")
        if (
            not isinstance(launch_artifact, dict)
            or set(launch_artifact) != {"path", "digest"}
            or not isinstance(output_artifact, dict)
            or set(output_artifact) != {"path", "digest"}
        ):
            fail("fallback failure evidence must bind launch verification and runtime output")
        _, launch_verification = read_bound_json(
            launch_artifact.get("path"), launch_artifact.get("digest"), "prior launch verification"
        )
        _, _ = read_bound_bytes(
            output_artifact.get("path"), output_artifact.get("digest"), "failed runtime output"
        )
        launch_evidence = launch_verification.get("evidence") or {}
        start_ref = launch_evidence.get("startResponseArtifact") or {}
        verified_launch = verify_command(
            argparse.Namespace(
                resolution=str(previous_path),
                resolution_digest=args.fallback_from_digest,
                herdr_start=start_ref.get("path"),
                runtime_env=None,
                output=None,
                _capture=True,
            )
        )
        if (
            launch_verification != verified_launch
            or launch_evidence.get("sessionIdentity") != failure["agentSessionId"]
            or launch_evidence.get("paneIdentity") != failure["paneId"]
        ):
            fail("fallback failure evidence is not bound to the prior verified launch")

        cleanup_path, cleanup = read_bound_json(
            args.cleanup_evidence, args.cleanup_evidence_digest, "fallback cleanup evidence"
        )
        if set(cleanup) != {
            "agentSessionId",
            "paneId",
            "agentStopped",
            "paneClosed",
            "remainingActive",
            "closureResponse",
            "absenceResponse",
        } or (
            cleanup.get("agentSessionId") != failure["agentSessionId"]
            or cleanup.get("paneId") != failure["paneId"]
            or cleanup.get("agentStopped") is not True
            or cleanup.get("paneClosed") is not True
            or cleanup.get("remainingActive") is not False
        ):
            fail("fallback cleanup evidence does not prove exact runtime cleanup")
        closure_artifact = cleanup.get("closureResponse")
        absence_artifact = cleanup.get("absenceResponse")
        if (
            not isinstance(closure_artifact, dict)
            or set(closure_artifact) != {"path", "digest"}
            or not isinstance(absence_artifact, dict)
            or set(absence_artifact) != {"path", "digest"}
        ):
            fail("fallback cleanup evidence must bind closure and post-close absence responses")
        _, closure = read_bound_json(
            closure_artifact.get("path"), closure_artifact.get("digest"), "runtime closure response"
        )
        if closure.get("id") not in {"cli:pane:close", "cli:tab:close"} or (closure.get("result") or {}).get("type") != "ok":
            fail("fallback cleanup evidence does not contain a successful Herdr closure response")
        _, absence = read_bound_json(
            absence_artifact.get("path"), absence_artifact.get("digest"), "post-close pane absence response"
        )
        if (
            absence.get("id") != "cli:pane:get"
            or (absence.get("error") or {}).get("code") != "pane_not_found"
            or (absence.get("error") or {}).get("message")
            != f"pane {failure['paneId']} not found"
        ):
            fail("fallback cleanup does not prove the exact failed pane is absent")
        excluded_refs.append(selected_ref)
        fallback_record = {
            "previousResolution": {
                "path": str(previous_path),
                "digest": args.fallback_from_digest,
            },
            "failureEvidence": {
                "path": str(failure_path),
                "digest": args.failure_evidence_digest,
            },
            "cleanupEvidence": {
                "path": str(cleanup_path),
                "digest": args.cleanup_evidence_digest,
            },
        }
    excluded_set = set(excluded_refs)
    if user_pin and args.user_model_authority != "latest-user-request":
        fail("a user-pinned model requires --user-model-authority latest-user-request")
    if not user_pin and args.user_model_authority is not None:
        fail("--user-model-authority requires --user-model")
    if user_pin and user_pin not in by_ref:
        fail(f"user-pinned model is not in the catalog: {args.user_model}", 5)

    contributors = [parse_ref(value) for value in args.stronger_than]
    contributor_thinking = args.stronger_than_thinking
    if any(contributor not in by_ref for contributor in contributors):
        fail("reviewer contributor baseline is not in the catalog")
    if len(contributors) != len(contributor_thinking):
        fail("each reviewer contributor baseline requires one thinking level")
    if args.task_class == "review" and bool(contributors) == bool(args.no_contributor):
        fail("review tasks require contributor baselines or --no-contributor")
    if args.task_class != "review" and (
        contributors or contributor_thinking or args.no_contributor
    ):
        fail("review baselines and --no-contributor are valid only for review tasks")

    catalog_eligible = [
        model
        for model in catalog["models"]
        if args.task_class in model["taskClasses"]
        and required_inputs.issubset(set(model["inputTypes"]))
        and model["qualityRank"] >= args.minimum_quality_rank
        and (model["provider"], model["modelId"]) not in excluded_set
    ]
    if user_pin:
        pinned = by_ref[user_pin]
        if pinned not in catalog_eligible:
            fail(
                "user-pinned model does not satisfy the requested task class, inputs, or minimum quality rank",
                5,
            )
        catalog_eligible = [pinned]
    eligible = [
        model
        for model in catalog_eligible
        if (model["provider"], model["modelId"]) in available
    ]
    if not eligible:
        if user_pin:
            fail("user-pinned model is unavailable; no fallback is allowed", 5)
        fail(
            "no remaining catalog model satisfies the routing zone and live availability",
            3,
        )
    if user_pin and args.thinking is not None and args.thinking not in eligible[0]["thinkingLevels"]:
        fail(
            "user-pinned model does not support the requested thinking level; no fallback is allowed",
            5,
        )

    escalation: dict[str, Any] = {"status": "not-required", "baselines": []}
    thinking_by_ref: dict[tuple[str, str], str] = {}
    pool = eligible
    if args.task_class == "review":
        baselines = [caller]
        for contributor, contributor_level in zip(contributors, contributor_thinking):
            contributor_model = by_ref[contributor]
            normalized_level = normalize_thinking(
                contributor_level, "review contributor baseline"
            )
            if normalized_level not in contributor_model["thinkingLevels"]:
                fail(
                    "review contributor thinking level is unsupported by its catalog entry"
                )
            baselines.append(
                {
                    "provider": contributor[0],
                    "modelId": contributor[1],
                    "thinkingLevel": normalized_level,
                    "qualityRank": contributor_model["qualityRank"],
                    "reviewTier": contributor_model["reviewTier"],
                }
            )
        baseline_quality = max(item["qualityRank"] for item in baselines)
        baseline_thinking_rank = max(
            THINKING_RANK[item["thinkingLevel"]] for item in baselines
        )

        def routed_review_candidates(
            models: list[dict[str, Any]], strict: bool, requested: str | None
        ) -> list[dict[str, Any]]:
            result = []
            for model in models:
                level = review_thinking(
                    model,
                    args.task_class,
                    requested,
                    baseline_quality,
                    baseline_thinking_rank,
                    require_strict=strict,
                )
                if level is not None:
                    choice = dict(model)
                    choice["resolvedThinking"] = level
                    result.append(choice)
            return result

        catalog_stronger = routed_review_candidates(catalog_eligible, True, None)
        stronger = routed_review_candidates(eligible, True, args.thinking)
        if not stronger:
            if user_pin:
                fail(
                    "user-pinned reviewer does not satisfy stronger-reviewer requirements; no fallback is allowed",
                    5,
                )
            if catalog_stronger:
                fail("the required stronger reviewer is unavailable", 4)
            fail("the catalog contains no stronger reviewer for this task", 4)
        pool = stronger
        status = "stronger"
        escalation = {
            "status": status,
            "rule": "no-regression-in-model-or-thinking-and-at-least-one-strict",
            "baselines": baselines,
            "baselineQualityRank": baseline_quality,
            "baselineThinkingLevel": THINKING_LEVELS[baseline_thinking_rank],
        }
        thinking_by_ref = {
            (item["provider"], item["modelId"]): item["resolvedThinking"]
            for item in pool
        }
    else:
        if args.thinking is not None:
            pool = [item for item in pool if args.thinking in item["thinkingLevels"]]
            if not pool:
                if user_pin:
                    fail(
                        "user-pinned model does not support the requested thinking level; no fallback is allowed",
                        5,
                    )
                fail("no available model supports the requested thinking level", 4)
        thinking_by_ref = {
            (item["provider"], item["modelId"]): choose_thinking(
                item, args.task_class, args.thinking
            )
            for item in pool
        }

    pool.sort(
        key=lambda item: (
            item["taskClassScores"].get(args.task_class, 0),
            item["qualityRank"],
            THINKING_RANK[thinking_by_ref[(item["provider"], item["modelId"])]],
            -item["catalogOrder"],
        ),
        reverse=True,
    )
    selected = pool[0]
    thinking = thinking_by_ref[(selected["provider"], selected["modelId"])]
    state_escalation = {
        "status": escalation["status"],
        "rule": escalation.get("rule"),
        "baselines": [
            {
                "provider": item["provider"],
                "model_id": item["modelId"],
                "thinking_level": item["thinkingLevel"],
            }
            for item in escalation.get("baselines", [])
        ],
    }
    state_selection = {
        "provider": selected["provider"],
        "model_id": selected["modelId"],
        "task_class": args.task_class,
        "input_types": sorted(required_inputs),
        "thinking_level": thinking,
        "reason": (
            "Explicit latest-user model request validated by shared routing policy"
            if user_pin
            else "Shared model-routing policy resolution"
        ),
        "availability_evidence": availability_evidence,
        "caller": {
            "provider": caller["provider"],
            "model_id": caller["modelId"],
            "thinking_level": caller["thinkingLevel"],
        },
    }
    if args.task_class == "review":
        state_selection["reviewer_escalation"] = state_escalation

    result = {
        "policyVersion": 5,
        "launchAllowed": True,
        "catalog": {
            "path": str(catalog_path),
            "digest": catalog["digest"],
            "schemaVersion": catalog["schemaVersion"],
            "catalogVersion": catalog["catalogVersion"],
        },
        "caller": caller,
        "request": {
            "taskClass": args.task_class,
            "inputTypes": sorted(required_inputs),
            "minimumQualityRank": args.minimum_quality_rank,
            "thinking": args.thinking,
            "noContributor": args.no_contributor,
            "strongerThan": args.stronger_than,
            "strongerThanThinking": args.stronger_than_thinking,
            "selectionMode": "user-pinned" if user_pin else "automatic",
            "userModel": args.user_model,
            "userModelAuthority": args.user_model_authority,
            "excludedModels": [f"{provider}/{model}" for provider, model in excluded_refs],
            "fallbackFrom": fallback_record,
        },
        "selection": {
            "provider": selected["provider"],
            "modelId": selected["modelId"],
            "thinkingLevel": thinking,
            "qualityRank": selected["qualityRank"],
            "reviewTier": selected["reviewTier"],
            "family": selected["family"],
            "independenceGroup": selected["independenceGroup"],
            "reason": (
                "Explicit latest-user model request passed catalog, capability, availability, thinking, and review-escalation checks"
                if user_pin
                else "Highest structured task-class score, review capability, non-regressive thinking, and catalog order among eligible available models"
            ),
        },
        "availability": {
            "verified": True,
            "evidence": availability_evidence,
            "models": [f"{provider}/{model}" for provider, model in sorted(available)],
        },
        "reviewerEscalation": escalation,
        "stateSelection": state_selection,
        "piArgs": [
            "--provider",
            selected["provider"],
            "--model",
            selected["modelId"],
            "--thinking",
            thinking,
        ],
    }
    if getattr(args, "_capture", False):
        return result
    write_json(result, args.output)
    return result


def value_after(argv: list[str], flag: str) -> str | None:
    positions = [index for index, value in enumerate(argv) if value == flag]
    if len(positions) != 1 or positions[0] + 1 >= len(argv):
        fail(f"launch arguments must contain exactly one {flag}")
    return argv[positions[0] + 1]


def recompute_resolution(
    resolution: dict[str, Any], catalog_path: Path
) -> dict[str, Any]:
    request = resolution.get("request") or {}
    task_class = request.get("taskClass")
    input_types = request.get("inputTypes")
    if (
        task_class not in TASK_CLASSES
        or not isinstance(input_types, list)
        or not input_types
    ):
        fail("resolution request is incomplete")
    selection_mode = request.get("selectionMode")
    user_model = request.get("userModel")
    user_model_authority = request.get("userModelAuthority")
    if selection_mode not in {"automatic", "user-pinned"}:
        fail("resolution request has an unsupported selection mode")
    if selection_mode == "user-pinned":
        if not nonempty(user_model) or user_model_authority != "latest-user-request":
            fail("user-pinned resolution request is incomplete")
    elif user_model is not None or user_model_authority is not None:
        fail("automatic resolution cannot contain a user model pin")
    excluded_models = request.get("excludedModels")
    if (
        not isinstance(excluded_models, list)
        or len(excluded_models) != len(set(excluded_models))
        or any(not nonempty(value) for value in excluded_models)
    ):
        fail("resolution request has invalid fallback exclusions")
    fallback = request.get("fallbackFrom")
    fallback_values: dict[str, str | None] = {
        "fallback_from": None,
        "fallback_from_digest": None,
        "failure_evidence": None,
        "failure_evidence_digest": None,
        "cleanup_evidence": None,
        "cleanup_evidence_digest": None,
    }
    if fallback is None:
        if excluded_models:
            fail("an initial resolution cannot contain fallback exclusions")
    else:
        if not isinstance(fallback, dict) or set(fallback) != {
            "previousResolution",
            "failureEvidence",
            "cleanupEvidence",
        }:
            fail("resolution request has invalid fallback provenance")
        field_map = {
            "previousResolution": ("fallback_from", "fallback_from_digest"),
            "failureEvidence": ("failure_evidence", "failure_evidence_digest"),
            "cleanupEvidence": ("cleanup_evidence", "cleanup_evidence_digest"),
        }
        for key, (path_field, digest_field) in field_map.items():
            artifact = fallback.get(key)
            if (
                not isinstance(artifact, dict)
                or set(artifact) != {"path", "digest"}
                or not nonempty(artifact.get("path"))
                or not valid_digest(artifact.get("digest"))
            ):
                fail("resolution request has incomplete fallback provenance")
            fallback_values[path_field] = artifact["path"]
            fallback_values[digest_field] = artifact["digest"]
    availability = resolution.get("availability") or {}
    snapshot = availability.get("models")
    if not isinstance(snapshot, list) or not snapshot:
        fail("resolution lacks its availability snapshot")
    namespace = argparse.Namespace(
        catalog=str(catalog_path),
        task_class=task_class,
        input=list(input_types),
        minimum_quality_rank=request.get("minimumQualityRank"),
        thinking=request.get("thinking"),
        user_model=user_model,
        user_model_authority=user_model_authority,
        stronger_than=list(request.get("strongerThan") or []),
        stronger_than_thinking=list(request.get("strongerThanThinking") or []),
        no_contributor=request.get("noContributor") is True,
        output=None,
        _availability_override=list(snapshot),
        _capture=True,
        **fallback_values,
    )
    return resolve_command(namespace)


def verify_command(args: argparse.Namespace) -> dict[str, Any]:
    resolution_path = Path(args.resolution)
    try:
        resolution_content = resolution_path.read_bytes()
        resolution = json.loads(resolution_content)
    except (OSError, json.JSONDecodeError) as error:
        fail(f"could not read resolution: {error}")
    resolution_digest = hashlib.sha256(resolution_content).hexdigest()
    if not args.herdr_start:
        fail("verify-launch requires a Herdr start response")
    if (
        not valid_digest(args.resolution_digest)
        or args.resolution_digest != resolution_digest
    ):
        fail(
            "resolution artifact digest does not match the preserved pre-launch digest"
        )
    selected = resolution.get("selection") or {}
    expected = {
        "provider": selected.get("provider"),
        "model": selected.get("modelId"),
        "thinking": selected.get("thinkingLevel"),
    }
    if (
        not all(nonempty(value) for value in expected.values())
        or resolution.get("launchAllowed") is not True
    ):
        fail("resolution is incomplete or does not allow launch")
    catalog_record = resolution.get("catalog") or {}
    if not nonempty(catalog_record.get("path")):
        fail("resolution does not identify its catalog")
    catalog_path = trusted_catalog_path(Path(catalog_record["path"]))
    catalog = load_catalog(catalog_path)
    if any(
        catalog_record.get(key) != catalog[value]
        for key, value in (
            ("digest", "digest"),
            ("schemaVersion", "schemaVersion"),
            ("catalogVersion", "catalogVersion"),
        )
    ):
        fail("resolution catalog metadata does not match the live Pi-global catalog")
    recomputed = recompute_resolution(resolution, catalog_path)
    if resolution != recomputed:
        fail("resolution does not match the current deterministic routing decision")
    selected_model = next(
        (
            item
            for item in catalog["models"]
            if item["provider"] == expected["provider"]
            and item["modelId"] == expected["model"]
        ),
        None,
    )
    request = resolution.get("request") or {}
    required_inputs = request.get("inputTypes") or []
    if (
        selected_model is None
        or expected["thinking"] not in selected_model["thinkingLevels"]
        or request.get("taskClass") not in selected_model["taskClasses"]
        or not set(required_inputs).issubset(set(selected_model["inputTypes"]))
    ):
        fail("resolution selection is not authorized by the live Pi-global catalog")
    evidence: dict[str, Any] = {
        "catalog": {
            "path": str(catalog_path),
            "digest": catalog["digest"],
        },
        "resolutionArtifact": {
            "path": str(resolution_path),
            "digest": resolution_digest,
        },
    }
    if args.herdr_start:
        try:
            start_path = Path(args.herdr_start)
            start_content = start_path.read_bytes()
            start = json.loads(start_content)
        except (OSError, json.JSONDecodeError) as error:
            fail(f"could not read Herdr start response: {error}")
        start_result = start.get("result") or {}
        argv = start_result.get("argv")
        agent = start_result.get("agent") or {}
        session = agent.get("agent_session") or {}
        session_identity = session.get("value")
        if (
            start.get("id") != "cli:agent:start"
            or start_result.get("type") != "agent_started"
            or not isinstance(argv, list)
            or not argv
            or argv[0] != "pi"
            or agent.get("agent") != "pi"
            or session.get("agent") != "pi"
            or session.get("source") != "herdr:pi"
        ):
            fail("Herdr start response does not prove a Pi agent start")
        if (
            agent.get("interactive_ready") is not True
            or agent.get("agent_status") != "idle"
            or not nonempty(session_identity)
        ):
            fail(
                "Herdr start response does not prove a ready agent with immutable session identity"
            )
        if argv != ["pi", *(resolution.get("piArgs") or [])]:
            fail("Herdr launch arguments do not exactly match the resolution")
        actual = {
            "provider": value_after(argv, "--provider"),
            "model": value_after(argv, "--model"),
            "thinking": value_after(argv, "--thinking"),
        }
        if actual != expected:
            fail(
                f"Herdr launch settings do not match resolution: expected {expected}, got {actual}"
            )
        if not nonempty(agent.get("pane_id")):
            fail("Herdr start response does not identify the launched pane")
        evidence["herdrArgv"] = actual
        evidence["sessionIdentity"] = session_identity
        evidence["paneIdentity"] = agent["pane_id"]
        evidence["startResponseArtifact"] = {
            "path": str(start_path),
            "digest": hashlib.sha256(start_content).hexdigest(),
        }
    if args.runtime_env:
        try:
            runtime_path = Path(args.runtime_env)
            runtime_content = runtime_path.read_bytes()
            runtime = json.loads(runtime_content)
        except (OSError, json.JSONDecodeError) as error:
            fail(f"could not read runtime environment evidence: {error}")
        actual = {
            "provider": runtime.get("provider"),
            "model": runtime.get("model"),
            "thinking": runtime.get("thinking"),
        }
        if actual != expected:
            fail(
                f"runtime environment does not match resolution: expected {expected}, got {actual}"
            )
        evidence["runtimeEnvironment"] = actual
        evidence["runtimeEnvironmentArtifact"] = {
            "path": str(runtime_path),
            "digest": hashlib.sha256(runtime_content).hexdigest(),
        }
    result = {"verified": True, "expected": expected, "evidence": evidence}
    if getattr(args, "_capture", False):
        return result
    write_json(result, args.output)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--catalog", required=True)
    validate_parser.add_argument("--output")
    validate_parser.set_defaults(handler=validate_command)

    resolve_parser = commands.add_parser("resolve")
    resolve_parser.add_argument("--catalog", required=True)
    resolve_parser.add_argument(
        "--task-class", choices=sorted(TASK_CLASSES), required=True
    )
    resolve_parser.add_argument("--input", action="append", default=[])
    resolve_parser.add_argument(
        "--minimum-quality-rank",
        type=int,
        choices=sorted(set(REVIEW_TIER_RANK.values())),
        default=1,
    )
    resolve_parser.add_argument("--thinking", choices=THINKING_LEVELS)
    resolve_parser.add_argument("--user-model")
    resolve_parser.add_argument("--fallback-from")
    resolve_parser.add_argument("--fallback-from-digest")
    resolve_parser.add_argument("--failure-evidence")
    resolve_parser.add_argument("--failure-evidence-digest")
    resolve_parser.add_argument("--cleanup-evidence")
    resolve_parser.add_argument("--cleanup-evidence-digest")
    resolve_parser.add_argument(
        "--user-model-authority", choices=("latest-user-request",)
    )
    resolve_parser.add_argument("--stronger-than", action="append", default=[])
    resolve_parser.add_argument(
        "--stronger-than-thinking", action="append", choices=THINKING_LEVELS, default=[]
    )
    resolve_parser.add_argument("--no-contributor", action="store_true")
    resolve_parser.add_argument("--output")
    resolve_parser.set_defaults(handler=resolve_command)

    verify_parser = commands.add_parser("verify-launch")
    verify_parser.add_argument("--resolution", required=True)
    verify_parser.add_argument("--resolution-digest", required=True)
    verify_parser.add_argument("--herdr-start", required=True)
    verify_parser.add_argument("--runtime-env")
    verify_parser.add_argument("--output")
    verify_parser.set_defaults(handler=verify_command)

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
