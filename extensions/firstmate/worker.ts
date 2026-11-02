/**
 * Narrow, local Core worker classification for First Mate.
 *
 * `HC_TERMINAL_ID` is present in every Core-hosted Pi process, including the
 * primary coordinator, so it is only a precondition. A worker is verified from
 * the labels that pi-herdr AgentCreate writes: `pi.task` and `pi.session`.
 * Partial labels or a failed lookup are reported as unknown instead of guessed.
 */

import type { ExecResult, ExtensionAPI } from "@earendil-works/pi-coding-agent";

export type WorkerClassification =
	| { kind: "not-core" }
	| { kind: "primary"; terminalId: string }
	| { kind: "worker"; terminalId: string; task: string; parentSessionId: string; parent?: string }
	| { kind: "unknown"; terminalId: string; message: string };

type CoreExec = Pick<ExtensionAPI, "exec">;

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readLabel(labels: Record<string, unknown>, key: string): string | undefined {
	const value = labels[key];
	if (typeof value !== "string") return undefined;
	const trimmed = value.trim();
	return trimmed === "" ? undefined : trimmed;
}

function firstLine(value: string): string {
	const line = value.split("\n", 1)[0]?.trim() ?? "";
	return line === "" ? "no diagnostic output" : line;
}

/**
 * Classify the current process as a primary Core session, a verified task
 * worker, a non-Core session, or unknown when the Core lookup cannot be trusted.
 */
export async function classifyCoreWorker(
	pi: CoreExec,
	env: NodeJS.ProcessEnv = process.env,
): Promise<WorkerClassification> {
	const terminalId = env.HC_TERMINAL_ID?.trim();
	if (!terminalId) return { kind: "not-core" };

	let result: ExecResult;
	try {
		result = await pi.exec("hc", ["get", terminalId, "--json"]);
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		return { kind: "unknown", terminalId, message: `hc get ${terminalId} failed: ${firstLine(message)}` };
	}

	if (result.code !== 0) {
		const detail = result.stderr.trim() === "" ? result.stdout.trim() : result.stderr.trim();
		const suffix = detail === ""
			? "; no diagnostic output (is hc installed and this terminal live?)"
			: `: ${firstLine(detail)}`;
		return {
			kind: "unknown",
			terminalId,
			message: `hc get ${terminalId} exited with code ${result.code}${suffix}`,
		};
	}

	let parsed: unknown;
	try {
		parsed = JSON.parse(result.stdout);
	} catch {
		return { kind: "unknown", terminalId, message: `hc get ${terminalId} returned invalid JSON` };
	}
	if (!isRecord(parsed)) {
		return { kind: "unknown", terminalId, message: `hc get ${terminalId} returned unexpected JSON` };
	}
	if (typeof parsed.address === "string" && parsed.address !== terminalId) {
		return {
			kind: "unknown",
			terminalId,
			message: `hc get ${terminalId} returned terminal ${parsed.address}`,
		};
	}

	const labels = isRecord(parsed.labels) ? parsed.labels : {};
	const task = readLabel(labels, "pi.task");
	const parentSessionId = readLabel(labels, "pi.session");

	if (task === undefined && parentSessionId === undefined) return { kind: "primary", terminalId };
	if (task === undefined || parentSessionId === undefined) {
		const missing = task === undefined ? "pi.task" : "pi.session";
		return {
			kind: "unknown",
			terminalId,
			message: `Core terminal ${terminalId} has a partial pi-herdr label set (missing ${missing})`,
		};
	}

	const parent = typeof parsed.parent === "string" && parsed.parent.trim() !== "" ? parsed.parent : undefined;
	return { kind: "worker", terminalId, task, parentSessionId, ...(parent ? { parent } : {}) };
}
