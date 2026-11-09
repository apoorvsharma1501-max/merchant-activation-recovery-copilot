# Independent QA audit — Razorpay Problem 3 (Merchant Activation Recovery Copilot)

**Audit date:** 9 Nov 2026 · **Code audited:** commit `0716b5d` plus uncommitted evaluation files · **Data:** `data/Buildathon_Student_Data_Pack.xlsx`
**Method:** an independent audit script (kept outside the project) re-read the workbook with `openpyxl`, re-derived every decision and number without using the system's own aggregation code, ran the CLI, the Streamlit app (via `AppTest`) and the test suite, and injected synthetic edge cases. **No project source file was modified.** Every PASS/FAIL below comes from an executed check; anything not executed is marked NOT TESTED. Two automated checks that first reported FAIL turned out to be false alarms in the audit's own checks on manual inspection; they are shown as reclassified with the reason.

> Important framing: no hidden answer key is available. "Correct" in this report means *agrees with an independent re-derivation from the catalog, the brief and the evaluator's reading of the reviewer notes*. It is **not** accuracy against the organisers' answers.

---

## 1. Executive assessment

**Is it submission-ready?** **Not yet.** The *software* is close: it processes all 75 non-activated applications correctly against an independent re-derivation, it fails safely without an API key or when the API errors, and its dashboard numbers reconcile with the output table. The *submission package* is not ready. The brief requires results on ≥20 human-checked cases including failures (written Q5), a failure analysis (Q6) and a pitch video. None of these exist yet, and the evaluation files are not committed (a reproducibility risk, which the brief lists as a disqualifier).

**Three strongest elements (with evidence)**
1. **Safety-critical routing is correct and layered.** All 5 R10 cases close with no workaround wording. All 3 R12 cases go to compliance on a manual channel, with no screening terms in English or native script (C02, C03, E03). In the 42-note stress test there were 0 critical misses, including disguised and euphemistic compliance notes.
2. **Rule-first design that degrades gracefully.**
   - 71 of 75 decisions are deterministic.
   - Without a key, the 4 blank-code notes are *held for review*, not guessed (B10).
   - With an invalid key the run completes and AI is disabled cleanly (G07).
   - With no key, the default run reproduces the AI output from the committed cache (G04).
3. **Numbers are reproducible and reconcile end to end.** An independent recomputation of counts, TPV, top causes, priority scores, ranks and tiers matches the system exactly (E05, F01, F02, G02). Two runs from the cache are identical, and identical to the committed CSV (G05).

**Five most important weaknesses**
1. **AI evidence base is thin.** Only 4 real AI classifications. The 42-case stress test uses labels written by the developer. There has been no human labelling and no native-speaker review (G11, G12).
2. **Uncertain AI diagnoses are counted as RECOVERABLE.** If the model flags ambiguity on a fixable code, the message is withheld, but the case is counted in TPV at stake and ranked HIGH (C04). No current row is affected, but 6 stress-test notes would be: S09, S19, S20, S21, S40 and S41.
3. **The priority score does not behave like its "70/30" label.** Recency only spans days 0–40, so its component varies from 18 to 29 points while TPV varies from 0 to 70. Effective TPV share is about 86% (E09). The claim in the README and pitch is therefore inaccurate.
4. **Data inconsistency not detected.** In 21 of 75 non-activated rows, `days_since_last_activity` is longer than the time since `signup_date` (as of the 30 Sep 2026 snapshot). Recency drives priority, yet the validator doesn't flag this (A07).
5. **The safety net has known gaps.**
   - The keyword backstop missed 6 of 8 sensitive stress notes; the AI caught them.
   - At least 4 of 74 drafts add content not in the brief, such as "nothing to worry about", "we are here if you need help" and "Thank you for choosing to grow your business with us!" (D07).
   - A3051, the withheld R10 case, still shows `WhatsApp` as its channel (E04).
   - Code/message contradictions are not checked, against handover §5.2 Rule 1 (B06).

---

## 2. Test execution report

Status counts: **49 PASS · 6 FAIL · 4 NOT TESTED** (59 checks), after 2 false alarms were reclassified.

| ID | Test | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|
| A01 | Required sheets present | P3 sheets present | 9 sheets incl. P3_Applications, P3_RejectionCatalog | PASS | openpyxl sheet list |
| A02 | Record count & status (raw read) | 100; 25/67/8 | 100; Stalled 67, Activated 25, Rejected 8 | PASS | independent openpyxl read |
| A03 | Duplicate / missing IDs | none | 0 duplicates, 0 missing | PASS | |
| A04 | Missing values in logic fields | 0 | 0 in TPV, days, opt-in, status, step, language | PASS | blank code 51, blank message 55 (by design) |
| A05 | Numeric fields valid | numeric, ≥0 | all numeric, none negative; TPV 0.7–59.9, days 0–40 | PASS | |
| A06 | Category values & codes | within known sets | 6 languages, opt-in Yes/No, codes R01–R12 all in catalog | PASS | R13 appears only by inference |
| A07 | Cross-field consistency | no contradictions | **21 rows (19 Stalled, 2 Rejected): inactivity > days since signup** | **FAIL** | e.g. A3006 signed up 23 Sep (7 days before snapshot) but "16 days inactive"; A3016 8 vs 37 |
| A08 | No silent exclusion by loader | 100 = 100 | loader 100, raw 100, 0 issues | PASS | `dropna(how="all")` drops only empty rows |
| A09 | One output per non-activated | 75 unique = IDs | 75 rows, unique, set-equal | PASS | |
| A10 | No nudge for activated | 0 in results | 0; 25 in audit sheet | PASS | |
| B01 | All 13 codes, deterministic mapping | per catalog fixability | 11 Yes→RECOVERABLE (R13 reminder), R10→close, R12→compliance | PASS | synthetic row per code |
| B02 | Coded rows kept; text consistent with code | 49 kept, 0 contradictions | 49 kept; 0 keyword contradictions | PASS | independent keyword map |
| B03 | Blank code + comment → AI | 4 rows, catalog codes | A3022→R05, A3028→R01, A3051→R10, A3081→R09 | PASS | |
| B04 | Blank code, no comment, Stalled → R13 | R13, step named | 22 rows, all R13, step in evidence | PASS | |
| B05 | Rejected + no evidence → escalate | NEEDS_HUMAN_REVIEW | NEEDS_HUMAN_REVIEW | PASS | synthetic; no such row in real data |
| B06 | Code contradicts text → flag (handover Rule 1) | keep code, human_review=True | **R01 kept, human_review=False** | **FAIL** | `core/rules.py` Rule 1 has no consistency check; README admits this |
| B07 | Unknown code R99 | human review | NEEDS_HUMAN_REVIEW, reason recorded | PASS | |
| B08 | No inference from industry / business type | never R10/R12 | Gambling/Trust rows → R13 (Stalled) or review (Rejected); prompt has no industry | PASS | |
| B09 | AI evidence is a verbatim quote from the record | 4/4 | 4/4 quotes found in raw workbook text | PASS | |
| B10 | No-AI mode doesn't guess free text | 4 rows held | 4 → NEEDS_HUMAN_REVIEW, no message | PASS | |
| C01 | Fixability ≠ recoverability fields | R12 kept distinct | R12 = "Needs compliance review" / COMPLIANCE_REVIEW | PASS | |
| C02 | R10 closure, no workaround | 5 close, 0 workaround | 5/5 close; 0 workaround phrases | PASS | regex on back-translations |
| C03 | R12 compliance, no disclosure | 3 compliance, manual, 0 leaks | 3/3; 0 leak terms (EN + Hindi/Tamil script) | PASS | |
| C04 | AI-uncertain fixable case not auto-recoverable | NEEDS_HUMAN_REVIEW, unranked | **RECOVERABLE, human_review=True, message withheld, tier HIGH** | **FAIL** | synthetic; 0 such rows in current data |
| C05 | Rejected + insufficient evidence | escalated | NEEDS_HUMAN_REVIEW / Unknown | PASS | |
| C06 | All 75 decisions vs independent re-derivation | 0 disagreements | 0 | PASS | not the hidden key |
| D01 | Language = preference | 74/74 | 74/74 | PASS | |
| D02 | Script matches language | 0 wrong | 0 wrong (21 EN, 17 Hinglish, 14 Hindi, 13 Tamil, 5 Kannada, 4 Marathi) | PASS | independent Unicode check |
| D03 | No promises / timelines | 0 | 0 English hits; 1 native hit (A3023 ದಿನಾಂಕ) | PASS *(reclassified)* | Manual check: ದಿನಾಂಕ = "date" in "date of birth", from the R09 catalog fix. False alarm in the audit's check. |
| D04 | No links / emails / phones | 0 | 0 | PASS | |
| D05 | Messages for non-recoverable only of allowed kinds | only R10 closure / R12 neutral | 4 R10 closures, 3 R12 neutral; none for review cases | PASS | |
| D06 | Fix matches catalog topic; reminders name step | 0 misses | 0 | PASS | |
| D07 | No content beyond the brief | 0 | **≥4 drafts add content** (A3005, A3052 "we are here if you need help"; A3034 "nothing to worry about"; A3030 "Thank you for choosing to grow your business with us!") | **FAIL** | not caught by `nudge_safety.py` |
| E01 | WhatsApp only on opt-in | 0 violations | 0 | PASS | |
| E02 | No opt-in → Manual follow-up | all manual | 19/19 manual | PASS | |
| E03 | Compliance never WhatsApp | manual even if opted in | A3094, A3096 opted in → manual | PASS | |
| E04 | Withheld messages have no outreach channel | "Not applicable" | **A3051: WhatsApp** | **FAIL** | `core/rules.py::select_channel` ignores withholding |
| E05 | Independent priority recomputation | identical | max diff 0.0; 0 rank / 0 tier mismatches; HIGH 17 / MEDIUM 33 / LOW 17 | PASS | |
| E06 | Non-recoverable excluded from ranking | unranked | 8/8 UNRANKED_REVIEW, no score | PASS | |
| E07 | Missing/invalid TPV or days | flagged, not 0 | NEEDS_DATA_REVIEW, score null | PASS | synthetic |
| E08 | Weight extremes behave | monotonic | TPV-only and recency-only orders monotonic | PASS | |
| E09 | Recency weight works as labelled | ≈30% of spread | **TPV share ≈86%** (TPV part 0–70, sd 20.7; recency part 18–29, sd 3.3) | **FAIL** | design limitation, not a code bug |
| E10 | Priority not presented as probability | explicit | "not a recovery probability" in report; no probability field | PASS | |
| F01 | Independent counts/TPV vs system summary | equal | 67/5/3/75 and Rs 933.9 L all equal | PASS | |
| F02 | Top-3 causes reconcile | same | count R13, R01, R06; TPV R13, R06, R09 — same | PASS | |
| G01 | Project test suite | all pass | 121 passed | PASS | |
| G02 | App launch; tiles reconcile | no exception, equal | no exception; 4 tabs; tiles 75/67/5/3/1/933.9 | PASS | Streamlit `AppTest` |
| G03 | Rule-only CLI without key | exit 0, 75 rows, 0 calls | exit 0, 75 rows, 0 calls | PASS | key blanked in environment |
| G04 | No key, default mode | cache mode, 0 calls, 74 drafts | as expected | PASS | |
| G05 | Reproducibility (run vs run; vs committed CSV) | identical | identical | PASS *(reclassified)* | First compare flagged 6 columns; caused by pandas reading text "N/A" as NaN. Recheck with `keep_default_na=False`: identical. |
| G06 | Export CSV + Excel | written | CSV + 6-sheet xlsx | PASS | |
| G07 | Live AI failure (invalid key) | no crash; safe fallback | 401 caught; AI disabled; 4 AI rows → review; no AI text | PASS | one real 401 call, not billed |
| G08 | Rule vs AI decisions distinguishable | visible | `diagnosis_method`, `nudge_model` columns; "Decided by" in app | PASS | |
| G09 | Handover §10 schema complete | 0 missing | 0 missing | PASS | |
| G10 | Secrets / repo state | .env untracked | .env untracked; **6 evaluation paths uncommitted** | PASS | see P0-1 |
| G11 | ≥20 cases human-reviewed (handover §13–14, brief Q5) | done | sheet built, not filled | NOT TESTED | |
| G12 | Native-speaker review (Tamil/Kannada/Marathi) | done | not done | NOT TESTED | |
| G13 | Live run-to-run AI consistency | stable | not run (cache bypass costs money) | NOT TESTED | |
| G14 | Upload of other / damaged workbook via UI | handled | loader paths unit-tested only | NOT TESTED | |

Supplementary: the 42-note stress test re-ran from its saved answers with 0 API calls. Result: 37 PASS, 5 OVER_CAUTIOUS, 0 wrong code, 0 critical miss. Labels were written by the developer before the run.

---

## 3. Data and business results (computed independently)

**How calculated:**
- Statuses were counted from a raw `openpyxl` read of `P3_Applications`.
- Each non-activated row's expected code was re-derived independently:
  - the reviewer's code if present;
  - otherwise R13 if Stalled with no text;
  - otherwise the evaluator's reading of the 4 free-text notes.
- That code was mapped through the catalog's `fixable` column.
- TPV is `expected_monthly_tpv_inr_lakh` (Rs lakh), as declared by the merchant.

| Metric | Value | Calculation |
|---|---|---|
| Total applications | 100 | rows in P3_Applications |
| Activated / Stalled / Rejected | 25 / 67 / 8 | `application_status` counts |
| Non-activated | 75 | 67 + 8 |
| Recoverable | 67 | catalog `fixable = Yes` (R01–R09, R11, R13) |
| Not recoverable (close) | 5 | R10: 4 coded + A3051 via AI |
| Compliance review | 3 | R12: A3082, A3094, A3096 |
| Needs human review (unresolved) | 0 | plus 1 flagged-but-decided case (A3051) |
| Expected monthly TPV, all non-activated | Rs 1,038.4 L | sum over 75 |
| **Expected monthly TPV at stake (recoverable)** | **Rs 933.9 L** | 1,038.4 − 46.9 (R10) − 57.6 (R12) |
| Priority distribution | HIGH 17 · MEDIUM 33 · LOW 17 | quartile cut on 67 ranked |
| TPV by tier | HIGH 571.0 · MEDIUM 319.0 · LOW 43.9 | |

| Cause | Apps | TPV (Rs L) | Fixable |
|---|---|---|---|
| R13 Abandoned | 22 | 307.6 | Yes |
| R01 PAN name mismatch | 9 | 54.9 | Yes |
| R06 Policy pages missing | 7 | 128.1 | Yes |
| R03 Bank name mismatch | 7 | 77.3 | Yes |
| R02 GST invalid | 6 | 106.3 | Yes |
| R10 Restricted category | 5 | 46.9 | No |
| R05 Unreadable document | 4 | 86.5 | Yes |
| R04 Bank verification failed | 4 | 40.7 | Yes |
| R09 Signatory incomplete | 3 | 112.1 | Yes |
| R12 Compliance screening | 3 | 57.6 | Needs compliance review |
| R07 Website not live | 3 | 15.1 | Yes |
| R11 Category differs | 1 | 3.3 | Yes |
| R08 Address proof | 1 | 2.0 | Yes |

- **Top 3 by count:** R13 (22), R01 (9), R06 (7). R06 is tied with R03 at 7 and is placed ahead because of its higher TPV.
- **Top 3 by TPV:** R13 (307.6), R06 (128.1), R09 (112.1).
- **Dashboard reconciliation:** the app tiles show 75 / 67 / 5 / 3 / 1 / 933.9, identical to the above (G02).

Caveats: TPV is self-declared and is not revenue. In 21 rows the inactivity value is inconsistent with the signup date (A07).

---

## 4. Diagnosis and recoverability audit

**Correct decisions (examples)**
- **A3001, R02 coded:** the catalog fix is used word for word, and the case is recoverable via WhatsApp (opted in).
- **A3005, blank code, no text, Stalled:** R13 with the step named ("KYC docs"), and no link invented.
- **A3022, blank code, "Doc blurred and cropped":** AI chose R05 and quoted "Doc blurred and cropped" (present in the record), giving a corrective message.
- **A3051, blank code, Rejected, "Business category not supported by policy":** AI chose R10 and quoted the full note. It's closed but flagged for review, with no message drafted (the agreed design).
- **A3094, R12, opted in to WhatsApp:** routed to compliance on manual follow-up, with neutral Tamil text and no reason given.
- **Synthetic checks:**
  - Rejected with no evidence → escalated.
  - Unknown code R99 → escalated.
  - A "Gambling" industry with no evidence → never inferred as R10.

**Incorrect or questionable decisions**
- **No incorrect decision among the 75 real rows** compared with the independent re-derivation (C06).
- **Latent defect (C04):** a fixable AI code flagged ambiguous is labelled RECOVERABLE and ranked. In the stress test this applied to S09, S19, S20, S21, S40 and S41. Each would inflate TPV at stake and the HIGH tier while its message is withheld.
- **Latent defect (B06):** a coded row whose text describes a different problem keeps the code silently. There are none in the current data (B02), but the handover requires a flag.
- **Questionable reminder timing:** A3055 and A3071 get R13 reminders after only 5 days of inactivity. The data defines no minimum inactivity threshold for abandonment. This is defensible, but it's an assumption you should state.
- **Interpretation to disclose:** R12 rows have status *Rejected*, yet the merchant is told their application is "under review". This follows the catalog's own instruction and is acceptable.

---

## 5. Communication audit

- **Coverage:** 74 drafts, all in the merchant's language, in the right script (D01, D02), with no links, timelines or approval promises (D03, D04).
- **Catalog alignment:** every corrective draft covers its catalog topic and every reminder names the step (D06).
- **Variety:** 46 distinct back-translations. Identical briefs reuse the same saved answer by design.

**Good examples (evaluator read the native text and the back-translation):**
- **A3004 (Hindi, R01):** a faithful version of the catalog fix, offering both alternatives (upload the matching PAN, or correct the business name).
- **A3040 (Tamil, R03):** includes the proprietorship exception and the cancelled-cheque option.
- **A3072 (Hinglish, R08):** "3 mahine se purana" keeps the catalog's 3-month rule, the only number used.
- **A3096 (Hindi, R12):** a neutral translation of the fixed text; no "screening" or "अनुपालन" (compliance).

**Problematic examples:**
- **Content beyond the brief (D07):**
  - A3005 and A3052: "we are here if you need help" implies a support channel the data doesn't define.
  - A3030: "Thank you for choosing to grow your business with us!" is marketing tone.
  - A3034: "Chinta ki koi baat nahi" ("nothing to worry about") could read as minimising a blocker.
  - Low harm, but the prompt says to add nothing, and the checks don't catch it.
- **Back-translation is self-reported** by the same model. It isn't independent proof of meaning for Tamil, Kannada or Marathi. No native-speaker check has been done (G12).
- **Channel error (E04):** A3051 shows `WhatsApp` with no permitted message. An operator could read that as "send via WhatsApp".
- **No language or channel errors** in the 74 drafts.

---

## 6. Safety and human-in-the-loop audit

| Case / scenario | Risk type | Current behaviour | Residual risk |
|---|---|---|---|
| Sensitive free text the AI misses | Compliance | Keyword backstop missed 6/8 sensitive stress notes (OFAC, betting, adverse media, risk team…); only the AI caught them | Medium: single point of failure for euphemisms |
| Ambiguous AI diagnosis on a fixable code (C04) | Operational / reporting | Message withheld (safe) but counted RECOVERABLE and ranked | Medium: TPV and HIGH tier overstated; ops calls the wrong merchants first |
| Code contradicts reviewer text (B06) | Operational | Code trusted silently | Low–medium: wrong fix sent; merchant fails again |
| A3051 channel label (E04) | Compliance / reputational | WhatsApp shown for a withheld R10 case | Low: operator confusion on the very case used in the demo |
| Drafts adding reassurance or offers of help (D07) | Reputational | 4 drafts; passes all checks | Low: implies support the business may not provide |
| Translation quality | Reputational | Script check plus same-model back-translation | Medium until a native speaker reviews |
| Inconsistent inactivity data (A07) | Operational | Used as-is in priority | Low–medium: recency for 21 rows is unreliable |
| R10 closure messages drafted automatically | Governance | Drafted; nothing sent; `nudge_review_required=True` | Acceptable (approval required) |
| API failure / no key | Operational | Safe fallback, tested (G03, G04, G07) | Low |
| Prompt injection in reviewer text | Compliance | Stress test: 3/3 injections didn't change the code; disguised sanctions hit still routed to compliance | Low on tested cases |

---

## 7. Priority fixes

| # | Pri | Issue | File | Exact correction |
|---|---|---|---|---|
| 1 | **P0** | Evaluation work not committed (stress test, its cache, labelling tool): results can't be reproduced by a judge | repo | `git add evaluation/ cache/stress_llm_cache.json` and commit |
| 2 | **P0** | No human-checked results on ≥20 cases (brief Q5; handover §14) | `evaluation/labelling/p3_labelling_sheet.xlsx` | You fill the yellow columns, then run `python -m evaluation.labelling score`; report the agreement and every disagreement |
| 3 | **P0** | Withheld case shows WhatsApp (A3051), visible in the demo | `core/output_builder.py` | After `nudge = …`, set `channel = config.CHANNEL_NOT_APPLICABLE if nudge.status is NudgeStatus.NO_NUDGE_HUMAN_REVIEW else channel`; add a test |
| 4 | **P0** | Submission artefacts missing: failure log, written answers Q1–Q8 + P3 extras, video | `docs/` | Write from this audit and the stress report; quote real numbers only |
| 5 | P1 | Uncertain AI diagnosis counted as RECOVERABLE (C04) | `core/rules.py::decide` | When `diagnosis.method is LLM_TEXT_CLASSIFICATION and diagnosis.human_review` and catalog fixability is Yes → return `NEEDS_HUMAN_REVIEW` (keep the suggested code). Keeps it out of TPV and ranking |
| 6 | P1 | Keyword backstop misses euphemisms | `config.py::SENSITIVE_TEXT_PATTERNS` | Add `bet`, `betting`, `ofac`, `\bpep\b`, `adverse media`, `high-risk`, `risk team`, `\bl2\b`, `do not process`, `flagged`; re-run the stress test and report the false-positive change (S34/S35 type) |
| 7 | P1 | "70/30" weighting misdescribed (≈86/14 in effect) | `core/prioritization.py` or docs | **Your business decision:** either (a) rescale recency to a 0–100 percentile like TPV, or (b) keep the formula and state "TPV dominates (~86% of score variation)". Don't change silently |
| 8 | P1 | Inactivity > account age in 21 rows not detected | `core/data_loader.py` | Add a WARNING per row when `days_since_last_activity` > days from `signup_date` to the snapshot (30 Sep 2026, from README); show it in the data-quality report. Don't alter values |
| 9 | P1 | Drafts add content beyond the brief | `prompts/nudge_system.txt`; `core/nudge_safety.py` | Add the rule "no reassurance, offers of help, marketing or thanks beyond one closing 'Thank you'"; add a check for `here (if|for) you`, `help`, `worry`, `choosing`; bump `NUDGE_PROMPT_VERSION` (re-run costs about $0.5) |
| 10 | P1 | Contradiction check missing (handover Rule 1) | `core/rules.py::diagnose` | Minimal: flag `human_review` when coded text is present and the AI classifier (already built) returns a different catalog code. Cost: 49 small calls (about $0.3). Otherwise document it as a known limitation |
| 11 | P1 | No native-speaker check | process | 2 drafts each in Tamil, Kannada and Marathi reviewed by a native speaker using the labelling columns |
| 12 | P2 | No minimum inactivity before an R13 reminder | `core/rules.py` / config | Optional threshold (e.g. 7 days) → "monitor" status; state it as an assumption |
| 13 | P2 | Unused engagement signals (`attempts`, `support_contacts`) | `core/prioritization.py` | Optional tiebreak; e.g. 5 LOW-tier cases have ≥3 attempts (A3040, A3041, A3043, A3072, A3080) |
| 14 | P2 | Live run-to-run consistency untested | `evaluation/` | Run the 4 real notes 3× bypassing the cache (about $0.05) |
| 15 | P2 | UI upload path untested | `app.py` | Upload a workbook missing a column and confirm the error is shown |

---

## 8. Submission-readiness verdict

| Dimension | Score | Justification |
|---|---|---|
| Business logic | **4/5** | 75/75 decisions agree with the independent re-derivation (C06); R10/R12/R13 rules correct (B01, C02, C03). Lost a point for C04 (uncertain → recoverable), E09 (weighting mismatch) and the unstated 5-day reminder assumption. |
| Data correctness | **4/5** | Counts and TPV verified from the raw workbook; no silent exclusion (A02–A10, F01). Lost a point for the undetected 21-row inactivity/signup inconsistency (A07). |
| Working application | **4/5** | Launches, renders, reconciles, exports, runs with no key and with a failed key (G01–G09). UI upload not exercised (G14); evaluation files uncommitted. |
| AI reliability | **3/5** | 4/4 real AI cases have a verbatim quote and agree with the evaluator's reading; stress test 0 wrong codes / 0 critical misses on 42 notes. But the labels are the developer's, the sample is small, the backstop is weak (6/8 missed), 4 drafts add content, and consistency is untested. |
| Safety & governance | **4/5** | No sends; WhatsApp gate holds (E01–E03); no compliance leaks (C03); safe fallbacks (G07). Lost a point for E04, C04 and the backstop gap. |
| Presentation readiness | **2/5** | Dashboard and executive summary are solid, but there are no human-labelled results, no failure log, no written answers and no video, and the evaluation evidence isn't committed. |

---

## 9. Interview risk register

1. **"Your system agrees on 75/75. How do you know it's accurate?"** We don't have the hidden key. We report agreement with an independent re-derivation, plus your human labels (once filled). 71 of 75 are deterministic catalog lookups. The real uncertainty is in 4 AI cases and the messages.
2. **"AI decides only 4 diagnoses. Why use an LLM at all?"** Its main value is the 74 messages in 6 languages, which rules can't write, plus reading unstructured notes. Decisions stay rule-based on purpose. The full run cost about $0.49.
3. **"Why 70/30, and does recency even matter?"** Be honest: in effect TPV drives about 86% of the score variation, because recency spans only 0–40 days. Sensitivity: recency-only shares 3 of 10 top cases. These are prototype weights, to be calibrated with outcome data.
4. **"Why rank recently active merchants above long-stalled ones?"** The assumption is that recent activity means higher intent. Long-stalled merchants still get a reminder, just later in the queue. With real data we'd A/B test reminder timing.
5. **"A3051 was classified by the AI as restricted. What if it's wrong?"** No message is drafted and the case is flagged for a person. The evidence is the full verbatim note. Closure only happens after human confirmation.
6. **"How do you stop compliance reasons leaking in Tamil?"**
   - The English R12 text is fixed, not generated.
   - Translations are scanned in English and native script.
   - The channel is forced to manual.
   - A person approves every message.
   - The remaining risk is translation nuance, which needs native review.
7. **"Your keyword safety net missed 'OFAC' and 'betting'. So is there really a second layer?"** Yes, we found it in our own stress test. The fix is to extend the list and re-measure. The AI caught all 8 cases, but we don't rely on one layer.
8. **"Some inactivity values are longer than the account's age. Did you notice?"** Yes: 21 of 75 rows. We report it as a data-quality issue; it affects recency for those rows. Without a corrected source, we don't alter the values.
9. **"You remind merchants after 5 days. Isn't that premature, and why ignore attempts and support contacts?"** The brief defines no threshold. A reminder is low-cost and needs approval. Engagement signals are the next refinement (5 LOW-tier merchants made ≥3 attempts).
10. **"Is Rs 933.9 lakh what Razorpay would earn?"** No. It's merchants' self-declared expected monthly payment volume for recoverable applications. It isn't recovered volume, revenue or a forecast; P3 gives no take-rate or conversion assumption.

---

## 10. Final action plan (shortest path)

1. **Commit the evaluation files** (P0-1). About 5 minutes.
2. **Fix the A3051 channel label** and add a test (P0-3). About 15 minutes.
3. **You fill the 30-case labelling sheet** and run the scorer (P0-2). About 40 minutes.
4. **Apply P1 fixes 5, 6, 8 and 9.** Decide fix 7 (weighting) yourself. Re-run the pipeline and stress test and record before/after. About 1–2 hours, about $0.5–1.
5. **Native-speaker check** of 6 drafts (P1-11).
6. **Write the failure log, written answers and video script** from this report, the stress report and your label results (P0-4). Then commit and submit.

*Audit scripts and raw outputs are kept outside the repository and can be re-run; they are not part of the submission.*

---

## Post-audit changes (the audit findings above are unchanged; they describe commit `0716b5d`)

| Item | Status | Detail |
|---|---|---|
| P0-1 Commit evaluation files | **Done** (`7eddd1e`) | Stress test, its saved answers, labelling tool, this report |
| P0-3 / E04 Withheld case showed WhatsApp | **Fixed** | `core/output_builder.py`: when `nudge_generator.should_withhold()` is true, channel = "Not applicable". This also covers AI-uncertain cases, not only A3051. A draft that merely *failed a safety check* keeps its channel, because the case is still actionable after a person rewrites it. Outputs regenerated from saved answers (0 API calls); diff vs previous output: **only** A3051 `recommended_channel` WhatsApp → Not applicable. Test added in `evaluation/test_ai.py`. Blank labelling sheet rebuilt (it had 0 filled cells). |
| P1-5 / C04 Uncertain AI → recoverable | **Fixed** | `core/rules.py::decide`: an AI-classified fixable code with `human_review` → NEEDS_HUMAN_REVIEW (suggested code kept). Stress cases S09, S19–S21, S40, S41 now go to review; real data unaffected (0 such rows). |
| P1-6 Keyword backstop gaps | **Fixed** | `config.SENSITIVE_TEXT_PATTERNS` widened. Stress test (re-run from cache, 0 API calls): backstop alone now catches **8/8** sensitive notes (was 2/8); non-sensitive notes it flags unchanged at 2 (S34, S35). |
| P1-7 / E09 Weighting misdescribed | **Documented, formula unchanged** | Effective TPV share computed and shown (executive summary, app, README): about 86%. Changing the formula is left to the student as a business decision. |
| P1-8 / A07 Inactivity > account age | **Fixed (flag only)** | `core/data_loader.py`: 21 WARNINGs and a `data_flags` entry per row; values not altered. |
| P1-9 / D07 Extra content in drafts | **Fixed** | Prompt `nudge-v2` forbids reassurance, help offers and marketing; `nudge_safety.check` blocks them. Live re-run: extra-content drafts **6 → 0** (the audit's regex found 3; A3030, A3071 and A3087 also had "grow your business"). 0 safety failures, 0 retries. |
| P1-10 / B06 Code/text contradiction | **Fixed** | `core/ai_diagnosis.check_consistency`: AI reads the text on coded rows; a different catalog code → human review, original code kept. Live: all 25 distinct coded notes read; AI agreed on 47/49 rows, UNKNOWN on 2 (R12 "Compliance review pending"), 0 flagged. |
| P1 live re-run | Done | 70 API calls, 78,289 in / 15,522 out tokens (about $0.62). Decisions, channels, ranks, tiers **unchanged**; only message texts, prompt version and data flags changed. |
| P1-11 Native-speaker review | Open (student) | — |
| P0-2 Human labelling of 30 cases | Open (student) | Sheet rebuilt with the v2 drafts (it had 0 filled cells) |
| P0-4 Failure log, written answers, video | Open | — |
