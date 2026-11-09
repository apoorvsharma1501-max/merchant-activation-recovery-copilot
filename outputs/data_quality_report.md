# P3 data-quality report

Source: `Buildathon_Student_Data_Pack.xlsx` (generated at runtime; nothing hard-coded).

## Overview
| Item | Value |
|---|---|
| Total applications | 100 |
| Non-activated (in scope) | 75 |
| Catalog codes | 13: R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13 |
| Blank rejection code (all rows) | 51 |
| Blank code, no reviewer text, non-activated | 22 |
| Expected monthly TPV range (Rs lakh) | 0.7 to 59.9 |
| TPV missing/invalid | 0 |
| Days since activity range | 0.0 to 40.0 |
| Days missing/invalid | 0 |
| Activated rows carrying a code or reviewer text | 0 |
| Rows where inactivity > days since signup (snapshot) | 21 |

## Status
| Status | Count |
|---|---|
| Stalled | 67 |
| Activated | 25 |
| Rejected | 8 |

## Blank code by status
| Status | Count |
|---|---|
| Activated | 25 |
| Stalled | 25 |
| Rejected | 1 |

## Blank code but reviewer text present (needs text classification)
| Application | Status | Reviewer text |
|---|---|---|
| A3022 | Stalled | Doc blurred and cropped, cannot verify |
| A3028 | Stalled | PAN ka naam aur application ka naam match nahi kar raha |
| A3051 | Rejected | Business category not supported by policy |
| A3081 | Stalled | Signatory ka ID proof upload nahi hua |

## Rejection codes among non-activated
| Code | Count |
|---|---|
| R01 | 8 |
| R02 | 6 |
| R03 | 7 |
| R04 | 4 |
| R05 | 3 |
| R06 | 7 |
| R07 | 3 |
| R08 | 1 |
| R09 | 2 |
| R10 | 4 |
| R11 | 1 |
| R12 | 3 |

## Step reached (non-activated)
| Step | Count |
|---|---|
| KYC docs | 32 |
| Bank verification | 17 |
| Website/App review | 16 |
| Business details | 10 |

## Preferred language
| Language | Count |
|---|---|
| English | 32 |
| Hinglish | 24 |
| Hindi | 19 |
| Tamil | 16 |
| Kannada | 5 |
| Marathi | 4 |

## WhatsApp opt-in
| Value | Count |
|---|---|
| Yes | 70 |
| No | 30 |

## Validation issues (21)
| Severity | Sheet | Row | Field | Message |
|---|---|---|---|---|
| WARNING | P3_Applications | A3001 | days_since_last_activity | inactivity (38 d) exceeds days since signup (37 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3006 | days_since_last_activity | inactivity (16 d) exceeds days since signup (7 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3008 | days_since_last_activity | inactivity (21 d) exceeds days since signup (8 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3016 | days_since_last_activity | inactivity (37 d) exceeds days since signup (8 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3026 | days_since_last_activity | inactivity (27 d) exceeds days since signup (13 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3030 | days_since_last_activity | inactivity (34 d) exceeds days since signup (15 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3034 | days_since_last_activity | inactivity (20 d) exceeds days since signup (14 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3044 | days_since_last_activity | inactivity (11 d) exceeds days since signup (5 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3047 | days_since_last_activity | inactivity (38 d) exceeds days since signup (16 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3049 | days_since_last_activity | inactivity (20 d) exceeds days since signup (6 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3050 | days_since_last_activity | inactivity (13 d) exceeds days since signup (12 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3076 | days_since_last_activity | inactivity (37 d) exceeds days since signup (32 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3080 | days_since_last_activity | inactivity (33 d) exceeds days since signup (17 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3081 | days_since_last_activity | inactivity (13 d) exceeds days since signup (7 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3082 | days_since_last_activity | inactivity (32 d) exceeds days since signup (30 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3083 | days_since_last_activity | inactivity (29 d) exceeds days since signup (8 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3087 | days_since_last_activity | inactivity (16 d) exceeds days since signup (8 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3089 | days_since_last_activity | inactivity (11 d) exceeds days since signup (8 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3095 | days_since_last_activity | inactivity (29 d) exceeds days since signup (7 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3097 | days_since_last_activity | inactivity (25 d) exceeds days since signup (10 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
| WARNING | P3_Applications | A3098 | days_since_last_activity | inactivity (26 d) exceeds days since signup (7 d) at snapshot 30 Sep 2026; recency-based priority is unreliable for this row |
