# Privacy and security

Floating Page Reader runs a local interception proxy and sends extracted webpage content to OpenAI when the user presses Send. Local processing and an encrypted login cache do not make the complete workflow offline or confidential from the webpage itself.

## What the reader sends

Each Send action captures the current page again. The normal browser payload contains:

- The document title.
- The page's origin, such as `https://example.com`, rather than its full path, query, or fragment.
- Up to 80,000 characters of structured page content and a truncation flag.
- Up to 2,000 characters of the user's question.
- The selected model and reasoning effort.

The backend sends the title, origin, extracted content, truncation flag, and question in the generation prompt. Model and effort select generation settings. Earlier answer cards are not included as conversation history. Opening the panel alone does not call the model. See [browser request](../inject_floating_stable_ai_subscription.py#L968) and [backend payload](../inject_floating_stable_ai_subscription.py#L1332).

## Extraction is not redaction

The extractor prefers `main` or `[role="main"]`, falling back to the document body. It preserves headings, lists, table text, labels, select-option text, code blocks, and available math representations. Images contribute descriptions such as alt text, not pixels. Canvas content is represented by a placeholder; embedded frames are skipped.

The traversal skips inputs, textareas, buttons, ordinary scripts, styles, and several embedded elements. It also skips elements with `hidden`, `aria-hidden="true"`, or an inline `display:none` or `visibility:hidden` style. It does not evaluate computed CSS visibility. Text hidden through stylesheets can therefore be collected. Math annotations can also contain text that is not visibly displayed. The extractor does not inspect or redact sensitive information appearing in ordinary page text. See [extraction rules](../inject_floating_stable_ai_subscription.py#L889).

Use the reader only on content you are permitted to send to the provider. A page can contain private information even when no password field is collected.

## Browser and website access

The local reader fetch uses `credentials: "omit"`, `cache: "no-store"`, and `redirect: "error"`. This applies to that reader request only. It does not remove cookies or credentials from ordinary browser traffic routed through mitmproxy. The proxy can inspect broader HTTP traffic, including HTTPS traffic when its certificate is trusted. Treat mitmweb flow views, recordings, screenshots, and exports as potentially sensitive.

OAuth access and refresh tokens are not inserted into the overlay. The overlay does contain a separate random per-process authorization token and reader route. This token allows calls to the local handler; it is not an OpenAI credential. The handler verifies the path, method, and token, but does not enforce a domain allowlist. See [injected constants](../inject_floating_stable_ai_subscription.py#L1451) and [request checks](../inject_floating_stable_ai_subscription.py#L1408).

The interface uses an open shadow root, and its script runs in the webpage's context. Shadow DOM provides layout separation, not a security boundary. Page scripts can inspect the injected code and interface, including reader questions and displayed answers. Do not assume the panel is private from the website. See [interface creation](../inject_floating_stable_ai_subscription.py#L79).

## Local storage

| Location | Contents | Protection and limits |
| --- | --- | --- |
| `%USERPROFILE%\.floating_page_reader\session.dpapi` | Access token, refresh token, client ID, expiry, and account subject. | Encrypted using Windows DPAPI for the current user. It is not a portable session file. |
| `%USERPROFILE%\.floating_page_reader\registration.json` | Registration host ID and, after sign-in, client ID, subject, and email. | Plaintext JSON; it contains identity information even though it does not contain OAuth tokens. |
| Website `localStorage` | Selected model, effort, and panel/icon coordinates. | Stored per origin when available; accessible to that origin's scripts. |
| Current page memory | Question text and displayed answer cards. | Not deliberately saved to `localStorage`; accessible to webpage scripts while present. |
| Launcher and proxy processes | Live OAuth tokens and other session configuration. | Tokens are present in process memory and child-process environment variables. |

The cache helper uses temporary-file writing followed by an atomic replacement. Successful token renewal updates the encrypted cache, including a rotated refresh token. DPAPI protects the stored file, not a running session from software with access to the user's account or process. See [cache implementation](../reader_auth_cache.py#L23), [registration writing](../start_mitm_page_reader.py#L76), and [process environment](../start_mitm_page_reader.py#L318).

The launcher prints the account email when available and the selected model. The add-on prints injected hosts and reader request hosts. Avoid publishing unreviewed terminal logs or proxy captures. See [startup output](../start_mitm_page_reader.py#L331) and [reader logging](../inject_floating_stable_ai_subscription.py#L1412).

## Network exposure

The launcher selects ports `8080` and `8081`, but does not explicitly set a proxy listen host. It does not establish a loopback-only proxy binding in source. Check the installed mitmproxy configuration and effective listener before use. Do not expose the proxy or its administration interface to untrusted networks. See [launch command](../start_mitm_page_reader.py#L333) and [mitmproxy options](https://docs.mitmproxy.org/stable/concepts/options/).

There is no website filter in the response hook. Any eligible HTML response routed through the proxy can receive the overlay. Use a dedicated browser profile and route only intended traffic through the proxy when practical.

## Provider handling and authorization

The Responses request sets `store: false`. This is a request setting, not a promise of zero retention across authentication, safety, operational, or other provider systems. This package does not implement or verify provider-side retention controls beyond its request parameters. See [generation settings](../inject_floating_stable_ai_subscription.py#L1356).

The source requests particular OAuth scopes and uses specific authentication endpoints. This documentation does not establish that those endpoints or plan permissions are available to this project, every account, or every deployment. Review the provider's current [Sign in with ChatGPT documentation](https://help.openai.com/en/articles/20001410-sign-in-with-chatgpt) and the actual authorization prompt. Never infer successful authorization from the package name or a saved session file.

## Removing a saved session

Stop the launcher and proxy before removing the cache; a running process still has live tokens and can recreate the file on renewal. Deleting `session.dpapi` removes that local saved copy. It does not revoke credentials at the provider or clear the registration file and browser preferences. `SIWC_FORCE_LOGIN=1` requests interactive sign-in but retains the existing account registration and its subject check.

Do not commit or share the cache, registration file, process environment, authorization callback URL, proxy flow exports, or unreviewed logs. Keep the supplied `.gitignore` in the repository and review files before publishing.
