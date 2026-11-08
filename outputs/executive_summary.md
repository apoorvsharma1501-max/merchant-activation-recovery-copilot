# Executive summary - onboarding recovery

All figures computed from the workbook at runtime. *Expected monthly TPV* is what merchants declared at signup; it is not recovered TPV, revenue or a forecast.

| Metric | Value |
|---|---|
| total applications | 100 |
| activated | 25 |
| stalled | 67 |
| rejected | 8 |
| non activated processed | 75 |
| fixable per catalog | 67 |
| recoverable | 67 |
| not recoverable close | 5 |
| compliance review | 3 |
| needs human review | 0 |
| human review flagged | 1 |
| expected monthly tpv at stake lakh | 933.9 |
| applications by tier | {'HIGH': 17, 'LOW': 17, 'MEDIUM': 33} |
| TPV at stake by tier (lakh) | {'HIGH': 571.0, 'LOW': 43.9, 'MEDIUM': 319.0} |

## Top three causes by number of applications
1. R13 Abandoned application (22)
2. R01 PAN name does not match business name (9)
3. R06 Website missing mandatory policy pages (7)

## Top three causes by expected monthly TPV
1. R13 Abandoned application (307.6 lakh)
2. R06 Website missing mandatory policy pages (128.1 lakh)
3. R09 Signatory details incomplete (112.1 lakh)

## Top fixable rejection causes (excluding abandonment)
By count:
1. R01 PAN name does not match business name (9)
2. R06 Website missing mandatory policy pages (7)
3. R03 Bank account name mismatch (7)

By TPV:
1. R06 Website missing mandatory policy pages (128.1 lakh)
2. R09 Signatory details incomplete (112.1 lakh)
3. R02 GST certificate invalid or mismatched (106.3 lakh)

## Where merchants abandon without a rejection (R13)
| Step | Applications | Expected monthly TPV (lakh) |
|---|---|---|
| Business details | 10 | 141.0 |
| Bank verification | 6 | 81.6 |
| KYC docs | 6 | 85.0 |

## All causes
| Code | Cause | Fixable | Apps | Share % | Recoverable | TPV (lakh) | Via AI |
|---|---|---|---|---|---|---|---|
| R13 | Abandoned application | Yes | 22 | 29.3 | 22 | 307.6 | 0 |
| R01 | PAN name does not match business name | Yes | 9 | 12.0 | 9 | 54.9 | 1 |
| R06 | Website missing mandatory policy pages | Yes | 7 | 9.3 | 7 | 128.1 | 0 |
| R03 | Bank account name mismatch | Yes | 7 | 9.3 | 7 | 77.3 | 0 |
| R02 | GST certificate invalid or mismatched | Yes | 6 | 8.0 | 6 | 106.3 | 0 |
| R10 | Restricted business category | No | 5 | 6.7 | 0 | 46.9 | 1 |
| R05 | Document unreadable | Yes | 4 | 5.3 | 4 | 86.5 | 1 |
| R04 | Bank verification failed | Yes | 4 | 5.3 | 4 | 40.7 | 0 |
| R09 | Signatory details incomplete | Yes | 3 | 4.0 | 3 | 112.1 | 1 |
| R12 | Compliance / sanctions screening hit | Needs compliance review | 3 | 4.0 | 0 | 57.6 | 0 |
| R07 | Website not live | Yes | 3 | 4.0 | 3 | 15.1 | 0 |
| R11 | Declared category differs from website | Yes | 1 | 1.3 | 1 | 3.3 | 0 |
| R08 | Address proof missing or outdated | Yes | 1 | 1.3 | 1 | 2.0 | 0 |

## HIGH-priority follow-ups
Score = 0.7 x TPV percentile + 0.3 x (100 - days inactive). A prototype ordering heuristic, not a recovery probability.

| Rank | Application | Cause | TPV (lakh) | Days inactive | Score | Channel | Language |
|---|---|---|---|---|---|---|---|
| 1 | A3031 | R02 | 43.3 | 4 | 94.5 | Manual follow-up | Hinglish |
| 2 | A3081 | R09 | 50.9 | 13 | 94.0 | WhatsApp | Hindi |
| 3 | A3033 | R06 | 50.6 | 11 | 93.6 | WhatsApp | English |
| 4 | A3018 | R06 | 34.9 | 4 | 92.4 | Manual follow-up | English |
| 5 | A3022 | R05 | 51.0 | 28 | 90.5 | WhatsApp | English |
| 6 | A3088 | R03 | 38.3 | 14 | 90.5 | WhatsApp | Hindi |
| 7 | A3023 | R09 | 59.9 | 35 | 89.5 | WhatsApp | Kannada |
| 8 | A3054 | R13 | 27.7 | 9 | 87.8 | WhatsApp | Tamil |
| 9 | A3068 | R04 | 25.6 | 4 | 87.7 | Manual follow-up | English |
| 10 | A3008 | R13 | 29.8 | 21 | 86.3 | Manual follow-up | Hindi |
| 11 | A3005 | R13 | 29.3 | 19 | 85.8 | WhatsApp | English |
| 12 | A3050 | R13 | 25.6 | 13 | 85.0 | WhatsApp | Kannada |
| 13 | A3006 | R13 | 24.9 | 16 | 82.5 | WhatsApp | Tamil |
| 14 | A3049 | R02 | 22.9 | 20 | 79.2 | WhatsApp | Hinglish |
| 15 | A3029 | R13 | 21.9 | 20 | 78.1 | Manual follow-up | Marathi |
| 16 | A3092 | R02 | 18.6 | 13 | 78.0 | WhatsApp | Tamil |
| 17 | A3091 | R03 | 15.8 | 6 | 78.0 | WhatsApp | English |

## Weight sensitivity (top 10)
| Variant | Top-10 overlap with base | Rank correlation | Top-10 expected TPV (lakh) |
|---|---|---|---|
| TPV only | 9 | 0.987 | 415.7 |
| 0.9 TPV / 0.1 recency | 9 | 0.99 | 415.7 |
| 0.8 / 0.2 | 9 | 0.996 | 415.7 |
| BASE 0.70 / 0.30 | 10 | 1.0 | 412.0 |
| 0.6 / 0.4 | 9 | 0.995 | 407.8 |
| 0.5 / 0.5 | 8 | 0.978 | 377.2 |
| Recency only | 3 | 0.177 | 128.3 |
