/**
 * Validation for the `pi-firstmate` section of Pi's effective settings.
 *
 * Pi owns settings loading, project trust and global/project merging, so the
 * extension reads the merged object from `pi.getSettings()` and validates only
 * the section it owns. Unknown sibling keys are ignored for forward compatibility.
 */

export const FIRST_MATE_SETTINGS_KEY = "pi-firstmate";

export type ConfiguredDefault =
	| { kind: "valid"; enabled: boolean }
	| { kind: "invalid"; message: string };

const DEFAULT_OFF: ConfiguredDefault = { kind: "valid", enabled: false };

function describeValue(value: unknown): string {
	if (value === null) return "null";
	if (Array.isArray(value)) return "an array";
	if (typeof value === "string") return "a string";
	if (typeof value === "number") return "a number";
	if (typeof value === "boolean") return "a boolean";
	return typeof value;
}

/**
 * Resolve the configured default.
 *
 * A missing section, a missing `enabled`, or an empty section means `false`.
 * A malformed section is reported instead of silently enabling coordinator mode.
 */
export function readConfiguredDefault(settings: unknown): ConfiguredDefault {
	if (typeof settings !== "object" || settings === null || Array.isArray(settings)) {
		return { kind: "invalid", message: "Pi returned settings that are not an object" };
	}

	const section = (settings as Record<string, unknown>)[FIRST_MATE_SETTINGS_KEY];
	if (section === undefined) return DEFAULT_OFF;
	if (typeof section !== "object" || section === null || Array.isArray(section)) {
		return {
			kind: "invalid",
			message: `expected "${FIRST_MATE_SETTINGS_KEY}" to be an object such as {"enabled": false}, found ${describeValue(section)}`,
		};
	}

	const enabled = (section as Record<string, unknown>).enabled;
	if (enabled === undefined) return DEFAULT_OFF;
	if (typeof enabled !== "boolean") {
		return {
			kind: "invalid",
			message: `expected "${FIRST_MATE_SETTINGS_KEY}.enabled" to be true or false, found ${describeValue(enabled)}`,
		};
	}

	return { kind: "valid", enabled };
}
