/**
 * First Mate - configurable coordinator mode for primary Pi sessions.
 *
 * The mode keeps conversation, decisions and quick inspection in the main
 * session, and delegates project execution to workers through the existing
 * pi-tasks/Herdr/implement workflow. The behavioral policy lives in
 * `skills/firstmate/SKILL.md`; this extension only owns configuration, the
 * session toggle, worker suppression, status and per-run prompt guidance.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type {
	ExtensionAPI,
	ExtensionCommandContext,
	ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { readConfiguredDefault, type ConfiguredDefault } from "./config.js";
import { classifyCoreWorker, type WorkerClassification } from "./worker.js";

const COMMAND_NAME = "firstmate";
const ENTRY_TYPE = "pi-firstmate.mode";
const SECTION_KEY = "first_mate";
const STATUS_KEY = "firstmate";
const POLICY_DISPLAY_PATH = "skills/firstmate/SKILL.md";
const POLICY_URL = new URL("../../skills/firstmate/SKILL.md", import.meta.url);

const ON_GUIDELINE =
	"First Mate coordinator mode is active for this session. Follow the <first_mate> section: keep conversation, decisions, quick inspection and coordination local, and delegate project execution to workers with the existing implement, herdr and model-routing-policy workflow.";
const OFF_GUIDELINE =
	"First Mate coordinator mode is off. Supersede any earlier First Mate coordinator guidance in this session and resume the normal implement self-or-delegate decision for project work.";

const USAGE =
	"Usage: /firstmate on | off | default | status. With no argument, shows status.";

interface ModeResolution {
	effective: boolean;
	worker: WorkerClassification;
	suppressed: boolean;
	uncertain: boolean;
}

function stripFrontmatter(markdown: string): string {
	const match = /^---[ \t]*\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/.exec(markdown);
	return match ? markdown.slice(match[0].length) : markdown;
}

function report(
	ctx: ExtensionContext | ExtensionCommandContext,
	message: string,
	level: "info" | "warning" | "error" = "info",
): void {
	if (ctx.hasUI) {
		ctx.ui.notify(message, level);
		return;
	}
	// Non-interactive modes have no dialog UI. Use stderr so print/json output
	// on stdout is never corrupted by extension diagnostics.
	console.error(message);
}

export default function firstMateExtension(pi: ExtensionAPI): void {
	let config: ConfiguredDefault = { kind: "valid", enabled: false };
	let override: boolean | null = null;
	let guidanceEvidence = false;
	let worker: WorkerClassification | undefined;
	let policyText: string | undefined;
	let policyError: string | undefined;

	function refreshConfig(): void {
		const settings: unknown = pi.getSettings();
		config = readConfiguredDefault(settings);
	}

	function refreshSessionState(ctx: ExtensionContext | ExtensionCommandContext): void {
		const sessionId = ctx.sessionManager.getSessionId();
		let restored: boolean | null = null;
		let sawGuidanceSection = false;

		// Session-level state: scan every entry, not only the active branch, so
		// tree navigation inside one session does not silently undo the toggle.
		for (const entry of ctx.sessionManager.getEntries()) {
			if (entry.type === "message" && entry.message.role === "system") {
				const sections = entry.message.sections;
				const value = sections?.[SECTION_KEY];
				if (value !== undefined && value !== null) sawGuidanceSection = true;
			}
			if (entry.type !== "custom" || entry.customType !== ENTRY_TYPE) continue;
			if (typeof entry.data !== "object" || entry.data === null || Array.isArray(entry.data)) continue;
			const data = entry.data as Record<string, unknown>;
			if (data.sessionId !== sessionId) continue;
			if (data.enabled !== true && data.enabled !== false && data.enabled !== null) continue;
			restored = data.enabled;
		}

		override = restored;
		// A persisted First Mate prompt section is direct evidence that earlier
		// coordinator guidance exists in this session, including after reload.
		guidanceEvidence = sawGuidanceSection;
	}

	function loadPolicy(): string | undefined {
		if (policyText !== undefined) return policyText;
		try {
			const text = stripFrontmatter(readFileSync(fileURLToPath(POLICY_URL), "utf8")).trim();
			if (text === "") throw new Error("the skill file is empty");
			policyText = text;
			policyError = undefined;
			return policyText;
		} catch (error) {
			policyError = error instanceof Error ? error.message : String(error);
			return undefined;
		}
	}

	function resolveMode(): ModeResolution {
		const configuredDefault = config.kind === "valid" ? config.enabled : false;
		const requested = override !== null ? override : configuredDefault;
		const classification: WorkerClassification = worker ?? {
			kind: "unknown",
			terminalId: "",
			message: "the Core worker check has not completed",
		};

		let effective = requested;
		let uncertain = false;
		if (classification.kind === "worker") {
			effective = false;
		} else if (classification.kind === "unknown" && override === null && requested) {
			// Never apply the configured default to a possible worker.
			effective = false;
			uncertain = true;
		}

		return {
			effective,
			worker: classification,
			suppressed: classification.kind === "worker" && requested,
			uncertain,
		};
	}

	async function ensureWorkerKnown(): Promise<void> {
		if (worker !== undefined && worker.kind !== "unknown") return;
		worker = await classifyCoreWorker(pi);
	}

	function saveOverride(enabled: boolean | null, ctx: ExtensionCommandContext): void {
		const sessionId = ctx.sessionManager.getSessionId();
		pi.appendEntry(ENTRY_TYPE, { sessionId, enabled });
		override = enabled;
	}

	function syncIndicator(ctx: ExtensionContext | ExtensionCommandContext): void {
		ctx.ui.setStatus(STATUS_KEY, resolveMode().effective ? "First Mate" : undefined);
	}

	function configuredDefaultText(): string {
		if (config.kind === "invalid") return `off (invalid settings: ${config.message})`;
		return config.enabled
			? `on (settings "pi-firstmate.enabled")`
			: `off (settings "pi-firstmate.enabled" or omitted)`;
	}

	function workerText(classification: WorkerClassification): string {
		switch (classification.kind) {
			case "not-core":
				return "not a Core process";
			case "primary":
				return `primary Core session (${classification.terminalId})`;
			case "worker": {
				const parent = classification.parent ? `, parent=${classification.parent}` : "";
				return `verified Core worker pi.task=${classification.task}, pi.session=${classification.parentSessionId}${parent}; coordinator guidance is never applied in workers`;
			}
			case "unknown":
				return `unknown: ${classification.message}`;
		}
	}

	function statusText(): { text: string; level: "info" | "warning" | "error" } {
		const mode = resolveMode();
		const state = mode.suppressed
			? "off (worker suppression)"
			: mode.uncertain
				? "off (worker check failed)"
				: mode.effective
					? "on"
					: "off";
		const policy = loadPolicy();
		const guidance = mode.effective
			? policy
				? `injected from ${POLICY_DISPLAY_PATH}`
				: `not injected: ${policyError ?? "the skill policy is unavailable"}`
			: "not injected";

		const lines = [
			`First Mate: ${state}`,
			`Configured default: ${configuredDefaultText()}`,
			`Session override: ${override === null ? "none" : override ? "on" : "off"}`,
			`Worker: ${workerText(mode.worker)}`,
			`Guidance: ${guidance}`,
		];

		const level =
			config.kind === "invalid"
				? "error"
				: mode.suppressed || mode.uncertain || (mode.effective && !policy)
					? "warning"
					: "info";
		return { text: lines.join("\n"), level };
	}

	pi.registerCommand(COMMAND_NAME, {
		description: "Turn First Mate coordinator mode on or off, or report its status",
		getArgumentCompletions: (prefix) => {
			const trimmed = prefix.trim();
			if (trimmed.includes(" ")) return null;
			const matches = ["on", "off", "status", "default"].filter((value) => value.startsWith(trimmed));
			return matches.length > 0 ? matches.map((value) => ({ value, label: value })) : null;
		},
		handler: async (args, ctx) => {
			refreshConfig();
			const parts = args.trim().split(/\s+/).filter(Boolean);
			const action = parts[0]?.toLowerCase();

			if (action === undefined || action === "status") {
				if (parts.length > 1) {
					report(ctx, USAGE, "warning");
					return;
				}
				await ensureWorkerKnown();
				const status = statusText();
				report(ctx, status.text, status.level);
				return;
			}

			if (parts.length > 1 || (action !== "on" && action !== "off" && action !== "default")) {
				report(ctx, USAGE, "warning");
				return;
			}

			await ensureWorkerKnown();

			if (action === "on") {
				saveOverride(true, ctx);
				syncIndicator(ctx);
				const mode = resolveMode();
				if (mode.worker.kind === "worker") {
					report(
						ctx,
						`First Mate override saved, but coordinator guidance is suppressed in this Core worker session (pi.task=${mode.worker.task}). Workers execute their assignment under the normal implement rules.`,
						"warning",
					);
				} else if (mode.worker.kind === "unknown") {
					report(
						ctx,
						`First Mate is on by explicit session override. The Core worker check failed (${mode.worker.message}), so the configured default is not applied to a possible worker; your explicit override still applies.`,
						"warning",
					);
				} else if (!loadPolicy()) {
					report(
						ctx,
						`First Mate is on for this session, but its policy could not be read from ${POLICY_DISPLAY_PATH}: ${policyError}. No coordinator guidance is injected.`,
						"error",
					);
				} else {
					report(
						ctx,
						"First Mate is on for this session. Conversation, decisions and quick inspection stay local; project execution goes to workers.",
						"info",
					);
				}
				return;
			}

			if (action === "off") {
				saveOverride(false, ctx);
				syncIndicator(ctx);
				report(
					ctx,
					"First Mate is off for this session. Earlier coordinator guidance is superseded; the normal implement self-or-delegate decision applies.",
					"info",
				);
				return;
			}

			saveOverride(null, ctx);
			syncIndicator(ctx);
			const mode = resolveMode();
			const state = mode.suppressed
				? "off because this is a verified worker session"
				: mode.uncertain
					? "off because the Core worker check failed"
					: mode.effective
						? "on"
						: "off";
			report(ctx, `First Mate now follows the configured default: ${state}.`, mode.suppressed || mode.uncertain ? "warning" : "info");
		},
	});

	pi.on("session_start", async (_event, ctx) => {
		refreshConfig();
		refreshSessionState(ctx);
		worker = await classifyCoreWorker(pi);
		loadPolicy();

		const mode = resolveMode();
		syncIndicator(ctx);

		if (config.kind === "invalid") {
			report(
				ctx,
				`First Mate settings problem: ${config.message}. The configured default is treated as off; fix settings.json or use /firstmate on explicitly.`,
				"error",
			);
		}
		if (mode.uncertain && mode.worker.kind === "unknown") {
			report(
				ctx,
				`First Mate could not verify whether this Core session is a task worker (${mode.worker.message}). Coordinator guidance from the configured default is not applied; use /firstmate on if this is a coordinator session.`,
				"warning",
			);
		}
		if (mode.effective && !loadPolicy()) {
			report(
				ctx,
				`First Mate is on, but its policy could not be read from ${POLICY_DISPLAY_PATH}: ${policyError}. No coordinator guidance will be injected.`,
				"error",
			);
		}
	});

	pi.on("before_agent_start", (event) => {
		const mode = resolveMode();
		const options = event.systemPromptOptions;

		if (mode.effective) {
			const policy = loadPolicy();
			if (policy !== undefined) {
				options.sections[SECTION_KEY] = policy;
				guidanceEvidence = true;
				if (!options.promptGuidelines.includes(ON_GUIDELINE)) {
					options.promptGuidelines.push(ON_GUIDELINE);
				}
			} else {
				delete options.sections[SECTION_KEY];
			}
			return;
		}

		delete options.sections[SECTION_KEY];
		if (guidanceEvidence && !options.promptGuidelines.includes(OFF_GUIDELINE)) {
			options.promptGuidelines.push(OFF_GUIDELINE);
		}
	});

	pi.on("session_shutdown", (_event, ctx) => {
		override = null;
		guidanceEvidence = false;
		worker = undefined;
		ctx.ui.setStatus(STATUS_KEY, undefined);
	});
}
