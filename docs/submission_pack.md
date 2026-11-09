# Submission pack: Problem 3, Merchant Onboarding and KYC Drop-off Recovery

**Product:** Merchant Activation Recovery & Diagnosis Copilot
**Source of every number:** the current implementation (commit `eba7e3d`), re-run from saved AI answers on 9 Nov 2026 with 0 API calls. All 155 automated tests pass, and the dashboard tiles match the output table.
**Units:** TPV figures are *expected monthly TPV* in Rs lakh, as declared by merchants at signup. This is **not** recovered TPV or revenue. The data contains no recovery outcomes.

> **Before you submit:** this is a draft prepared with Claude (an AI assistant). The brief requires individual work and that you can explain every choice. Read each answer, change anything that isn't how you'd say it, and see the "Personalise" list at the end.

---

## Deliverable 1: Requirement coverage matrix

Wording is quoted from the official brief (sections 3, 4 and 5). "Fully" means built, run on the full data and evidenced. "Partially" means built, but the evidence is incomplete. "Proposed" means designed, not built.

| # | Exact requirement (brief) | Type | How the solution addresses it | Evidence | Status |
|---|---|---|---|---|---|
| T1 | "(1) diagnoses why it stalled" | Task | Catalog rules for coded rows; R13 for stalled rows with no code and no note; AI for free-text notes, which must quote the note | `diagnosed_reason_code`, `diagnosis_evidence`: 75/75 rows | Fully |
| T2 | "(2) explains the fix in simple language in the merchant's preferred language (English, Hindi, Hinglish, Tamil, Kannada or Marathi)" | Task | Rules write a brief from catalog wording; AI writes it in the preferred language; script and safety checks | `nudge_text` + `nudge_english_back_translation`: 74/74 in the right language and script | Fully (native-speaker check pending) |
| T3 | "(3) decides whether the case is recoverable or must be closed or routed to compliance" | Task | Catalog `fixable` → RECOVERABLE / NOT_RECOVERABLE_CLOSE / COMPLIANCE_REVIEW / NEEDS_HUMAN_REVIEW | `recoverability`: 67 / 5 / 3 / 0 | Fully |
| T4 | "(4) drafts the right nudge" | Task | Corrective, reminder, closure or neutral-compliance message by case type | `recommended_action`, `nudge_status` | Fully |
| T5 | "Also tell the product team which fixable causes affect the most merchants." | Task | Cause tables by count and by TPV, plus abandonment by step | `outputs/executive_summary.md`; app Overview tab | Fully |
| M1 | "For every non-activated application: diagnosed cause, fixable or not, recoverable or not, and a drafted nudge in the merchant's language and a suitable channel (WhatsApp only if opted in)." | Minimum | See Part C | 75/75 cause, fixability, recoverability, channel; 74/75 nudges (A3051 held for human confirmation by design) | Fully |
| M2 | "Never suggest a workaround for restricted business categories, and never reveal compliance screening reasons to the merchant." | Minimum | R10 closure brief forbids workarounds; R12 gets fixed neutral text only, manual channel; scans in English and native script | 0 workaround phrases; 0 compliance terms; QA audit C02/C03 | Fully |
| M3 | "A summary: how many applications are recoverable, expected TPV at stake, and the top three systemic causes." | Minimum | Executive summary and dashboard | 67 recoverable; Rs 933.9 L; top 3 in Part E | Fully |
| S1 | "Prioritise nudges by TPV and days since activity." | Stretch | Score = 0.7 × TPV percentile + 0.3 × (100 − days inactive); HIGH / MEDIUM / LOW tiers | `priority_*` columns, `work_queue` sheet, sensitivity sheet | Fully |
| S2 | "Propose a product change to prevent the top cause." | Stretch | Data analysis is built; the product change is a written proposal | Part D2 | Proposed (analysis built) |
| S3 | "Design a follow-up sequence with stopping rules." | Stretch | Written design; not built into the app | Part D3 | Proposed |
| E1 | "Diagnosis accuracy against hidden answers, including the blank-code cases." | Measure | Can't be measured without the key. Proxies: independent re-derivation 75/75 agree; 42-case stress test, 0 wrong codes | QA audit C06; `evaluation/results/stress_report.md` | Partially evidenced |
| E2 | "Correct handling of the non-fixable and compliance cases, and fixed-versus-recoverable counts." | Measure | Fixable 67 / recoverable 67 / close 5 / compliance 3 | Part E | Fully |
| E3 | "Clarity, tone and language quality of the nudges." | Measure | Automated checks (script, promises, links, extra content); human approval required | 0 safety failures | Partially evidenced (no native-speaker review yet) |
| A | "(a) your working solution (link, file, or screen recording)" plus "the output table described in your problem" | Submission | Git repo, Streamlit app, `outputs/p3_results.csv` / `.xlsx` | Local repo; no shareable link yet | Partially (needs a link or recording) |
| B | "(b) a 5-minute pitch video" | Submission | Outline in the Appendix | — | Not done |
| C | "(c) your answers to the questions in Section 5", "100 to 150 words" each | Submission | Deliverable 2 below | Word counts checked | Drafted |
| G1 | "Tell us which [AI tools], and what they did versus what you decided." | Ground rule | Answer 4 | — | Drafted |
| G2 | "Never invent facts, promise refunds, dates or waivers… or take irreversible actions without a human check." | Ground rule | No sending; every draft needs approval; promise and timeline checks | QA audit D03/D04 | Fully |

---

## Deliverable 2: Written answers (Section 5C, 100–150 words each)

### All problems

**1. Which problem did you pick, and who is the main user (merchant, CSM, support agent)?**

<!-- answer:Q1 -->
I picked Problem 3, merchant onboarding and KYC drop-off recovery. The main user is the onboarding operations specialist, who has to work out why each application stalled and what to do next, usually from a short, technical reviewer note. The merchant is the second user: a small business owner who often cannot tell what "GSTIN inactive / legal name mismatch" asks them to do, and may prefer Tamil or Hinglish to English. The product team is the third user, because the same errors repeat across merchants. In the data pack, 75 of 100 applications are not activated (67 stalled, 8 rejected), declaring Rs 1,038 lakh of expected monthly payment volume between them. My copilot gives the specialist, for every one of those 75, a diagnosis with evidence, a decision, a priority and a message ready for approval.
<!-- /answer -->

**2. What does a good outcome look like in numbers today, and what does your solution change?**

<!-- answer:Q2 -->
The data pack has no recovery history, so "good" has to be defined rather than measured. I would judge success by the share of stalled merchants who clear their blocked step within 14 days, the activation rate, time from signup to activation, and specialist minutes per case. What the solution changes today is the work that comes before those outcomes. All 75 non-activated applications now have a cause, a fixable and recoverable decision, and a next action, and 74 have a draft message in the merchant's own language. 67 are recoverable, representing Rs 933.9 lakh of expected monthly TPV, and the 17 HIGH-priority cases hold 61% of it, so a team can start where the value is. I cannot claim a conversion uplift: that has to be measured in a pilot against a control group.
<!-- /answer -->

**3. What does AI do in your solution, and what is deliberately left to rules or humans? Why?**

<!-- answer:Q3 -->
Rules make every decision that carries risk. Known rejection codes (49 cases) map directly to the catalog, and stalled applications with no code and no note become abandonment reminders (22 cases). Fixability, recoverability, channel and priority are all computed in code, so they are predictable and testable. AI does two jobs that rules cannot: it reads reviewer notes that have no code (4 cases), and it writes messages in six languages (74 drafts). Even there it is constrained. It may only choose a catalog code, must quote the note word for word, and writes from a brief the rules have already approved. People approve every message, confirm sensitive cases such as A3051, and handle all compliance contact. The reason is asymmetric risk: a wrong closure or a leaked screening reason costs far more than a slower manual check.
<!-- /answer -->

**4. Which tools and models did you use, and why those?**

<!-- answer:Q4 -->
I built the solution with Claude Code (Claude Opus 5.5), which wrote most of the Python code, tests and dashboard under my direction and challenged it in an independent audit. Inside the application, the Anthropic API with claude-opus-5-5 classifies uncoded reviewer notes and drafts multilingual messages, using a fixed JSON format so every answer can be checked automatically. I used one strong model because volumes are small and quality in Tamil, Kannada and Marathi matters; three live runs cost about USD 1.50 in total. Python and pandas process the data, Streamlit provides the review dashboard, pytest runs 155 automated tests, and Git tracks every change. Every AI answer is saved, so results reproduce without an API key. Decisions I made include holding A3051 for human review, using a live API rather than pre-written text, and keeping value-led prioritisation.
<!-- /answer -->

**5. How did you test it? Show results on at least 20 cases, including the ones it got wrong.**

<!-- answer:Q5 -->
I tested at three levels. First, 155 automated tests check the rules, safety checks and edge cases such as unknown codes and missing data. Second, an independent audit re-derived all 75 decisions from the raw workbook: 75 of 75 agreed, and the dashboard matched the output table. Third, I wrote 42 deliberately tricky reviewer notes (typos, Hindi and Tamil script, two problems in one note, disguised sanctions wording, prompt-injection attempts) and fixed the expected answers before running them. Results: 37 correct, 5 over-cautious (sent to review unnecessarily), 0 wrong codes, 0 sensitive cases missed. Testing also exposed real defects: a held case still showing WhatsApp, six messages adding lines like "nothing to worry about", and a keyword safety net catching only 2 of 8 sensitive notes. All were fixed and re-measured. These labels are mine, not Razorpay's answer key.
<!-- /answer -->

**6. Describe one real failure or edge case, what it could have cost, and how your design handles it.**

<!-- answer:Q6 -->
In stress testing, the note "Possible match on OFAC list" contained none of the words my keyword safety net was watching for, such as "sanction" or "screening". Only the AI recognised it as a compliance case. The same happened with "real-money betting", "adverse media" and "flagged by risk team": the second line of defence caught just 2 of 8 sensitive notes. Had the AI also missed one, the system could have drafted an ordinary "please re-upload your document" message for a sanctions match, which is a regulatory and reputational failure. The design already limited the damage, because every message needs human approval and compliance cases are routed manually. I then widened the keyword list. It now catches 8 of 8 on its own with no new false alarms, and any sensitive or uncertain case gets no message and no channel until a person confirms it.
<!-- /answer -->

**7. What are the risks (wrong answer, bias, compliance, privacy), and what controls did you add?**

<!-- answer:Q7 -->
Wrong answer: the AI can only choose a catalog code and must quote the note word for word. Uncertain diagnoses go to human review instead of being counted as recoverable, and coded rows are cross-checked against their note, with any conflict sent to review. Compliance: restricted categories close with no workaround; screening cases receive only a fixed, neutral "under review" text and never go to WhatsApp. Every message is checked for links, numbers, promises, timelines, compliance terms, extra content and wrong script, and nothing is sent automatically. Bias: decisions never use industry, city or business type, and the AI sees only the reviewer note. Prioritisation favours high-TPV merchants by design, which can push small businesses down the queue; that trade-off is visible and adjustable. Privacy: synthetic data only, minimal fields sent to the model, and the API key kept outside the repository.
<!-- /answer -->

**8. If you had 3 months and a small team, what would you build next, and how would you know it worked?**

<!-- answer:Q8 -->
Month 1: connect to the onboarding system so stalls are detected from event logs rather than a spreadsheet, and have native speakers review a sample of messages in every language. Month 2: pilot with one operations pod, sending approved messages through Razorpay's approved channels and testing the three-touch follow-up sequence with stopping rules that I have designed but not yet built. Month 3: ship the highest-value product fix, PAN-first entry with live name checks, behind an A/B test. I would know it worked from the share of nudged merchants who clear their blocked step within 14 days compared with a control group, the activation rate, specialist minutes per case, opt-out and complaint rates, and fewer name-mismatch rejections. Only once real recovery outcomes exist would I replace the priority heuristic with a model trained on them.
<!-- /answer -->

### Problem 3: Onboarding recovery

**P3-a. How do you tell a fixable rejection from a genuine compliance failure?**

<!-- answer:P3a -->
I do not let the model decide this. The rejection catalog is the authority: R01–R09, R11 and R13 are fixable, R10 (restricted category) is not, and R12 (screening hit) needs compliance review. When a code exists, a rule applies it directly. When only free text exists, the AI may suggest a catalog code with a verbatim quote, while a keyword check runs alongside it; any hint of restriction, sanctions, risk flags or fraud marks the case as sensitive. Sensitive or uncertain cases get no merchant message until a person confirms them. In the data, 67 cases are fixable and recoverable, 5 are closed as restricted (including A3051, read from free text and held for review), and 3 go to Compliance with a neutral "under review" message that never mentions screening.
<!-- /answer -->

**P3-b. How does your nudge change by language, channel and timing?**

<!-- answer:P3b -->
Language: each message is written in the merchant's preferred language and script. That means English, Hinglish in Roman letters, Hindi and Marathi in Devanagari, and Tamil and Kannada in their own scripts; terms such as PAN, GSTIN and IFSC stay in English, as they appear on documents. A script check rejects any draft in the wrong script, and each draft carries an English back-translation for the reviewer. Channel: WhatsApp only with explicit opt-in (53 cases); otherwise manual follow-up (21), because the data contains no email addresses and I do not invent contact details. Compliance cases are always manual. Timing: priority order decides who is contacted first. Timed reminders and stopping rules are a designed proposal, not yet built, and they never apply to closures or compliance cases.
<!-- /answer -->

**P3-c. Which single fix would you ask the product team to ship first?**

<!-- answer:P3c -->
PAN-first onboarding with live name checks. Merchants would enter their PAN, and GSTIN if registered, at the start. The legal name and address would be pre-filled from it, and the bank account holder's name would be checked against it before submission, with any mismatch explained on screen. The evidence: name mismatches across PAN, GST and bank account (R01, R02, R03) are the largest group of fixable rejections, 22 applications and Rs 238.5 lakh of expected monthly TPV. And the largest group of abandoned applications, 10, stops at the very first "Business details" screen, where pre-filling reduces typing. Together that is 32 of 75 non-activated applications. Without outcome data I cannot estimate how many would activate, so I would launch it as an A/B test tracking step completion and name-mismatch rejections.
<!-- /answer -->

---

## Part C: Minimum expectations, case by case

Coverage across the 75 non-activated applications, computed from `outputs/p3_results.csv`:

| Element | Coverage | Detail |
|---|---|---|
| 1. Diagnosed cause | **75/75** | 49 reviewer code · 22 abandonment (R13) · 4 AI-read free text |
| 2. Supporting evidence | **75/75** | Reviewer text, a rule explanation ("Stalled, no code or note; last step 'KYC docs'; 19 days"), or a verbatim AI quote |
| 3. Fixable? | **75/75** | Yes 67 · No 5 · Needs compliance review 3 |
| 4. Recoverable? | **75/75** | RECOVERABLE 67 · NOT_RECOVERABLE_CLOSE 5 · COMPLIANCE_REVIEW 3 · NEEDS_HUMAN_REVIEW 0 |
| 5. Next action | **75/75** | Corrective nudge 45 · Reminder 22 · Close politely 5 · Route to Compliance 3 |
| 6. Nudge in preferred language | **74/75** | 71 drafted + 3 neutral compliance texts. Languages: English 21, Hinglish 17, Hindi 14, Tamil 13, Kannada 5, Marathi 4. All 74 in the matching language and script; 0 safety-check failures. A3051 has none by design. |
| 7. Channel | **75/75** | WhatsApp 53 (all opted in) · Manual follow-up 21 · Not applicable 1. WhatsApp without opt-in: 0 |
| 8. Human escalation | **4 cases + all drafts** | A3051 flagged for human confirmation; 3 R12 cases owned by Compliance; every one of the 74 drafts needs approval before sending |

**How blank rejection codes are handled (26 of the 75 have no code):**
- **22 have no code and no reviewer note,** and all 22 are *Stalled*. They become R13 abandonment, and the reminder names the exact step reached. A blank code is **not** assumed to mean abandonment on its own: a *Rejected* application with no code and no note goes to human review (tested; none in this data).
- **4 have no code but a reviewer note.** The AI matches each note to the catalog and must quote it:

| App | Reviewer note | Decision |
|---|---|---|
| A3022 | "Doc blurred and cropped, cannot verify" | R05, recoverable |
| A3028 | "PAN ka naam aur application ka naam match nahi kar raha" | R01, recoverable |
| A3081 | "Signatory ka ID proof upload nahi hua" | R09, recoverable |
| A3051 | "Business category not supported by policy" | R10, close, **held for human confirmation, no message, no channel** |

- **Safeguards on these:**
  - Without an API key these 4 stay in human review instead of being guessed.
  - If the AI is unsure, the case goes to review and isn't counted as recoverable.
  - On rows that do have a code, the AI also reads the note: it agreed on 47 of 49, returned "unknown" on 2, and found 0 contradictions.

---

## Part D / Deliverable 4: Stretch ideas

### D1. Prioritisation by business value and inactivity: **implemented**

**Method:**
- Only recoverable cases are ranked. Closures, compliance cases and cases awaiting review are excluded.
- **Score = 0.7 × TPV percentile + 0.3 × (100 − days inactive).** The TPV percentile is 0 to 100 among recoverable cases.
- The top 25% are HIGH, the middle 50% MEDIUM and the bottom 25% LOW.

| Tier | Cases | Expected TPV (Rs L) | Share of TPV at stake |
|---|---|---|---|
| HIGH | 17 | 571.0 | 61% |
| MEDIUM | 33 | 319.0 | 34% |
| LOW | 17 | 43.9 | 5% |

**Top 10:** A3031 (R02), A3081 (R09), A3033 (R06), A3018 (R06), A3022 (R05), A3088 (R03), A3023 (R09), A3054 (R13), A3068 (R04), A3008 (R13).

**Assumptions and honesty notes:**
- **The weights are my choice, not a fitted model.** Inactivity only spans 0–40 days, so in this data TPV drives about 86% of the order. I decided to keep it that way on purpose: business value leads, and recency separates merchants with similar TPV.
- **The order is stable under different weights.** TPV-only keeps 9 of the top 10, and so do weightings from 0.9/0.1 down to 0.6/0.4; 50/50 keeps 8; recency-only keeps 3.
- **21 rows have an inactivity value longer than the account's age.** These are flagged; for them, recency is unreliable.
- **The score is a prioritisation heuristic, not a probability of conversion.**

**Business value:** a team that works only the 17 HIGH cases (a quarter of the queue) first is addressing 61% of the expected TPV at stake.

### D2. Product and process improvements: **analysis implemented; changes proposed**

**The three most common avoidable (fixable) causes, from the data:**

| Rank | Cause | Applications | Expected TPV (Rs L) | Where it happens |
|---|---|---|---|---|
| 1 | R13 Abandoned, no rejection | 22 | 307.6 | Business details 10, KYC docs 6, Bank verification 6 |
| 2 | R01 PAN name ≠ business name | 9 | 54.9 | KYC docs |
| 3 | R06 Website policy pages missing (R03 bank-name mismatch is tied at 7) | 7 | 128.1 | Website/App review |

Grouped together, **name mismatches** (R01 PAN, R02 GST, R03 bank) account for **22 applications and Rs 238.5 L**. Across all causes, KYC docs is the biggest stall point: **32 applications, Rs 504.4 L**.

**Proposed changes, none of them built:**
1. **PAN-first entry with live name checks.** Pre-fill the legal name and address from the PAN or GSTIN, and check the bank account holder's name before submission. This targets the 22 name-mismatch cases and the 10 abandonments at the first screen. *Assumption:* the data sources for pre-filling are not verified.
2. **Pre-submission website checker.** Confirm that the four mandatory policy pages exist and the site is publicly reachable before review (R06 + R07: 10 applications, Rs 143.2 L).
3. **Clearer reviewer instructions.** Replace terse notes like "GSTIN inactive / legal name mismatch" with the catalog's plain-language meaning and fix. The copilot already does this for its messages; the proposal is to show the same text inside the onboarding screen.
4. **A save-and-resume reminder** for applications idle at a step. This is the in-product version of the R13 nudge.

**How this prevents repeat rejections:**
- Validation moves mistakes from *after* submission, as a rejection days later, to *during* entry, where they can be fixed immediately.
- Clearer instructions reduce resubmissions that fail the same check. The 16 recoverable merchants with 3 or more attempts suggest repeated failures already happen.
- No uplift figure is claimed. Each change should be A/B-tested on step completion and rejection rate.

### D3. Follow-up sequence and stopping rules: **proposed, not built**

The tool drafts messages but has **no messaging integration**. It does not send, schedule or track anything. The sequence below is a design for a future pilot.

**Before any message:**
- A person approves every message.
- Language and channel stay as recommended: WhatsApp only with explicit opt-in, otherwise manual follow-up.
- Timings are internal checkpoints and are never promised to the merchant.

| Touch | When | What |
|---|---|---|
| 1 | Day 0, in priority order (HIGH → MEDIUM → LOW) | The approved drafted message |
| 2 | If no progress after the catalog's typical fix time + 2 days (day 3 for R13, up to day 5 for website fixes) | A short reminder naming the same step and the same fix |
| 3 | About 7 days after touch 2 | HIGH tier: a call by a specialist (needs a phone number from the CRM; none in this data). Others: a final written reminder |
| — | No progress after touch 3 | Mark dormant; no more outreach this cycle |

**Stop immediately when:**
- the merchant activates, moves past the blocked step or resubmits;
- the merchant asks to stop, opts out of WhatsApp (switch to manual) or complains;
- the case is reclassified as R10, R12 or needing human review, or a new rejection code appears (re-diagnose first);
- the merchant contacts support (hand over to that person);
- three touches have been sent.

**Never sequenced:**
- R10 closures get one message only.
- R12 compliance cases: Compliance owns all contact.
- Withheld cases, such as A3051, get nothing until a person confirms.

**Guardrails:** at most one message every 2 days, and business hours only.

**Business value:** it caps contact frequency (protecting merchant experience and opt-out rates) and focuses specialist calls on HIGH-value cases.

---

## Part E / Deliverable 3: Business results

| Metric | Value | How calculated |
|---|---|---|
| Total applications | 100 | Rows in P3_Applications |
| Activated | 25 | `application_status` |
| Stalled | 67 | `application_status` |
| Rejected | 8 | `application_status` |
| Non-activated | 75 | Stalled + Rejected |
| Recoverable | 67 | Catalog fixable = Yes |
| Not recoverable (close) | 5 | R10 (4 coded + A3051) |
| Compliance review | 3 | R12 |
| Unresolved human review | 0 | `recoverability` = NEEDS_HUMAN_REVIEW |
| Flagged for human confirmation | 1 | A3051 (plus 3 compliance cases owned by people) |
| Expected monthly TPV, all non-activated | Rs 1,038.4 L | Sum over 75 |
| **Expected monthly TPV at stake (recoverable)** | **Rs 933.9 L** | 1,038.4 − 46.9 (R10) − 57.6 (R12) |
| High-priority recoverable applications | 17 (Rs 571.0 L, 61%) | Top quartile of priority score |

| Rank | Top causes by count | Top causes by expected TPV |
|---|---|---|
| 1 | R13 Abandoned: 22 | R13 Abandoned: Rs 307.6 L |
| 2 | R01 PAN name mismatch: 9 | R06 Policy pages missing: Rs 128.1 L |
| 3 | R06 Policy pages missing: 7 (tied with R03; higher TPV) | R09 Signatory incomplete: Rs 112.1 L |

**Expected business impact (qualitative; no uplift is claimed):**
- **Operational efficiency:** specialists receive a diagnosis, decision, priority and draft message instead of raw notes. 71 of 75 cases need no AI at all, and the system works without an API key.
- **Merchant experience:** plain-language instructions in six languages, one clear next step, no promises, and WhatsApp only with consent.
- **Onboarding conversion:** effort is focused where expected value is concentrated (61% of TPV at stake in 17 cases), and the product team gets evidence for fixes that prevent the causes.

**Not available:** recovered TPV, activation uplift and revenue impact. The data has no outcomes, and Problem 3 provides no take-rate or cost assumptions, so these must come from a pilot.

---

## Part F / Deliverable 5: Risk, limitations and human oversight

- **Why rules for known codes:** the catalog is the source of truth. Rules are predictable, auditable and free, and they make 71 of 75 decisions. A model adds risk without adding information when a code already exists.
- **Why the LLM only for ambiguous text and communication:** these are the only tasks rules cannot do well, namely reading free-text notes in English or Hinglish and writing natural messages in six languages.
- **How unsupported classifications are prevented:**
  - The model must return a catalog code or "unknown".
  - It must quote the note word for word, and a quote not found in the record is rejected.
  - One retry is allowed, then human review.
  - If the model is unsure, the case is not counted as recoverable.
  - Industry, city and TPV are never sent to the model.
- **How compliance cases are escalated:**
  - R12 goes to Compliance with only the catalog's fixed neutral text, on a manual channel.
  - Free text that hints at screening or restriction is held with no message. The keyword backstop alone catches 8 of 8 sensitive stress notes; the AI caught them too.
- **How human review protects:** nothing is ever sent by the tool. Every draft, closure and compliance route needs a person. Uncertain or sensitive cases show no channel, so they can't be sent by mistake.
- **How messages are checked:**
  - **Automatic checks:** links, emails, phone numbers, internal codes, numbers not in the brief, promises and timelines, compliance terms, workarounds, content beyond the brief, missing step names, wrong script and length. A draft that fails is retried once, then held.
  - **Live results:** 0 failures across 74 drafts. Extra-content lines went from 6 to 0 after a prompt fix.
- **Failure cases found and fixed:**
  - a held case showing WhatsApp;
  - uncertain AI diagnoses counted as recoverable;
  - the keyword backstop missing euphemisms (2 of 8 caught);
  - six messages with reassurance or marketing lines;
  - inactivity longer than account age in 21 rows (now flagged, not altered).
- **What the solution cannot establish:**
  - accuracy against Razorpay's hidden labels;
  - whether nudges actually lead to activation;
  - recovered TPV or revenue;
  - true translation quality without native speakers;
  - whether the 0.7/0.3 weights are optimal.

  The stress-test labels and the independent re-derivation are mine. They show internal consistency, not ground truth.

---

## Part G: Future roadmap

| Phase | Focus | Practical steps | Success measure |
|---|---|---|---|
| 1 | Diagnosis and reliability | Native-speaker review of message samples; human-labelled set of 100+ real reviewer notes; repeat-run consistency checks; minimum-inactivity rule for reminders | Agreement with specialists' labels; 0 compliance leaks; reviewer edits per draft |
| 2 | Integration | Read stalls from onboarding event logs; send *approved* messages through Razorpay's existing channels; log every touch; build the D3 sequence | Time from stall to first contact; specialist minutes per case |
| 3 | Measure outcomes and refine prioritisation | Pilot against a control group; record step completion and activation; add engagement signals (attempts, support contacts) | Step completion within 14 days vs control; activation rate; opt-outs |
| 4 | Predictive recovery | Only with enough validated outcomes: train a simple, explainable model of recovery likelihood and compare it with the heuristic | Better ranking than the heuristic on held-out outcomes |

---

## Deliverable 6: Final consistency check

The check script is `verify_submission.py`, kept outside the repository and re-runnable. It found:

| Check | Result |
|---|---|
| All numbers match the executed output | **Pass.** Every figure above recomputed from the current pipeline (0 API calls). |
| Written answers match the code | **Pass.** Each feature described was checked in code. Follow-up timing (D3) and the product changes (D2) are labelled as proposed. |
| Dashboard and output table reconcile | **Pass.** App tiles 75 / 67 / 5 / 3 / 1 / 933.9 = output table (Streamlit AppTest, no exceptions). |
| No unsupported accuracy or conversion claims | **Pass.** Agreement and stress results are described as internal; no uplift, revenue or recovered TPV is claimed. |
| All official requirements addressed | **Pass,** with three items still open: a native-speaker review, a shareable link to the working solution, and the video. |
| Word limits (100–150) | **Pass.** See the counts below. |
| No proposed feature presented as complete | **Pass.** S2 and S3 are marked "Proposed"; the messaging integration is stated as not built. |

<!-- wordcounts -->
| Answer | Words | Within 100–150 |
|---|---|---|
| Q1 | 137 | Yes |
| Q2 | 135 | Yes |
| Q3 | 138 | Yes |
| Q4 | 138 | Yes |
| Q5 | 139 | Yes |
| Q6 | 145 | Yes |
| Q7 | 142 | Yes |
| Q8 | 135 | Yes |
| P3a | 130 | Yes |
| P3b | 127 | Yes |
| P3c | 130 | Yes |

---

## Missing information that prevents a fully evidence-based answer

1. **Hidden answer key:** needed to state diagnosis accuracy (brief measure E1).
2. **Recovery outcomes:** needed for conversion uplift, recovered TPV and validated priority weights.
3. **Native-speaker review** of the Tamil, Kannada and Marathi drafts: needed to evidence language quality (measure E3).
4. **Your own human labels** on the 30-case sheet: needed to report human-checked results in Answer 5.
5. **Contact data and messaging integration** (email, phone, WhatsApp API): needed to build and test the follow-up sequence.
6. **Whether data sources exist** to pre-fill names from PAN or GSTIN: needed to cost the proposed product fix.
7. **Cost assumptions** (specialist time, take rate): Problem 3 provides none, so no rupee impact can be computed.
8. **Snapshot date:** taken from the README sheet (30 Sep 2026); 21 rows conflict with it.

## Personalise before submitting

- Re-read every answer and reword it in your own voice. Check that you can explain each claim.
- Answer 4: confirm the list of decisions you made, and add any I don't know about (for example, who drafted the technical handover).
- Answer 5: once you've filled in the 30-case sheet, add one line with your agreement figure and one case you disagreed with.
- Record a short screen capture, or provide the repository link, as the "working solution".

---

## Appendix: 5-minute pitch outline (Section 5B)

| Segment (brief) | Time | What to show and say |
|---|---|---|
| 1. Problem and user | 0:30 | 75 of 100 applications not activated; Rs 1,038 L declared expected monthly TPV stuck; the specialist reads terse notes, and the merchant doesn't understand them |
| 2. Your approach | 1:00 | Rules decide (71/75); AI reads 4 free-text notes and writes 74 messages in 6 languages; humans approve everything; WhatsApp only with consent |
| 3. Live demo | 1:30 | Dashboard Overview → Work queue: A3001 (coded R02, Marathi, WhatsApp) → A3022 (AI reads "Doc blurred", quote shown) → A3051 (restricted, held, no channel) → A3094 (compliance, neutral Tamil, manual) → Nudge review tab |
| 4. Results and failures | 1:30 | 67 recoverable, Rs 933.9 L at stake, 17 HIGH = 61%; top causes; stress test 37/5/0/0; failures found and fixed (keyword net 2/8 → 8/8, extra content 6 → 0, A3051 channel) |
| 5. Next steps | 0:30 | Native-speaker review, pilot vs control, PAN-first fix, then outcome-based prioritisation |
