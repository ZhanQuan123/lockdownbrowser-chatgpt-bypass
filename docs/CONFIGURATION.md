# Configuration

Use the launcher to initialize authentication and the model catalog. Running `mitmweb -s inject_floating_stable_ai_subscription.py` directly does not establish a session.

## User-set environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `MITMWEB_EXE` | Executable name or full path to `mitmweb`; quote paths containing spaces in PowerShell | Search `PATH`, then a legacy Windows Store location hard-coded in the launcher |
| `SIWC_MODEL` | Startup model slug, which must exist in the returned catalog | `gpt-6.1-sol` if available, otherwise the first allowed model |
| `SIWC_FORCE_LOGIN` | Set exactly `1` to skip reading the saved session at startup | Reuse the encrypted cache when valid |

The legacy Windows Store path is installation-specific. Set `MITMWEB_EXE` rather than relying on that fallback.

Example from the application directory:

```powershell
$readerPython = Join-Path $PWD '.venv\Scripts\python.exe'
$env:MITMWEB_EXE = Join-Path $PWD '.venv\Scripts\mitmweb.exe'
& $readerPython .\start_mitm_page_reader.py
```

To set a model, replace the example with an exact slug present in your startup catalog:

```powershell
$env:SIWC_MODEL = 'your-authorized-model-slug'
```

Restart the launcher after changing startup variables. A valid per-site model saved in the panel can override the startup model for that site's requests. Clear the panel's saved selection to return to the startup default.

## Ports and mitmproxy settings

The launcher passes `--listen-port 8080 --web-port 8081` to mitmweb. There are no custom application environment variables for these ports, and extra launcher command-line arguments are not forwarded.

To change ports, edit the launch command in `start_mitm_page_reader.py` and update the browser's proxy settings. A `listen_port` entry in mitmproxy configuration does not override the launcher's explicit flag.

For this computer's browser, set the following in `%USERPROFILE%\.mitmproxy\config.yaml` before launch:

```yaml
listen_host: 127.0.0.1
web_host: 127.0.0.1
```

Preserve existing configuration and avoid duplicate keys. Mitmproxy's configuration also controls its own behavior; the application does not enforce these bind addresses. See the [official options reference](https://docs.mitmproxy.org/stable/concepts/options/).

## Force a new sign-in

Stop the running instance. Disable the browser proxy if it points at the stopped instance. From the application directory:

```powershell
$readerPython = Join-Path $PWD '.venv\Scripts\python.exe'
$env:MITMWEB_EXE = Join-Path $PWD '.venv\Scripts\mitmweb.exe'
$env:SIWC_FORCE_LOGIN = '1'
try {
    & $readerPython .\start_mitm_page_reader.py
}
finally {
    Remove-Item Env:SIWC_FORCE_LOGIN -ErrorAction SilentlyContinue
}
```

The environment flag remains set while the launcher runs. The `finally` block clears it when that process exits. This forces authentication for the existing registration; it does not remove the account binding.

## Remove the cached session

Stop the launcher and proxy first. A running process can still hold tokens and write a renewed cache.

```powershell
$readerState = Join-Path $env:USERPROFILE '.floating_page_reader'
Remove-Item -LiteralPath (Join-Path $readerState 'session.dpapi') -ErrorAction SilentlyContinue
```

This deletes the local cache. It does not revoke permissions or credentials at the provider. The next launch requires authentication if no valid cache exists.

## Switch accounts or reset registration

The registration is bound to the original account subject. To intentionally register a different account, stop the application and delete both local files:

```powershell
$readerState = Join-Path $env:USERPROFILE '.floating_page_reader'
Remove-Item -LiteralPath (Join-Path $readerState 'session.dpapi') -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $readerState 'registration.json') -ErrorAction SilentlyContinue
```

Then restart and authenticate with the intended account. Re-registration remains subject to provider support and authorization. Do not delete the mitmproxy configuration or certificate files as part of this account reset.

## Browser preferences

These keys are stored in the visited site's `localStorage`, when available:

| Key | Value |
| --- | --- |
| `mitm-floating-page-reader-model` | Selected model slug |
| `mitm-floating-page-reader-effort` | Selected effort slug |
| `mitm-floating-page-reader-v54-position` | Panel and icon coordinates |

To reset only the reader's preferences, run this in the target page's browser console, then reload:

```javascript
localStorage.removeItem('mitm-floating-page-reader-model');
localStorage.removeItem('mitm-floating-page-reader-effort');
localStorage.removeItem('mitm-floating-page-reader-v54-position');
```

Do not clear all site storage just to reset the panel. The reader does not save answer cards or OAuth tokens in these preference keys.

## Internal environment variables

The launcher supplies `SIWC_ACCESS_TOKEN`, `SIWC_REFRESH_TOKEN`, `SIWC_CLIENT_ID`, `SIWC_SUBJECT`, `SIWC_EXPIRES_AT`, and `SIWC_MODELS_JSON` to the mitmweb child process. It also supplies the selected `SIWC_MODEL`, extends `PYTHONPATH` so the addon can import the cache helper, and removes `OPENAI_API_KEY` from the child environment.

Treat token-bearing environment values as credentials. Do not set, print, commit, or copy them into bug reports. Setting `OPENAI_API_KEY` does not enable a supported alternate authentication mode.

Return to the [README](../README.md).
