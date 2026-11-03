# Anonymizer LLM
[![CI](https://github.com/lorenz00k/anonymizerLLM/actions/workflows/ci.yml/badge.svg)](https://github.com/lorenz00k/anonymizerLLM/actions/workflows/ci.yml)

[![Security](https://github.com/lorenz00k/anonymizerLLM/actions/workflows/security.yml/badge.svg)](https://github.com/lorenz00k/anonymizerLLM/actions/workflows/security.yml)

A local privacy filter for AI chat websites. A Chrome extension intercepts your message before it is sent to [claude.ai](https://claude.ai), replaces sensitive data (names, e-mail addresses, IBANs, phone numbers, internal secrets) with realistic placeholders, and swaps the real values back into the answer, so the chat stays readable for you while the provider never sees the originals.

Everything runs on your own machine. Detection happens in a local Python host and, optionally, a local LLM via [Ollama](https://ollama.com). Nothing is sent to a third-party service.

> **Status:** early development, works on claude.ai only. Currently tested on Linux with Chrome/Chromium.

## How it works

```
claude.ai  ──►  Chrome extension  ──(Native Messaging)──►  Python host (piifilter)
                (intercepts send,                           ├─ 1. Custom rules
                 review panel,                              ├─ 2. Regex
                 restores answers)                          ├─ 3. Presidio NER (German)
                                                            └─ 4. Local LLM via Ollama (optional)
```

Detection runs in phases:

1. **Instant, automatic (stages 1–3).** All three stages scan the original text independently. Overlaps are resolved by priority (custom rules > regex > Presidio), then everything is replaced in one pass. Further occurrences of an already detected value (e.g. a first name that appears alone later) are masked consistently.
2. **LLM suggestions (stage 4, optional).** A local model looks for things the pattern-based stages cannot see: trade secrets, internal project names, employee IDs, salaries, API keys and other credentials. It only *suggests*, nothing is replaced yet.
3. **Review.** A panel in the page lets you accept, decline (or "decline all"), or ask for a new rewording of each suggestion before the message is sent.

The mapping of placeholders to originals (the "vault") is stored per chat, so answers can be translated back to the real values, including after a page reload. Restored words are highlighted in the response.

### Detection stages

| Stage | What it finds | Notes |
|---|---|---|
| Custom rules | Your own words and phrases | Case-insensitive, case-preserving replacement. Three tiers: global, folder, chat. |
| Regex | E-mail, IBAN, phone numbers | |
| Presidio | Person names, locations | spaCy model `de_core_news_lg`, so German text works best. |
| Local LLM | Company secrets, personal identifiers, technical secrets | Uses Ollama with `llama3.2` by default. Beta, off by default. |

## Requirements

- Linux with Google Chrome or Chromium
- Python 3.10+
- About 600 MB of disk space for the spaCy model and its dependencies
- Optional, for the LLM stage: [Ollama](https://ollama.com) running locally with the `llama3.2` model
- Only for development: Node.js 22 and npm (used for linting the extension)

## Installation

1. **Load the extension.** Open `chrome://extensions`, enable *Developer mode*, choose *Load unpacked* and select the `browser_extension/` folder. Note the extension ID.

   The native messaging manifest template currently allows one fixed extension ID. If yours differs, the installer fills in the ID you enter.

2. **Run the installer** from the repository root:

   ```bash
   ./scripts/install_linux.sh
   ```

   It creates a virtual environment in `host/.venv`, installs the host (`pip install -e host`), downloads a German spaCy model, asks for the extension ID and installs the native messaging manifest for Chrome or Chromium.

3. **Restart the browser completely** (including background processes). The first host start is slow because Presidio has to load the language model.

4. **Optional, LLM stage.**

   ```bash
   ollama pull llama3.2
   ```

   Then enable *KI-Erkennung (Beta)* in the extension popup.

## Usage

Open claude.ai and chat as usual. The extension popup has three switches:

- **Filter aktiv**: turns anonymization on or off.
- **Rückübersetzen aktiv**: restores real values in answers.
- **KI-Erkennung (Beta)**: enables the local LLM suggestions and review panel.

### Managing custom rules

The rules UI is a small local web app, separate from the browser extension. Start it with:

```bash
source host/.venv/bin/activate
piifilter-rules-ui
```

Then open <http://127.0.0.1:8756> (the popup's *Regeln verwalten* button links there). It only listens on localhost. Rules apply at three levels (global, folder, single chat) and are stored in `~/.piifilter/custom_rules.json`, outside the repository, so they survive reinstalls.

To keep it running in the background, you can run it as a systemd user service pointing at `host/.venv/bin/piifilter-rules-ui`.

## Development

```bash
cd host && pip install -e ".[dev]"   # package + pytest + ruff
ruff check host && ruff format --check host && pytest host
npm ci && npm run lint               # browser extension
```

Unit tests are in `host/tests/`. The scripts in `host/evals/` try the real LLM stage and need a running Ollama, so they don't run in CI.
## Debugging

- Host log: `/tmp/pii_filter_host.log`. The level is set in `host/src/piifilter/logger.py`; trace/debug levels may contain plaintext PII, so keep it at `INFO` for normal use.
- To check the Ollama connection, run `python host/evals/check_ollama.py`.

## Limitations and roadmap

- Only claude.ai is supported; ChatGPT and Gemini are planned.
- The installer is Linux-only; the log path is Linux-specific.
- The rules UI does not start automatically yet.
- The LLM stage is best-effort: it can miss things or flag too much, which is why it goes through review.
- Cold starts are slow. The first host start after a browser restart is slow because Presidio has to load the spaCy model, and the first LLM request can take 15 seconds or more while Ollama loads the model into memory. The host warms the model up on start, and Ollama unloads it after 30 minutes of inactivity, so the next request after a longer pause is slow again.
- The Ollama server must be running for the LLM stage. If it isn't, the stage silently returns no suggestions and the other three stages keep working.
- Prompts for the LLM stage and the language model are German-oriented.
- Packaging for easier distribution (standalone host, Chrome Web Store) is planned.

## License

Apache License 2.0, see [LICENSE](LICENSE).