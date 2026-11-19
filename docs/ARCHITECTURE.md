# Architecture

This document describes the source supplied in the `floating_page_reader_v5_10_saved_login.zip` package. It records implementation behavior, not a live verification of OpenAI sign-in, model availability, or plan entitlement.

## Components

| Component | Responsibility |
| --- | --- |
| `start_mitm_page_reader.cmd` | Changes to the package directory and runs the Python launcher using `py -3`, with `python` as a fallback. |
| `start_mitm_page_reader.py` | Finds `mitmweb`, obtains or renews a session, fetches a model catalog, and starts the proxy with the add-on. |
| `reader_auth_cache.py` | Reads and atomically writes a Windows DPAPI-encrypted session file. |
| `inject_floating_stable_ai_subscription.py` | Injects the browser interface, extracts page content, handles local reader requests, and calls OpenAI. |

The browser interface is JavaScript, CSS, and HTML embedded in the add-on's `OVERLAY` string. There is no separate frontend build step.

## Request flow

```mermaid
sequenceDiagram
    participant Browser
    participant Proxy as mitmweb and add-on
    participant Site as Website
    participant OpenAI
    Browser->>Proxy: Request a webpage
    Proxy->>Site: Forward the request
    Site-->>Proxy: HTML response
    Proxy-->>Browser: HTML with reader overlay
    Note over Browser: User presses Send; collect current DOM text
    Browser->>Proxy: Same-origin POST to random reader path
    Proxy->>OpenAI: Responses request with OAuth bearer token
    OpenAI-->>Proxy: Server-sent events
    Note over Proxy: Accumulate text; require completion event
    Proxy-->>Browser: JSON containing the completed answer
```

The random reader path is intercepted by the add-on before normal upstream forwarding. It is a virtual route on the webpage's origin, not a separate browser-facing API server. The add-on requires `POST` and its per-process `X-Local-Page-Token` value. See the [request handler](../inject_floating_stable_ai_subscription.py#L1408).

## Startup and authentication

1. The launcher locates `mitmweb` and confirms that the add-on exists.
2. It loads or creates `%USERPROFILE%\.floating_page_reader\registration.json`.
3. It tries the DPAPI cache unless `SIWC_FORCE_LOGIN` equals `1`. The cached client ID and subject must match the registration.
4. It refreshes a cached token when expiry is within 120 seconds, then requests the model catalog. A catalog HTTP `401` or `403` triggers one refresh and another catalog request.
5. If cache reuse fails, the launcher clears the session file and starts interactive sign-in. The cache-reuse failure path also includes network and other handled errors; a sign-in prompt does not necessarily prove that the credentials were invalid.
6. Interactive sign-in uses an ephemeral `127.0.0.1` callback port, OAuth state, a nonce, and PKCE with `S256`. The callback wait is approximately 240 seconds.
7. The launcher validates the ID token using the issuer's JWKS. It checks `RS256`, issuer, audience, required identity claims, nonce, and the previously registered subject. It also requires the requested plan-usage scopes and renewable tokens.
8. It saves the session, selects a model, and starts `mitmweb`.

See [sign-in implementation](../start_mitm_page_reader.py#L87) and [cache reuse](../start_mitm_page_reader.py#L229). These checks describe the supplied client; they do not establish that the authentication service accepts this integration.

## Process configuration

The launcher passes access and refresh tokens, client ID, subject, expiry, selected model, and the filtered model catalog to the child process through `SIWC_*` environment variables. It prepends the package directory to `PYTHONPATH` so the add-on can import the cache helper, and removes `OPENAI_API_KEY` from the child environment. These are process environment values, not browser configuration. See [child process startup](../start_mitm_page_reader.py#L310).

The command fixes the proxy port at `8080` and the web interface port at `8081`. It does not explicitly set `--listen-host`. Therefore, the source does not enforce a loopback-only proxy listener. Effective binding and other settings depend on the installed mitmproxy version and configuration; consult [mitmproxy's option reference](https://docs.mitmproxy.org/stable/concepts/options/).

## Network destinations

| Destination | Purpose |
| --- | --- |
| `https://auth.openai.com/api/accounts/authorize` | Browser sign-in request. |
| `http://127.0.0.1:<ephemeral-port>/auth/callback` | Temporary local sign-in callback. |
| `https://auth.openai.com/api/accounts/oauth/token` | Authorization-code exchange and token renewal. |
| `https://auth.openai.com/.well-known/jwks.json` | ID-token verification keys. |
| `https://api.openai.com/v1/models` | Startup model catalog. |
| `https://api.openai.com/v1/responses` | Answer generation. |
| Current webpage origin plus `/__local_page_reader_<random>` | Browser-to-add-on reader request. |

Python authentication, model, and generation requests use a `urllib` opener with proxy handling disabled. This avoids routing those calls through the intercepted browser proxy. The browser's sign-in navigation still uses the browser's own network settings. See [launcher opener](../start_mitm_page_reader.py#L50) and [add-on opener](../inject_floating_stable_ai_subscription.py#L1238).

## Model catalog assumptions

The launcher expects a JSON object containing a `models` list. Each accepted item must have `visibility: "list"` and a unique `slug` matching `[a-zA-Z0-9._-]{1,96}`. Only the slug and a bounded display label reach the overlay. It does not implement a general parser for alternative response schemas.

`SIWC_MODEL` must identify an accepted slug. Otherwise, the launcher prefers `gpt-6.1-sol` when present, then the first accepted model. An empty or incompatible catalog prevents startup. The browser can select only from this startup snapshot; it does not refresh the catalog itself. See [catalog parsing](../start_mitm_page_reader.py#L268).

## Injection and limits

Injection applies to successful `GET` responses with status `200` and a `text/html` content type. Attachment responses and HTML already containing the reader marker are skipped. There is no domain allowlist. The JavaScript installs one interface in the top-level document, not in frames. The response hook reuses a script nonce when one is present; it does not remove CSP or other response headers. Site policies can still prevent operation. See [response hook](../inject_floating_stable_ai_subscription.py#L1438).

| Limit | Value |
| --- | --- |
| Captured page text | 80,000 characters |
| DOM traversal | 22,000 visited nodes; depth greater than 45 is skipped |
| Question | 2,000 characters |
| Backend title / URL fields | 300 / 1,500 characters |
| Local POST body | At most 320,000 bytes |
| Generation request | `max_output_tokens: 1800` |
| Generation connection timeout | 120 seconds passed to the HTTP opener |

Additional extraction bounds apply to tables, code blocks, math, and image descriptions. Traversal depth limits can omit content without setting the displayed truncation flag. See [DOM extraction](../inject_floating_stable_ai_subscription.py#L886) and [generation payload](../inject_floating_stable_ai_subscription.py#L1332).

## Responses and errors

The backend requests server-sent events but buffers answer text until it receives `response.completed`. The browser receives one JSON answer after completion; it does not display live token streaming. Failure, incomplete, or error events raise an error, and a stream ending without completion is rejected. See [SSE parser](../inject_floating_stable_ai_subscription.py#L1292).

At generation time, the add-on refreshes a token when expiry is within 90 seconds. It does **not** retry a Responses API `401` by refreshing and resending the generation request. Unsupported effort levels also produce an error; the user must choose Auto or another level. Most backend execution failures become local HTTP `502` responses. See [token renewal](../inject_floating_stable_ai_subscription.py#L1250) and [generation error handling](../inject_floating_stable_ai_subscription.py#L1393).
