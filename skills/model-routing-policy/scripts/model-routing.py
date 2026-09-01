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


def available_models() -> tuple[set[tuple[str, str]], str]:
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


def resolve_command(args: argparse.Namespace) -> None:
    catalog_path = trusted_catalog_path(Path(args.catalog))
    catalog = load_catalog(catalog_path)
    required_inputs = set(args.input or ["text"])
    available, availability_evidence = available_models()
    by_ref = {(item["provider"], item["modelId"]): item for item in catalog["models"]}
    caller = current_caller(by_ref)

    user_pin = parse_ref(args.user_model) if args.user_model else None
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
            "no catalog model satisfies task class, inputs, review tier, and live availability",
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
        "policyVersion": 3,
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
        "availability": {"verified": True, "evidence": availability_evidence},
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
    write_json(result, args.output)


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
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "resolve",
        "--catalog",
        str(catalog_path),
        "--task-class",
        task_class,
        "--minimum-quality-rank",
        str(request.get("minimumQualityRank")),
    ]
    for input_type in input_types:
        command.extend(["--input", input_type])
    if request.get("thinking") is not None:
        command.extend(["--thinking", request["thinking"]])
    selection_mode = request.get("selectionMode")
    user_model = request.get("userModel")
    user_model_authority = request.get("userModelAuthority")
    if selection_mode not in {"automatic", "user-pinned"}:
        fail("resolution request has an unsupported selection mode")
    if selection_mode == "user-pinned":
        if not nonempty(user_model) or user_model_authority != "latest-user-request":
            fail("user-pinned resolution request is incomplete")
        command.extend(
            [
                "--user-model",
                user_model,
                "--user-model-authority",
                user_model_authority,
            ]
        )
    elif user_model is not None or user_model_authority is not None:
        fail("automatic resolution cannot contain a user model pin")
    if request.get("noContributor") is True:
        command.append("--no-contributor")
    for contributor in request.get("strongerThan") or []:
        command.extend(["--stronger-than", contributor])
    for thinking in request.get("strongerThanThinking") or []:
        command.extend(["--stronger-than-thinking", thinking])
    try:
        return json.loads(
            subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)
        )
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        fail(f"could not recompute routing resolution: {error}")


def verify_command(args: argparse.Namespace) -> None:
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
        evidence["herdrArgv"] = actual
        evidence["sessionIdentity"] = session_identity
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
    write_json(
        {"verified": True, "expected": expected, "evidence": evidence}, args.output
    )


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
