# Publishing on GitHub

The documentation bundle contains the original five supplied files, a new README, detailed guides, and a `.gitignore`. Application source is unchanged. The bundle is ready for GitHub upload.

## Upload the project

1. Extract `floating-page-reader-github.zip` into a working directory.
2. Create an empty GitHub repository under the intended owner. A suggested repository name is `floating-page-reader`.
3. Open that repository's **Add file > Upload files** page, or follow GitHub's instructions for pushing an existing local project.
4. Upload the contents of the extracted project directory so `README.md` appears at the repository root. Include `docs/` and the application files.
5. Include `.gitignore`; some file pickers hide dotfiles. GitHub's file editor can create it if necessary.
6. Commit the files and check that the README links and diagram render correctly.

Use a private repository while resolving ownership, license, and compatibility questions if the project is not ready for public release.

Suggested repository description:

> A Windows floating webpage reader using mitmproxy, structured HTML extraction, and an encrypted local sign-in cache.

## Before a public release

- Choose a license with the project's rights holder. No license is supplied in the source archive.
- Confirm the sign-in integration is supported for this application and account. Identity sign-in and model usage authorization are separate concerns.
- Test installation, HTTPS proxying, initial sign-in, cached restart, token renewal, model selection, and at least one complete answer.
- Record the Windows, Python, browser, mitmproxy, PyJWT, and cryptography versions used for that test. Dependencies are currently unpinned.
- Decide whether to align the package's v5.10 label with the frontend's `5.9` label in a later code change.
- Review release contents for credentials, account identifiers, captured traffic, private page content, and certificate private keys.

The included `.gitignore` helps prevent accidental commits, but it does not remove already tracked files or protect manual uploads. Do not upload `%USERPROFILE%\.floating_page_reader` or `%USERPROFILE%\.mitmproxy`.

## Report problems usefully

Include the failing step, exact redacted error, component versions, whether the page uses HTTP or HTTPS, and whether traffic appears in mitmweb. Say whether authentication was fresh or cached. A small public test page is preferable to a private page capture.

Never include tokens, callback URLs, authorization headers, `session.dpapi`, `registration.json`, certificate private keys, or unredacted traffic captures. The [troubleshooting guide](TROUBLESHOOTING.md) covers common symptoms.

Return to the [README](../README.md).
