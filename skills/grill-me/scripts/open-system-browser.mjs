import { spawnSync } from "node:child_process";

/** Return the platform-native command for opening a URL in the visible browser. */
export function systemBrowserCommand(url, platform = process.platform) {
  if (!/^https?:\/\//u.test(url)) {
    throw new Error("Browser URL must use HTTP or HTTPS");
  }
  if (platform === "darwin") {
    return { command: "open", args: [url] };
  }
  if (platform === "win32") {
    return {
      command: "rundll32",
      args: ["url.dll,FileProtocolHandler", url],
    };
  }
  return { command: "xdg-open", args: [url] };
}

/** Open a human interview page through the operating system, never Browser Use. */
export function openSystemBrowser(url, options = {}) {
  const opener = systemBrowserCommand(url, options.platform);
  const run = options.run ?? spawnSync;
  const result = run(opener.command, opener.args, { stdio: "inherit" });
  if (result.error) {
    throw new Error(`Could not start the system browser: ${result.error.message}`);
  }
  if (result.status !== 0) {
    throw new Error(
      `System browser opener exited with status ${result.status ?? "unknown"}`,
    );
  }
  return opener;
}
