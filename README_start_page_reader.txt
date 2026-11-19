V5.10 — ENCRYPTED CHATGPT LOGIN CACHE (Windows)

WHAT CHANGED
- Start mitmweb with your usual command. First login is interactive.
- Later restarts reuse an encrypted session on the same Windows user profile.
- Tokens are encrypted with Windows DPAPI and saved to:
    %USERPROFILE%\.floating_page_reader\session.dpapi
- The backend updates the file whenever the refresh token rotates.
- No access token, refresh token, or browser cookie is exposed to page JavaScript.
- If the session expires, is revoked, or cannot be renewed, you must sign in again.

INSTALL
1. Extract ALL FIVE files into the same folder. Replace previous files.
2. Run start_mitm_page_reader.cmd.
3. Sign in once when required. Subsequent runs reuse the saved session.
4. Refresh your webpage to reload the floating panel.

FORCE A FRESH SIGN-IN (PowerShell)
  $env:SIWC_FORCE_LOGIN = '1'
  & "$env:USERPROFILE\Downloads\start_mitm_page_reader.cmd"
  Remove-Item Env:SIWC_FORCE_LOGIN

REMOVE THE CACHED LOGIN (PowerShell)
  Remove-Item "$env:USERPROFILE\.floating_page_reader\session.dpapi"

SECURITY
- DPAPI binds the encrypted file to the Windows user profile on this machine.
- Never share the encrypted file, your Windows profile, or session data.
- An administrator or malware running with your user permissions can still
  potentially misuse a live session. Encryption is not invisibility.
- If you switch Windows user accounts, devices, or invalidate the tokens, sign in again.
- This script follows the existing sign-in integration in this package. It does
  not establish whether ChatGPT plan usage is supported for your integration.

V5.9 — Mac Glass Chat: Reasoning Effort + Stable Popover Menus

NEW IN V5.9
- Reasoning effort picker next to the model name: Auto, Low, Medium, High, Extra High, Max.
- Auto sends no reasoning.effort override; the model chooses its default.
- Non-Auto choices send the model's documented reasoning.effort field (Extra High = xhigh).
- Both model and effort menus now float outside the panel layout. Opening them does not increase the chatbox height, even after repeated open/close cycles.
- Answer area size is based on answer-card content, not its own available flex height, preventing cumulative growth.
- Keyboard still opens only on request. The panel shrinks again after the keyboard closes.
- Existing minimize, drag position memory, HTML parsing, answer history, and readable math are retained.
- Model and effort settings are saved per website when localStorage is available.

INSTALL ON WINDOWS
1. Stop any currently running mitmweb process.
2. Extract the FOUR files in this ZIP to the SAME folder (e.g. Downloads). Replace older versions.
3. Start start_mitm_page_reader.cmd in that folder.
4. Refresh the target webpage with Ctrl+Shift+R to load the new script.

VERIFY VERSION
In the browser console, on a page you have permission to debug:
  document.getElementById('mitm-floating-stable-host')?.dataset.readerVersion
Expected output: "5.8"

HOW TO USE
- Top-left model name: choose a model from the account's startup catalog.
- Next to it: click Auto / Low / Medium / High / Extra High / Max.
- Yellow circle at top-right: minimize.
- Keyboard icon next to Send: show/hide the on-screen keyboard.
- Click outside a popover (or press Escape) to close it.
- The chatbox height does not change when model or effort menus open.

LIMITATIONS
- Not all models support every reasoning effort. If a model rejects an effort, use Auto or a supported level. Higher effort can increase latency and token use.
- ChatGPT plan entitlement and live OAuth sign-in are not tested by the offline build.
- Only analyze sites/content you are authorized to access. Script injection may be blocked by website security policy.

V5.9: Model and effort buttons have stable positions regardless of selected text.
Dropdowns now use the V5.7-style glass menu and consistent system font.
