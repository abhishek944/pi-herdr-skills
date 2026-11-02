"""Run one browser-use program in an owned, isolated, invisible Chrome session."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse
from urllib.request import build_opener, ProxyHandler


def chrome_binary():
    for candidate in [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("google-chrome"), shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError("No installed Chrome/Chromium found; do not install without authority.")


def endpoint_for(browser, profile):
    deadline = time.monotonic() + 30
    marker = profile / "DevToolsActivePort"
    http = build_opener(ProxyHandler({}))
    while time.monotonic() < deadline:
        if browser.poll() is not None:
            raise RuntimeError("Owned headless Chrome exited during startup.")
        if marker.exists():
            lines = marker.read_text().splitlines()
            if len(lines) >= 2 and lines[0].isdigit():
                port = int(lines[0])
                if not 0 < port < 65536:
                    raise RuntimeError("Invalid owned debugging port.")
                endpoint = f"http://127.0.0.1:{port}"
                try:
                    remaining = max(0.1, min(5, deadline - time.monotonic()))
                    with http.open(endpoint + "/json/version", timeout=remaining) as response:
                        ws = urlparse(json.load(response)["webSocketDebuggerUrl"])
                except (OSError, ValueError, KeyError):
                    time.sleep(0.05)
                    continue
                if (ws.scheme != "ws" or ws.hostname != "127.0.0.1"
                        or ws.port != port or ws.path != lines[1]
                        or not ws.path.startswith("/devtools/browser/")):
                    raise RuntimeError("Endpoint does not match the owned Chrome marker.")
                return endpoint
        time.sleep(0.05)
    raise RuntimeError("Owned headless Chrome did not become ready within 30 seconds.")


def emit(text, stream):
    # WebSocket debugger URLs are capabilities, including in failure messages.
    stream.write(re.sub(r"wss?://[^\s\"'<>]+", "[debugger endpoint redacted]", text or ""))


_CANCEL = {"requested": False, "interruptible": False}


def interrupted(_signum, _frame):
    _CANCEL["requested"] = True
    if _CANCEL["interruptible"]:
        raise KeyboardInterrupt


def process_gone(pid):
    if type(pid) is not int or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return False
    except ProcessLookupError:
        return True
    except PermissionError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=120, choices=range(1, 121),
                        metavar="SECONDS", help="program timeout, 1..120 (default120)")
    args = parser.parse_args()
    if sys.stdin.isatty():
        parser.error("Provide a closed heredoc or file on stdin; no interactive input.")
    source = sys.stdin.buffer.read(1024 * 1024 + 1)
    if len(source) > 1024 * 1024:
        parser.error("Browser program exceeds 1 MiB.")
    program = source.decode("utf-8")
    if not program.strip():
        parser.error("Provide a browser-use Python program on stdin.")
    cli = shutil.which("browser-use")
    if not cli:
        raise RuntimeError("browser-use CLI is not installed; no automatic installation.")
    binary = chrome_binary()
    # macOS's default TMPDIR can exceed the harness Unix-socket path limit.
    root = Path(tempfile.mkdtemp(prefix="pi-headless-", dir="/tmp" if os.name == "posix" else None))
    profile = root / "profile"
    profile.mkdir(mode=0o700)
    env = os.environ.copy()
    for name in ("BU_CDP_WS", "BU_BROWSER_ID", "BROWSER_HARNESS_HOME",
                 "BH_REQUIRE_EXISTING_DAEMON"):
        env.pop(name, None)
    env.update(BH_HOME=str(root / "harness"), BH_AGENT_WORKSPACE=str(root / "workspace"),
               BH_CONFIG_DIR=str(root / "config"), BH_RUNTIME_DIR=str(root / "ipc"),
               BH_TMP_DIR=str(root / "tmp"), BH_RUNTIME_DIR_SHARED="0", BH_TMP_DIR_SHARED="0",
               BH_DOMAIN_SKILLS="0", BU_NAME="headless", BH_RECORD="0",
               BH_TAB_MARKER="0", BH_TELEMETRY="0")
    bypass = env.get("no_proxy", env.get("NO_PROXY", ""))
    env["NO_PROXY"] = env["no_proxy"] = "127.0.0.1,localhost,::1," + bypass
    browser = None
    started_cli = False
    clean = True
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        browser = subprocess.Popen([
            binary, "--headless", "--no-first-run", "--no-default-browser-check",
            "--disable-background-networking", "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        env["BU_CDP_URL"] = endpoint_for(browser, profile)
        print(f"Owned headless Chrome ready (pid={browser.pid}, session={root.name}); "
              "no personal profile attached.", flush=True)
        if _CANCEL["requested"]:
            raise KeyboardInterrupt
        started_cli = True
        startup = subprocess.run([cli], input="cdp('Browser.getVersion')\n", env=env,
                                 text=True, capture_output=True, timeout=30)
        if startup.returncode:
            emit(startup.stderr, sys.stderr)
            raise RuntimeError("Owned headless controller failed to start.")
        print("Owned headless controller ready.", flush=True)
        _CANCEL["interruptible"] = True
        if _CANCEL["requested"]:
            raise KeyboardInterrupt
        result = subprocess.run([cli], input=program, env=env, text=True,
                                capture_output=True, timeout=args.timeout)
        emit(result.stdout, sys.stdout)
        emit(result.stderr, sys.stderr)
        return result.returncode
    finally:
        _CANCEL["interruptible"] = False
        if started_cli:
            controller_pid = None
            pid_record = root / "ipc" / "bu.pid"
            try:
                record = json.loads(pid_record.read_text())
                controller_pid = record.get("pid") if isinstance(record, dict) else record
                if type(controller_pid) is not int or not 0 < controller_pid < (1 << 31):
                    raise ValueError("Invalid owned controller PID.")
            except (OSError, ValueError, TypeError):
                clean = False
            try:
                stopped = subprocess.run([cli, "--reload"], env=env, capture_output=True,
                                         text=True, timeout=25)
                clean = clean and stopped.returncode == 0
                if controller_pid is not None:
                    clean = clean and process_gone(controller_pid)
            except (OSError, subprocess.TimeoutExpired):
                clean = False
        if browser is not None and browser.poll() is None:
            try:
                browser.terminate()
                try:
                    browser.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(browser.pid, signal.SIGKILL)
                    browser.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                clean = clean and browser.poll() is not None
        if clean:
            shutil.rmtree(root)
            print("Owned controller, Chrome and temporary profile cleaned up.", flush=True)
        else:
            raise RuntimeError(f"Controller cleanup uncertain; ownership state retained at {root}.")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Headless session interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        emit(f"Headless session failed: {type(error).__name__}: {error}\n", sys.stderr)
        raise SystemExit(1)
