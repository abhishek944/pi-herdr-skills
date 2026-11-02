---
name: browser-use
description: Automates browser testing, screenshots, forms, and extraction with isolated local Chrome; no permission or readiness questions for authorized testing or owned-window foreground fallback.
allowed-tools: Bash(browser-use:*) Bash(python3:*) Bash(grep:*)
compatibility: Requires Python 3, installed Chrome/Chromium, and the browser-use CLI with its browser-harness runtime.
---

# Browser Use

Use Browser Use when a task needs a real browser: JavaScript rendering, clicks, forms, screenshots, downloads, or an existing signed-in session. Use normal web fetching for public pages that do not need interaction.

Before replying to the user, follow the global `talk-human` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Read repository instructions before starting an app or choosing a port.
- Do not close tabs, browsers, or services you did not create.
- Stop for personal passwords, multi-factor authentication, an actual consent prompt or explicit refusal, or an unclear account choice. Anticipated consent is not a reason to ask for general permission again.
- Keep waits bounded to 120 seconds. Inspect the page before trying one additional bounded wait.
- Prefer accessible names and the accessibility tree for finding controls.
- Verify every click, navigation, and form value after performing it.
- Never expose credentials or private data in output or screenshots.

## Keep testing simple and validate the tester first

- Start with direct browser actions or short inline command batches: inspect, click, type, read back. The launcher's small Python input program is fine; do not build an ad-hoc test framework, custom session manager or long workflow script just to perform a simple interaction.
- Prove the individual steps work before automating a longer sequence. Add a reusable script only for a concrete repeated, already-working sequence; keep it small and inspect its selectors, waits and success conditions before relying on it.
- Keep related investigation steps in the same owned page/session, within the tool's existing lifetime and safety limits. With the headless launcher, group related steps into one invocation rather than restarting for every action or screenshot. Reset accounts/profiles only when isolation or the case requires it; do not extend deadlines or build a persistence daemon to avoid a reset.
- Before blaming the application for missing input or a timeout, validate the tester: confirm the actual target/frame after redirects and demonstrate that the observation catches a known working interaction in an authorized control. A broken selector or observer makes the product result **NOT VERIFIED**, not an application failure.
- Prefer visible value/result readback over custom event watchers. If instrumentation is necessary, keep it observational and bounded, verify it against a positive control, and prevent observers from repeatedly triggering their own writes. `beforeinput` is intent, not proof that text was inserted; tool delivery success alone is not product success.
- For save workflows, verify each stage separately: actual input/value change, application acknowledgement, completed save/drain and fresh reopen with the expected value. A locally saved label or temporarily held editor does not prove the later stages.
- After two failed attempts at the same step, stop repeating that approach, not the verification goal. Diagnose the failure using the recovery workflow below. Resume through a supported, evidence-backed correction or fallback; do not treat the attempt count alone as a blocker.
- Report **application failures**, **tooling/test failures** and **unverified checks** separately. Preserve original failures and unknown operation outcomes; never replay an uncertain submission or force DOM/model/caret state to manufacture a pass.

## Diagnose browser failures and recover

- Investigate from the first failure: inspect the exact error, target/frame, tool health, app/server reachability and owned browser/controller state as relevant. Use a minimal known-working page or observation to distinguish automation failure from an app defect. Say when the cause remains unknown.
- Test a concrete hypothesis with a small diagnostic before another attempt. For controller/CDP timeouts, validate the automation connection before replaying the full workflow; for missing controls, verify navigation, frame and selector. Use documented diagnostic interfaces without inspecting opaque helper sources.
- Correct the evidenced cause and retry only the affected step, or use a documented alternate route that preserves the same acceptance criteria and authorization. Owned-window foreground fallback remains available when justified below; personal-profile attachment and consent bypass do not.
- Keep each recovery attempt bounded and require new evidence or a verified changed condition before further attempts. Do not cycle through identical launches, input methods or longer waits. A larger timeout needs evidence of expected duration or real progress.
- Read back any possible submission/save outcome before retrying. If it is uncertain, preserve that uncertainty and diagnose without replaying the write. Never force DOM/model state to make a check pass.
- Continue safe diagnosis and independent checks while recovery is possible. Before reporting a blocker, record what was inspected, the supported fixes/fallbacks attempted or ruled out, remaining unknowns and the concrete resume condition. A timeout or two failed attempts alone does not justify abandoning verification; a real safety, authority or tooling limit can.

## Authorization: never ask again for approved testing

- **DO NOT ask for permission, approval, consent to proceed, or readiness for already-authorized testing.** Do not ask “May I use the browser?”, “Are you ready?”, “May I switch tools?” or “May I briefly focus an isolated test window?” Carry the task authorization forward and act.
- This covers starting an owned isolated browser, fresh temporary test profiles, task-scoped screenshots, ordinary test-data input/saves, and a bounded switch from headless/background delivery to headed or foreground input through `computer-use` in the verified owned test window when technical evidence justifies it.
- Prefer headless/background operation first. After an observed delivery failure, inspect current evidence and use an appropriate documented fallback within the same task, account, test data and intended actions. Give a brief informational notice before foreground input, then proceed; **do not wait for a reply**. Keep focus changes brief and restore prior focus when supported.
- A timeout, unsupported event, unconfirmed keystroke, missing tool or need to focus the owned window is a technical issue, **not missing user permission**. Do not mark a Work/Todo blocked awaiting a generic approval or readiness answer. Continue allowed diagnosis and independent work; if no viable route remains, report the evidenced technical limitation.
- Respect an explicit background-only restriction and shared desktop ownership. This fallback does not authorize personal-profile attachment, unrelated windows, new sensitive/paid/destructive actions, changed OS grants or bypassing Pi/Driver policy.
- Stop only at an actual consent prompt or explicit refusal, unresolved account/document choice, or genuinely new scope requiring authorization. Ask only for that concrete action or decision, never for permission to repeat the already-approved testing. Never auto-approve consent or evade a denial by changing tools.

## Default: isolated headless testing, no approval questions

Browser testing, screenshots and public/local-page automation use an owned invisible browser by default. Do not ask permission to start browser testing, ask for “ready”, or ask the user to approve remote debugging for this mode. Carry existing task authorization forward and proceed within scope. Permission for testing does not authorize sensitive account/data writes, device access, paid actions or credential extraction.

Use the bundled `scripts/headless.py` launcher (resolve it relative to this skill). It starts installed Chrome directly with `--headless`, a fresh private nondefault profile, ephemeral loopback-only CDP and a private harness home/controller. It never discovers/attaches personal Chrome, foregrounds a window, copies cookies or auto-clicks native consent. No cloud/API key or new app dependency is needed. Missing tooling or startup failure is a technical error, not a reason to ask for browser permission. Diagnose it; use an evidenced owned-window fallback under the authorization section rather than blindly switching modes.

```bash
python3 ~/.agents/skills/browser-use/scripts/headless.py <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

Provide a closed UTF-8 heredoc or file on stdin (maximum1 MiB); input collection happens before browser timers, so never leave an interactive producer open. The stdin program uses the usual pre-imported browser-use helpers. Keep related inspect/action/capture steps and multiple pages in one invocation; reuse `current_tab()`, `list_tabs()` and `switch_tab()` inside it. The launcher bounds Chrome/controller startup to30s each and program execution to120s (lower with `--timeout SECONDS`), then cleans only its owned controller/browser/profile on success or failure. Each invocation is a fresh signed-out session; do not assume state survives between invocations or create one invocation per screenshot. Cancellation during startup waits for a safe ownership checkpoint; cleanup is bounded. Hard process/machine death can prevent cleanup; report retained/uncertain ownership rather than deleting or killing unrelated resources.

Do not use bare `browser-use` for ordinary testing: it may auto-discover personal Chrome and trigger its Allow flow. Do not use unscoped `open -a` or `activate_tab` to make headless mode work. In an authorized owned-window fallback, select/focus only the verified owned target without another permission question. Never run automatic consent helpers or change browser/OS grants. A backgrounded visible browser is not headless; describe the actual mode. If the task really requires an existing signed-in personal session, use that separate mode only when the user explicitly requests it; stop for actual credentials/MFA/native consent and never bypass refusal.

Common helpers include `click_at_xy`, `fill_input`, `press_key`, `js`, `wait_for_element`, `cdp` and `capture_screenshot`. Capture viewport/DPR, fonts and PNG dimensions explicitly; screenshots do not prove backend/provider behavior.

Use a named remote browser only when isolation or a hosted browser is genuinely needed, and ask before leaving a paid remote browser running.

## Personal-session connection failures and consent (not the testing default)

These rules apply only when the user explicitly needs an existing personal browser session. Ordinary browser testing uses the headless launcher above instead, without a permission round trip. Do not fall back from failed isolated testing into this mode.

User authorization, Chrome's per-connection remote-debugging consent, and connector health are separate. Permission to test remains valid after a failed connection; do not repeatedly ask the user to authorize the same testing. A timeout or expired handshake is not evidence that the user denied permission.

### Carry authorization forward

- Once browser work is authorized, do not ask “May I use the browser?”, “Are you ready?” or “Tell me when you can approve a fresh connection” merely because a handshake failed. A predicted prompt is not an observed user-action blocker.
- Diagnose connector health and inspect documented recovery without waiting for a readiness reply. These personal-session recovery limits do not permit a different personal profile or a backend change to evade consent. Owned isolated testing and its bounded delivery fallback use the authorization section above; neither mode permits consent bypass.
- Before creating or carrying forward a blocked Work/Todo, check current evidence. Record the exact error/state, diagnosis performed, and concrete missing action. An old timeout, stale task note or missing general “ready” response is not proof that permission is missing.
- Ask for user action only for an observed native prompt, explicit refusal, credentials/account choice, genuinely additional authority, or a verified recovery step requiring the user. If no actionable prompt exists, report a connector/diagnostic limitation rather than inventing a consent request. Once that dependency is resolved, resume the already-authorized work without another approval round.

If local Chrome cannot connect:

1. Inspect the exact error and run `browser-use --doctor`. Report the observed state, not an assumed cause. Distinguish a pending Allow prompt, an explicit refusal, an ended/expired connection, and an unavailable daemon. If the tools cannot distinguish them, say so.
2. If an Allow prompt or connection is still pending, preserve that exact connection. Do not reset/reload the daemon or create another connection: that can invalidate the prompt the user is approving. Ask the user to complete that specific native prompt, not to repeat their general authorization. Never click consent or change browser/OS grants automatically.
3. If the connection ended, do not claim there is still an actionable prompt. Use only documented recovery appropriate to the observed failure. Do not delete permission state, attach another profile, or try another CDP endpoint to bypass consent. Do not reset a shared daemon without checking ownership and impact.
4. Make at most one additional bounded connection attempt after evidence of a relevant state change or a documented recovery. Explain any native prompt the attempt may create as an informational notice, not a renewed permission/readiness question. If a prompt actually appears, ask only for that specific native action; never approve it yourself. If the same failure recurs, stop retrying and report the exact technical blocker and required recovery.
5. Continue independent authorized work. For owned isolated testing, use the bounded browser/desktop delivery fallback above **without asking permission again**. A personal-session failure does not authorize another personal profile, a new remote/paid backend, or a tool switch that evades an actual consent prompt or refusal; those remain separate scope.

A successful reconnection proves connectivity only. Verify the intended page and each interaction before claiming browser acceptance.

## Files

If the task needs retained screenshots, downloads or notes, follow global `implement` and write only inside the current owner's canonical task directory (`taskDir`). Reuse the caller's task for the same assignment; standalone work establishes real session/Work/Task ownership first. A delegated browser owner uses its own IDs nested below the exact supplied parent task directory, not a feature or lane folder. Disposable browser profiles remain tool-managed temporary resources, not retained evidence.

```text
<taskDir>/screenshots/
```

## Final response

Report what was done, what was observed, saved files, and any user action still required.
