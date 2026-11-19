# Troubleshooting

These notes describe behavior verified by inspecting the supplied source. Live OAuth sign-in, account eligibility, model responses, and browser proxy operation were not verified while preparing this documentation.

For installation commands, browser proxy configuration, certificate setup, and session management, start with the [README](../README.md).

## The launcher cannot start

| Message or symptom | What to check |
| --- | --- |
| `Install the login dependency: python -m pip install 'PyJWT[crypto]'` | Install the login dependency into the Python environment used by the launcher. Follow the README's dependency steps. |
| `mitmweb not found. Add it to PATH or set MITMWEB_EXE to its full path.` | Install mitmproxy and make `mitmweb` discoverable, or set `MITMWEB_EXE` as described in the README. |
| `MITMWEB_EXE does not point to an executable.` | Check the executable path, including its filename. |
| `Put inject_floating_stable_ai_subscription.py in the same folder as this launcher.` | Keep all supplied application files together. |
| `ModuleNotFoundError` for `reader_auth_cache` | Confirm `reader_auth_cache.py` is beside the launcher and addon. Start with the supplied launcher, which configures the addon's import path. |
| A port binding error | Check whether another process already occupies proxy port `8080` or web UI port `8081`. Stop the conflicting instance before starting the reader. |

The `.cmd` file chooses `py -3` when the Windows Python launcher is available, otherwise `python`. Installing a dependency into a different Python environment will not satisfy that launcher's imports.

## Sign-in does not finish

`Sign-in was not completed.` means the local callback did not complete within the launcher's four-minute wait.

1. Keep the launcher running while completing sign-in.
2. If the browser points to proxy port `8080` before the reader starts, temporarily disable that proxy for sign-in. The launcher starts mitmweb only after authentication succeeds.
3. If no browser opens, use the sign-in link printed by the launcher.
4. Check whether the browser can return to the local callback on `127.0.0.1`.

`ChatGPT sign-in was declined:` and `Authorization server rejected the sign-in (...)` report a rejected authentication attempt. Follow the returned sign-in error; restarting does not establish account eligibility.

`ChatGPT plan usage permission was not granted.` means the returned scopes did not include the permissions required by this code. The package's presence does not prove that this integration is available to your account or plan.

## A saved login is not reused

The launcher prints `Saved login could not be reused; interactive sign-in is required.` when the encrypted session cannot be used successfully. Complete sign-in again using the same Windows user profile.

The cache is tied to Windows DPAPI. A copied cache, revoked session, changed account, or failed renewal can require another sign-in. See the [README](../README.md) for forcing a fresh sign-in and removing the cache.

`This account does not match the original registration. Delete the local registration file only if you want to set up a different account.` indicates that the sign-in identity differs from the saved registration. Use the README's account-switching guidance; deleting the login cache alone does not remove that registration.

## No usable model is returned

Exact startup error:

```text
No usable model was returned for this ChatGPT plan, or SIWC_MODEL is not in the list.
```

The launcher expects a JSON object containing a `models` list. Each accepted entry must contain `visibility: "list"` and a valid `slug`. A response with a different shape, such as a `data` list, produces no accepted entries in this implementation.

If you set `SIWC_MODEL`, remove that override or use an identifier present in the returned catalog. Removing the variable does not fix an empty catalog, an incompatible response shape, or missing account permission. Inspect the integration before changing code to assume a different response format.

The panel error `This model is not available for the signed-in account.` means the submitted model is outside the backend's startup catalog. Refresh the page and select a listed model.

## The floating icon does not appear

Check the [browser proxy and certificate setup](../README.md) first. A running mitmweb web UI does not by itself mean that the target browser's traffic passes through the proxy.

- Confirm that the launcher is still running and the browser uses the configured proxy.
- For HTTPS pages, complete the certificate setup for that browser. Do not dismiss an unexplained certificate warning to continue.
- Refresh the target page after starting the proxy; an already loaded document does not receive the overlay automatically.
- Confirm that the response is an HTTP `200` HTML document requested with `GET`. Downloads, non-HTML responses, and other status codes are skipped.
- Check the top-level document. The script does not install an icon inside frames.
- Check the browser console for blocked scripts or styles. A website's Content Security Policy can block the overlay; the addon does not remove that policy.

The proxy logs `Page reader V5.9 injected into host:` when it modifies a qualifying response. That log confirms insertion into the HTML response, not successful browser execution.

## The version looks wrong

The package is labeled **v5.10**, while the supplied overlay's `dataset.readerVersion` and injection log still identify **5.9**. The original text README's expected **5.8** console result is outdated. See the [version check](USAGE.md#check-the-loaded-overlay-version).

## Requests fail after restarting the proxy

Refresh every open reader page after a restart. Each proxy process generates a new handler path and local request token. Tabs loaded by the previous process retain the old values.

The message ending with `The local proxy handler may not have received the request.` means the response lacked the handler's `X-Page-Reader-Local: 1` marker. Check for a stale tab, a stopped proxy, or browser traffic bypassing the proxy. The browser can show another HTTP error before this check if the old request is blocked or redirected.

`This page reader is not authorized.` indicates that the local request token does not match the running process. Refresh the page through the current proxy.

## A selected reasoning effort fails

Exact backend error:

```text
This model does not accept the selected effort. Choose Auto or a different level.
```

Choose **Auto**, which sends no effort override, or select a level supported by that model. The menu contains the same choices for every model; it does not dynamically filter by model support.

## There is no readable page text

The panel can show:

```text
No readable HTML content was found on this page.
```

The backend can also return `No readable page text received.`

The reader extracts HTML text rather than screenshots. Questions rendered only as image pixels, canvas graphics, iframe contents, or excluded controls are unavailable. Content outside the preferred `main` subtree may also be omitted. Wait for dynamic content to load, then submit again. See [content capture and limits](USAGE.md#what-page-content-is-read).

## An answer is incomplete or lacks context

Large pages are bounded to 80,000 extracted characters and 22,000 scanned nodes. Tables and individual text fragments have additional limits. Model output is requested with a maximum of 1,800 tokens.

Earlier answer cards are not sent as conversation history. Restate any context needed for a follow-up question. An empty question invokes the page-question/summary behavior; it does not mean “continue the last answer.”

Math and multiple-choice answers are explicitly instructed to omit explanations. This is current application behavior.

## HTTP 502, connection failures, or timeouts

The local handler maps most backend exceptions to HTTP `502`. That status can indicate an upstream authentication, connection, model, stream, or cache-save error. Read the accompanying message.

| Message | Meaning and next step |
| --- | --- |
| `Start the proxy using start_mitm_page_reader.py to sign in with ChatGPT.` | The addon lacks the launcher-provided session. Restart through the supplied launcher. |
| `ChatGPT session expired. Restart the proxy launcher to sign in.` | The backend cannot renew the session with its current state. Restart the launcher. |
| `ChatGPT session refresh failed (...)` | The authentication server rejected token renewal. Restart the launcher and complete sign-in if prompted. |
| `Could not connect to OpenAI:` | Inspect network reachability and the error details. Backend HTTP calls deliberately bypass proxy environment settings. |
| `ChatGPT (...)` | Inspect the upstream status and message. A listed model can still reject a later request. |
| `ChatGPT response stream ended before completion.` | The upstream stream ended without the completion event expected by this implementation. Check connectivity and retry. |
| `Session renewed, but saving the encrypted cache failed.` | Check write access to the application's user-profile cache directory. The request reports an error even though token renewal completed. |

The model request uses a 120-second URL-open timeout. This is not a guaranteed end-to-end deadline. The backend consumes the upstream stream before returning a complete answer to the panel, so the panel does not display token-by-token output.

## Reporting a problem

Record the exact error, package label, overlay version, affected browser, and steps to reproduce. Include whether the failure occurs before sign-in, during startup, or after sending a question. Share only a sanitized log excerpt; do not include tokens, callback URLs, session files, private page content, or captured browser traffic.
