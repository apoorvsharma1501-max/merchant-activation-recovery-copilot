# Pitch video script (maximum 5 minutes)

Spoken lines are in plain text. *[Screen: …]* lines are what to show, not what to say. Figures match `docs/submission_pack.md` and the app's saved results.

**Before recording:** start the app (`.venv\Scripts\streamlit run app.py`), keep AI mode on "Saved AI answers", and leave the Overview tab open.

---

## 1. Problem and user (0:00 to 0:30)

*[Screen: Overview tab, top tiles visible]*

<!-- say:1 -->
Every merchant who signs up but never goes live is payment volume Razorpay never processes. In this data pack, 75 of 100 applications are stuck, declaring 1,038 lakh rupees of expected monthly payments. Two people carry the cost. The onboarding specialist decides each case by hand from short, technical reviewer notes. The merchant receives a rejection they often cannot understand, sometimes not in their own language.
<!-- /say -->

## 2. Your approach (0:30 to 1:30)

*[Screen: stay on Overview]*

<!-- say:2 -->
I built a recovery copilot for the onboarding specialist. For every stuck application it finds the cause, decides whether the case can be recovered, drafts the merchant message, and ranks who to contact first.

Rules make every decision that carries risk. Where a reason code exists, the system applies the rejection catalog. With no code and no note, it treats the case as abandoned and prepares a reminder. That covers 71 of 75 cases.

AI does only what rules cannot. It reads the 4 reviewer notes written without a code, quoting the exact words it relied on, and it writes every message in the merchant's preferred language, across six languages.

People stay in control. A person approves every message. Restricted businesses are closed without any workaround, screening cases go to Compliance, and WhatsApp is used only with the merchant's consent.
<!-- /say -->

## 3. Live demo (1:30 to 3:00)

*[Screen: Overview tiles]*

<!-- say:3 -->
This is the dashboard running on the real data. 67 applications are recoverable, and 933.9 lakh rupees a month is at stake.

[Screen: Work queue, search A3001, open it]
A3001 is stuck on a GST mismatch. The catalog fix becomes a message in Marathi, sent on WhatsApp because this merchant opted in.

[Screen: search A3022]
A3022 has no code, only a note: "Doc blurred and cropped". The AI identifies an unreadable document and shows the exact quote it used.

[Screen: search A3051]
A3051 says "Business category not supported by policy". That is a restricted category. The case is closed with no workaround, and no message or channel is assigned until a person confirms.

[Screen: search A3094]
A3094 is a screening case. The merchant receives only a neutral "under review" message in Tamil, through manual follow-up, even though they accept WhatsApp.

[Screen: Merchant nudge review tab, pick a Tamil or Kannada draft]
Each draft sits next to an English translation for the reviewer. There is no send button.
<!-- /say -->

## 4. Results and failures (3:00 to 4:30)

*[Screen: Overview, scroll to "Top three systemic causes", then Evaluation & audit tab]*

<!-- say:4 -->
Every one of the 75 applications has a cause, a decision, a next step and a channel, and 74 have a message ready in the right language. The 17 highest-priority cases hold 61 percent of the volume at stake, so the team knows where to start.

Two causes dominate. 22 merchants abandoned the process, the largest group on the very first screen. Another 22 were rejected for name mismatches across PAN, GST and bank account. Both are product problems, not follow-up problems.

I also tested 42 deliberately difficult notes: typos, Hindi and Tamil script, disguised sanctions wording and attempts to trick the AI. There were no wrong codes and no missed sensitive cases. Five went to human review unnecessarily, which is the safe direction.

Testing exposed real failures. My keyword safety net caught only 2 of 8 sensitive notes. Six messages added lines like "nothing to worry about". After the fixes, the safety net catches all 8 and no message adds extra content.

One limit: the data has no recovery outcomes, so I report volume at stake, not volume recovered.
<!-- /say -->

## 5. Next steps (4:30 to 5:00)

*[Screen: Overview]*

<!-- say:5 -->
With three months and a small team, I would do three things. Have native speakers review the messages and connect the tool to live onboarding data. Run a pilot with one operations team against a control group, measuring how many merchants clear their blocked step within 14 days. And ship one product fix: PAN-first onboarding with live name checks, which addresses 32 of the 75 stuck applications. Thank you.
<!-- /say -->

---

<!-- timing -->
## Timing check (spoken words at about 140 words per minute)

| Segment | Words | Approx. time | Budget |
|---|---|---|---|
| 1 | 66 | 28s | 30s |
| 2 | 140 | 60s | 60s |
| 3 | 140 | 60s | 90s |
| 4 | 180 | 77s | 90s |
| 5 | 69 | 30s | 30s |
| **Total** | **595** | **255s** | **300s** |

The demo segment leaves time for clicks and pauses. If you speak faster or slower, practise once with a timer.
