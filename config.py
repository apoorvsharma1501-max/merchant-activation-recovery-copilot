"""Central configuration. Business policy lives in the workbook catalog, not here.

Only structural settings (sheet/column names, status values, channel labels) and
explicit prototype assumptions (marked ASSUMPTION) belong in this file.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_WORKBOOK = ROOT / "data" / "Buildathon_Student_Data_Pack.xlsx"
OUTPUT_DIR = ROOT / "outputs"

RULE_VERSION = "rules-v1"

# --- Workbook contract -------------------------------------------------------
APPLICATIONS_SHEET = "P3_Applications"
CATALOG_SHEET = "P3_RejectionCatalog"

APPLICATION_COLUMNS = [
    "application_id", "business_type", "industry", "city", "preferred_language",
    "signup_date", "expected_monthly_tpv_inr_lakh", "whatsapp_opted_in",
    "step_reached", "application_status", "days_since_last_activity", "attempts",
    "support_contacts", "rejection_code", "rejection_message",
]
APPLICATION_NUMERIC_COLUMNS = [
    "expected_monthly_tpv_inr_lakh", "days_since_last_activity", "attempts", "support_contacts",
]
CATALOG_COLUMNS = [
    "code", "reviewer_reason", "plain_language_meaning", "fixable",
    "standard_fix", "typical_days_to_fix",
]

# --- Status values observed in the supplied workbook ---------------------------
STATUS_ACTIVATED = "Activated"
STATUS_STALLED = "Stalled"
STATUS_REJECTED = "Rejected"
KNOWN_STATUSES = {STATUS_ACTIVATED, STATUS_STALLED, STATUS_REJECTED}

# The catalog row describing "no rejection, applicant just stopped".
# Verified at load time to exist in the catalog.
INACTIVITY_CODE = "R13"

# ASSUMPTION: cells holding only these tokens are treated as missing.
# (The brief's PDF renders blanks as an em dash; the workbook itself uses empty cells.)
MISSING_TOKENS = {"", "—", "–", "-", "nan", "none", "null", "n/a"}

# ASSUMPTION: only an explicit "Yes" (case-insensitive) permits WhatsApp.
WHATSAPP_AFFIRMATIVE = {"yes"}

# --- Languages and channels ----------------------------------------------------
SUPPORTED_LANGUAGES = ("English", "Hindi", "Hinglish", "Tamil", "Kannada", "Marathi")

CHANNEL_WHATSAPP = "WhatsApp"
# No email/phone exists in the data, so we do not claim an email can be sent.
CHANNEL_MANUAL = "Manual follow-up"
CHANNEL_NOT_APPLICABLE = "Not applicable"

# --- Safety screen for blank-code reviewer text -------------------------------
# ASSUMPTION: deterministic keyword guard. Any match on blank-code reviewer text
# suppresses merchant-facing diagnosis and forces human/compliance review,
# regardless of what an LLM later says.
SENSITIVE_TEXT_PATTERNS = [
    r"restrict", r"prohibit", r"not supported", r"support nahi", r"sanction",
    r"screening", r"compliance", r"fraud", r"\baml\b", r"blacklist",
    r"negative list", r"gambl",
]

# --- LLM (Phase 3) ---------------------------------------------------------------
PROMPTS_DIR = ROOT / "prompts"
# Committed so anyone can reproduce the exact AI outputs without an API key.
LLM_CACHE_FILE = ROOT / "cache" / "llm_cache.json"

LLM_PROVIDER = "anthropic"
LLM_MODEL = "claude-opus-5-5"
# Thinking is always on for this model; effort controls depth and cost.
LLM_EFFORT_DIAGNOSIS = "medium"   # few calls, judgement matters
LLM_EFFORT_NUDGE = "low"          # many short localisation calls
LLM_MAX_TOKENS = 8000             # includes thinking tokens
# Server-side refusal fallback (Anthropic beta). Set False if your account rejects it.
LLM_USE_REFUSAL_FALLBACK = True

DIAGNOSIS_PROMPT_VERSION = "diag-v1"
NUDGE_PROMPT_VERSION = "nudge-v1"

NUDGE_MAX_CHARS = 900

# Unicode script each language must be written in (sanity check, not a quality check).
LANGUAGE_SCRIPTS = {
    "English": "latin", "Hinglish": "latin",
    "Hindi": "devanagari", "Marathi": "devanagari",
    "Tamil": "tamil", "Kannada": "kannada",
}

# --- Prioritisation (Phase 4) --------------------------------------------------
# ASSUMPTION: prototype heuristic, not a validated model or Razorpay policy.
PRIORITY_WEIGHT_TPV = 0.70
PRIORITY_WEIGHT_RECENCY = 0.30
