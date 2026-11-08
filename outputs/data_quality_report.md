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

## Validation issues (0)
None found.
