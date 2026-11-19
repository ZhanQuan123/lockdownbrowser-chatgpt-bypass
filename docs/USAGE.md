# Using Floating Page Reader

Complete the [installation and browser proxy setup](../README.md) before opening a page. The launcher must remain running while you use the reader.

## Open the panel

1. Open or refresh a supported HTML page through the proxy.
2. Click the floating chat icon. The reader starts minimized.
3. Enter a question about the page, then click **Send** or press **Enter**.

Each submission captures the page's current HTML text. Content loaded after the page first opened can therefore be included in the next submission.

An empty submission asks the model to answer questions found on the page in their displayed order. If it finds no answerable questions, it is instructed to return a one-sentence summary.

## Controls

| Control | Action |
| --- | --- |
| Floating chat icon | Open the panel. |
| Icon or panel title bar | Drag the reader to another position. |
| Yellow circle | Minimize the panel. |
| Model name | Choose from the catalog loaded at startup. |
| Reasoning effort button | Choose Auto, Low, Medium, High, Extra High, or Max. |
| Keyboard button | Show or hide the optional on-screen keyboard. |
| Send button or Enter | Submit the current question; an empty question reads the page. |
| Shift+Enter | Insert a newline in the question. |
| Escape or click outside a menu | Close an open model or reasoning effort menu. |

The on-screen keyboard includes letters, numbers, symbols, Shift, Backspace, Space, and a newline key. Opening a model or effort menu closes this keyboard. The panel grows for answers and the keyboard, while answer cards remain scrollable.

## Models and reasoning effort

The launcher obtains the available model catalog before starting the proxy. The panel displays that catalog, and the backend accepts only model identifiers included in it. A model appearing in the menu is not a guarantee that a later request will succeed.

**Auto** omits the `reasoning.effort` field from the request. Other choices send `low`, `medium`, `high`, `xhigh` for **Extra High**, or `max`. Support varies by model. If a request rejects an effort, select **Auto** or another supported level.

When browser storage is available, the selected model and effort are saved separately for each website origin. A saved model is used only if it still appears in the startup catalog.

## Answers and history

Answers appear as cards within the current page. The backend instructs the model to provide:

- Option letters for multiple-choice questions.
- Final results, with units where needed, for math questions.
- Short direct answers for other questions.
- “Cannot determine” when the supplied content lacks the required information.

These are requested output rules, not a guarantee of correctness. The math and multiple-choice instructions explicitly suppress explanations and working.

The cards provide a visible history for the current document only. Earlier questions and answers are not included in later model requests. Reloading or navigating the page clears this history; no history export or persistent chat storage is implemented.

Mathematical answers use a built-in LaTeX-to-MathML renderer. It supports a subset of LaTeX, rather than a complete TeX engine. Unsupported syntax may appear as text, and display depends on the browser's MathML support.

## What page content is read

The reader prefers the first `main` or `[role="main"]` element. If neither exists, it reads `document.body`. It converts that DOM subtree into structured text, including headings, lists, labels, table cells, choice text, and available math markup.

Images contribute their alternative text, rather than their pixels. Labeled SVG graphics contribute a description. Canvas content becomes a placeholder. The reader does not take screenshots, run OCR, or inspect iframe contents.

The capture excludes ordinary scripts, styles, input and textarea values, buttons, embedded objects, and the reader panel itself. Math-specific script markup can be included as notation. Hidden filtering checks the HTML `hidden` attribute, `aria-hidden="true"`, and inline `display: none` or `visibility: hidden`. It does not evaluate every computed CSS rule, so it cannot guarantee that all visually hidden content is excluded.

When you submit, the reader sends the document title, website origin, extracted text, truncation flag, current question, model, and effort to the local handler. The backend forwards the relevant content to OpenAI. The standard panel sends `location.origin`, not the full page URL. See the [README](../README.md) for privacy and session handling.

## Capture and request limits

| Item | Limit |
| --- | --- |
| Extracted page text | 80,000 characters |
| Submitted question | 2,000 characters |
| Scanned DOM nodes | 22,000 |
| DOM traversal depth | 45 |
| Rows captured per table | 150 |
| Text captured per table cell | 2,000 characters |
| Requested model output | 1,800 tokens |

The reader can omit content because of these limits, the selected root element, or unsupported markup. The truncation flag reports the overall character or node limit; it does not identify every smaller extraction limit.

## Saved position and settings

When `localStorage` is available, the reader remembers the icon position, panel position, selected model, and reasoning effort for each origin. It still works when storage is unavailable, but those preferences will not survive a reload.

The reader opens only in the top-level document. It does not add separate icons inside frames.

## Check the loaded overlay version

Run this in the browser console on a page you are authorized to debug:

```javascript
document.getElementById('mitm-floating-stable-host')?.dataset.readerVersion
```

The supplied **v5.10 saved-login package** currently reports **`"5.9"`** for its overlay. This reflects the source's version marker. The older bundled text README's expected `"5.8"` value is stale.

After restarting the proxy, refresh open pages to load the new per-process handler path and local request token. See [troubleshooting](TROUBLESHOOTING.md) if the icon or an answer does not appear.
