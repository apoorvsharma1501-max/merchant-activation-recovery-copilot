# Merchant Activation Recovery & Diagnosis Copilot

Razorpay Campus AI Build-a-thon, Problem 3 (onboarding & KYC drop-off recovery).
Synthetic data only. This is a drafting and decision-support prototype: **it never sends messages**.

## Status

| Phase | Scope | State |
|---|---|---|
| 1 | Load, validate and profile the workbook | Done |
| 2 | Deterministic rules, rule-based output table, tests | Done |
| 3 | AI classification of blank-code reviewer text; multilingual nudges; safety checks; cache | Done; live run 2026-11-09 (51 calls, ~$0.49), answers cached |
| 4 | Prioritisation, cause analytics, executive summary | Done |
| 5 | Streamlit interface | Done |

## Setup (Windows)

```
py -3.12 -m venv .venv          # or: python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env          # then put your key after ANTHROPIC_API_KEY=
```

## Run

```
.venv\Scripts\python run_pipeline.py              # live AI if a key is set, else cached answers only
.venv\Scripts\python run_pipeline.py --llm off    # rules only, no AI
.venv\Scripts\python run_pipeline.py --llm cache  # replay saved AI answers; never calls the API
.venv\Scripts\python -m pytest                    # test suite (uses a fake model; free)
.venv\Scripts\streamlit run app.py                # the app, at http://localhost:8501
```

### The app (`app.py`)
- **Sidebar:** pick the supplied workbook or upload one; AI mode (saved answers / rules only / live – live appears only when a key is set); Run analysis. A standing banner says nothing is sent.
- **Overview:** headline counts, Expected monthly TPV at stake, outcome and step breakdowns, top three causes by count and by TPV, abandonment by step. Every chart has a table view.
- **Application work queue:** search and filter; click a row for the full diagnosis, evidence, who decided (rule or AI), decision, priority and source record. Compliance and closure cases show a warning.
- **Merchant nudge review:** the draft, its English back-translation, channel, WhatsApp opt-in and safety-check result. No send button; copy or download only.
- **Evaluation & audit:** rule vs AI coverage, AI-classified cases, human-review cases, safety failures, provenance (model, prompt and rule versions, tokens), weight sensitivity, data issues, CSV/Excel download.

Outputs:
- `outputs/data_quality_report.md` – profile of the workbook
- `outputs/p3_results.csv` / `.xlsx` – one row per non-activated application (xlsx adds `summary`, `activated_audit`, `data_issues` sheets)
- `outputs/executive_summary.md` – headline counts, TPV at stake, top causes, HIGH-priority list, weight sensitivity
- xlsx also has `work_queue` (recoverable rows in priority order), `causes`, `abandonment_by_step`, `priority_sensitivity`
- `cache/llm_cache.json` – every AI answer, keyed by model + prompt. Committed so results reproduce without a key.

## Prioritisation (prototype heuristic)

Only RECOVERABLE rows are ranked. `priority_score = 0.7 × TPV percentile + 0.3 × (100 − days inactive)`; weights in `config.py`. Tiers: top 25% HIGH, middle 50% MEDIUM, bottom 25% LOW. This orders follow-up work; it is **not** a recovery probability. The `priority_sensitivity` sheet compares TPV-only, recency-only and other weightings (top-10 overlap and rank correlation with the base order).

## What AI does, and what it does not

| Job | Who decides | Why |
|---|---|---|
| Which catalog code applies when a code exists | Rules | Catalog is the source of truth |
| Fixable / recoverable / close / compliance | Rules, from the catalog's `fixable` column | Safety-critical; must be predictable |
| Channel (WhatsApp only on explicit opt-in) | Rules | Brief's hard rule |
| What a message may say (the `nudge_brief`) | Rules, catalog wording only | Stops invented advice |
| Classify reviewer text that has no code | **AI** proposes; code validates | Free text varies; rules can't read it reliably |
| Write the message in the merchant's language | **AI** | Six languages incl. Tamil, Kannada, Marathi |
| Approve or send anything | **A person** | Nothing is sent by this tool |

Model: `claude-opus-5-5` (Anthropic) with JSON-schema structured output. Effort `medium` for classification, `low` for messages. Server-side refusal fallback is enabled (`config.LLM_USE_REFUSAL_FALLBACK`).

### Guardrails on AI classification (`core/ai_diagnosis.py`)
- Only the reviewer note and the catalog are sent – no ID, name, city or TPV.
- The code must be in the catalog (enforced by the schema and again in code).
- `evidence_quote` must appear word-for-word in the note, or the answer is rejected.
- One retry with the rejection reason; then human review.
- A keyword guard for restricted/compliance wording can only add caution. Sensitive cases (e.g. A3051 → R10) are closed/routed but **flagged for human review with no message drafted**.

### Guardrails on messages (`core/nudge_safety.py`)
Every draft is checked on the message and its English back-translation for: links, emails, phone numbers, internal codes, numbers not in the brief, promises/timelines, compliance disclosure (R12 and sensitive cases), workarounds (R10), missing step name (reminders), wrong script for the language, and length. A failing draft is retried once; if it still fails it is kept for reviewers but marked `NO_NUDGE_HUMAN_REVIEW`. The English R12 text is fixed and never generated. These checks catch known failure types; they do **not** prove translation quality – a person reviews every draft.

## How diagnosis works

1. **Known code** → use it as given (`CATALOG_RULE`).
2. **Blank or invalid code + reviewer text** → AI classification as above (`LLM_TEXT_CLASSIFICATION`); without AI it stays in human review.
3. **No code, no text, status Stalled** → R13 abandonment, naming the exact step reached (`INACTIVITY_RULE`). Rejected with no evidence is **not** assumed to be inactivity.
4. **Unknown status / anything unresolved** → human review.

## Assumptions (also marked `ASSUMPTION` in `config.py`)

- Cells that are empty or hold only `—`, `-`, `n/a`, etc. are treated as missing.
- Only "Yes" (any case) counts as WhatsApp opt-in; otherwise "Manual follow-up" (no email or phone exists in the data).
- "Expected monthly TPV at stake" is the expected TPV of applications classified RECOVERABLE. It is not recovered TPV, revenue, or a forecast.
- `typical_days_to_fix` is reference only and is never promised to merchants.
- Without AI, only English rows get a message (fixed templates from catalog wording); other languages are `NOT_GENERATED` rather than silently sent in English.

## Known limitations

- Code/message contradiction checks for already-coded rows are not implemented.
- Script and keyword checks cannot judge translation quality; native-speaker review of Tamil, Kannada and Marathi drafts is still needed.
- Priority weights are an assumption, not fitted to outcomes (no recovery labels exist in the data).
- "Expected monthly TPV" is self-declared at signup and may be optimistic.
