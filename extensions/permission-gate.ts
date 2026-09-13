import { isToolCallEventType, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

type Rule = {
	label: string;
	pattern: RegExp;
};

const recursiveRm = String.raw`\brm\b(?=[^\n;&|]*(?:--recursive|-[^\s;&|]*[rR][^\s;&|]*))`;
const homeDirectory = process.env.HOME?.replace(/\/+$/, "");
const escapedHomeDirectory = homeDirectory?.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

// These commands are too dangerous or too ambiguous for an agent to run, even
// with confirmation. Run them yourself in a separate terminal if required.
const blockedRules: Rule[] = [
	...(escapedHomeDirectory
		? [
				{
					label: "recursive deletion of the current home directory",
					pattern: new RegExp(
						String.raw`${recursiveRm}[^\n;&|]*\s+["']?${escapedHomeDirectory}\/?["']?(?=\s|$|[;&|])`,
						"i",
					),
				},
			]
		: []),
	{
		label: "recursive deletion with a broad or ambiguous target",
		pattern: new RegExp(
			String.raw`${recursiveRm}[^\n;&|]*\s+["']?(?:\.\.(?:\/|["']?(?:\s|$))|[^\s;&|]*(?:\*|\?|\[|\]|\{|\}|\$|\x60|~))`,
			"i",
		),
	},
	{
		label: "recursive deletion of the filesystem, home, or a protected system root",
		pattern: new RegExp(
			String.raw`${recursiveRm}[^\n;&|]*\s+["']?(?:\/|~\/?|\$HOME\/?|\$\{HOME\}\/?|\/(?:Users|System|Applications|Library|private|etc|usr|var|bin|sbin|opt|Volumes|tmp)\/?)["']?(?=\s|$|[;&|])`,
			"i",
		),
	},
	{
		label: "recursive deletion of credential-sensitive files",
		pattern: new RegExp(
			String.raw`${recursiveRm}[^\n;&|]*\s+["']?[^\s;&|]*(?:\.ssh|\.gnupg|\.aws|\.kube|\.docker|\.config\/(?:gcloud|gh)|Library\/Keychains)(?:\/|["']?(?=\s|$|[;&|]))`,
			"i",
		),
	},
	{ label: "filesystem formatting or signature erasure", pattern: /\b(?:mkfs(?:\.[\w+-]+)?|wipefs)\b/i },
	{ label: "direct disk-device overwrite", pattern: /\bdd\b[^\n;&|]*\bof\s*=\s*["']?\/dev\//i },
	{
		label: "macOS disk erase or partition operation",
		pattern: /\bdiskutil\b[^\n;&|]*\b(?:erase|partition|apfs\s+(?:delete|erase))\b/i,
	},
	{ label: "shell fork bomb", pattern: /:\s*\(\s*\)\s*\{[^}]*:\s*\|\s*:[^}]*\}/i },
];

// These commands require an explicit confirmation in interactive Pi sessions.
// This includes exact recursive-deletion targets outside the current project.
// They are blocked when Pi has no confirmation UI (for example, print/JSON mode).
const confirmationRules: Rule[] = [
	{ label: "recursive or forced file deletion", pattern: /\brm\b[^\n;&|]*(?:--recursive|--force|-[^\s;&|]*[rRfF][^\s;&|]*)/i },
	{ label: "find with deletion", pattern: /\bfind\b[^\n;&|]*\s-delete\b/i },
	{ label: "privilege escalation", pattern: /\bsudo\b/i },
	{ label: "recursive permission or ownership change", pattern: /\b(?:chmod|chown)\b[^\n;&|]*(?:\s-R\b|\s--recursive\b|\b777\b)/i },
	{ label: "destructive Git operation", pattern: /\bgit\b[^\n;&|]*\b(?:reset\s+--hard|clean\s+-[^\s;&|]*f|branch\s+-D|push\b[^\n;&|]*--force(?:-with-lease)?|reflog\s+expire)\b/i },
	{ label: "package publication", pattern: /\b(?:npm|pnpm|yarn|bun|cargo|gem)\b[^\n;&|]*\bpublish\b/i },
	{ label: "downloaded script execution", pattern: /\b(?:curl|wget)\b[^\n;&|]*(?:\|\s*(?:sh|bash|zsh)\b|\b(?:sh|bash|zsh)\s*<\s*\()/i },
	{ label: "infrastructure destruction", pattern: /\b(?:terraform|tofu)\b[^\n;&|]*\bdestroy\b|\bkubectl\b[^\n;&|]*\bdelete\b/i },
	{ label: "machine shutdown or restart", pattern: /\b(?:shutdown|reboot|halt)\b/i },
];

function matchingLabels(command: string, rules: Rule[]): string[] {
	return [...new Set(rules.filter(({ pattern }) => pattern.test(command)).map(({ label }) => label))];
}

export default function permissionGate(pi: ExtensionAPI) {
	pi.on("session_start", (_event, ctx) => {
		ctx.ui.setStatus("permission-gate", "guardrails on");
	});

	pi.on("tool_call", async (event, ctx) => {
		if (!isToolCallEventType("bash", event)) return undefined;

		const command = event.input.command;
		const blocked = matchingLabels(command, blockedRules);
		if (blocked.length > 0) {
			return {
				block: true,
				reason: `Blocked by Pi command guardrails: ${blocked.join(", ")}. Run this manually only after checking every target.`,
				terminate: true,
			};
		}

		const needsConfirmation = matchingLabels(command, confirmationRules);
		if (needsConfirmation.length === 0) return undefined;

		if (!ctx.hasUI) {
			return {
				block: true,
				reason: `Command requires confirmation but this Pi mode has no confirmation screen: ${needsConfirmation.join(", ")}.`,
				terminate: true,
			};
		}

		const label = needsConfirmation.join(", ");
		pi.events.emit("herdr:blocked", { active: true, label });
		let confirmed = false;
		try {
			confirmed = await ctx.ui.confirm(
				"Dangerous command",
				`${label}\n\n${command}\n\nAllow this command?`,
				{ signal: ctx.signal },
			);
		} finally {
			pi.events.emit("herdr:blocked", { active: false, label });
		}
		if (!confirmed) {
			return { block: true, reason: "Command rejected by the user.", terminate: true };
		}

		return undefined;
	});
}
