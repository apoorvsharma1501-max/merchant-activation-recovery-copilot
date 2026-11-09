"""Visual theme: colors, global CSS and the hero banner illustration."""

NAVY = "#0A1F44"
BLUE = "#2F6BFF"
SKY = "#E8F0FF"
INK2 = "#4A5878"
MUTED = "#8492AD"
LINE = "#E3E8F2"

STATUS = {  # recoverability -> (label, background, text)
    "RECOVERABLE": ("Recoverable", "#E3FAF0", "#0B7A53"),
    "NOT_RECOVERABLE_CLOSE": ("Close, no workaround", "#EEF0F4", "#3F4A5E"),
    "COMPLIANCE_REVIEW": ("Compliance review", "#F1ECFF", "#5B3CC4"),
    "NEEDS_HUMAN_REVIEW": ("Needs a person", "#FFF1E3", "#B3540E"),
}
TIER = {  # priority tier -> (label, background, text)
    "HIGH": ("High priority", "#FFE6E6", "#C02B2B"),
    "MEDIUM": ("Medium", "#FFF4CC", "#9A6A00"),
    "LOW": ("Low", "#E6F2FF", "#1F5FAD"),
    "UNRANKED_REVIEW": ("Not ranked", "#EEF0F4", "#3F4A5E"),
}

CSS = f"""
<style>
.block-container {{padding-top: 1.2rem; max-width: 1280px;}}
h1, h2, h3 {{color: {NAVY}; letter-spacing: -0.01em;}}
[data-testid="stSidebar"] {{background: #FFFFFF; border-right: 1px solid {LINE};}}
[data-testid="stMetric"] {{background: #FFFFFF; border: 1px solid {LINE}; border-radius: 16px; padding: 14px 16px;
  border-top: 4px solid {BLUE};}}
[data-testid="stMetricValue"] {{color: {NAVY}; font-weight: 700;}}
[data-testid="stMetricLabel"] p {{color: {INK2}; font-weight: 600;}}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] {{border-top-color: #12B886;}}
div[data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] {{border-top-color: #868E96;}}
div[data-testid="stHorizontalBlock"] > div:nth-child(4) [data-testid="stMetric"] {{border-top-color: #7048E8;}}
div[data-testid="stHorizontalBlock"] > div:nth-child(5) [data-testid="stMetric"] {{border-top-color: #F08C00;}}
div[data-testid="stHorizontalBlock"] > div:nth-child(6) [data-testid="stMetric"] {{border-top-color: #E8590C;}}
.stTabs [data-baseweb="tab-list"] {{gap: 6px; border-bottom: 1px solid {LINE};}}
.stTabs [data-baseweb="tab"] {{background: #FFFFFF; border: 1px solid {LINE}; border-bottom: none;
  border-radius: 12px 12px 0 0; padding: 10px 18px; font-weight: 600; color: {INK2};}}
.stTabs [aria-selected="true"] {{background: {BLUE}; color: #FFFFFF !important; border-color: {BLUE};}}
.stTabs [aria-selected="true"] p {{color: #FFFFFF !important;}}
.stButton button, .stDownloadButton button {{border-radius: 12px; font-weight: 600;}}
.rp-card {{background: #FFFFFF; border: 1px solid {LINE}; border-radius: 18px; padding: 18px 20px; margin-bottom: 14px;}}
.rp-chip {{display: inline-block; padding: 3px 12px; border-radius: 999px; font-size: 12.5px; font-weight: 600;
  margin: 0 6px 6px 0; white-space: nowrap;}}
.rp-muted {{color: {MUTED}; font-size: 13px;}}
.rp-k {{color: {MUTED}; font-size: 12px; text-transform: none; font-weight: 600; margin-bottom: 2px;}}
.rp-v {{color: {NAVY}; font-size: 14.5px; margin-bottom: 10px;}}
.rp-quote {{background: #F6F8FC; border-left: 4px solid {BLUE}; border-radius: 0; padding: 10px 14px;
  color: {NAVY}; font-size: 14px; margin: 6px 0 12px;}}
.rp-section {{font-size: 18px; font-weight: 700; color: {NAVY}; margin: 6px 0 10px;}}
</style>
"""

HERO_ART = """
<svg viewBox="0 0 340 190" width="100%" height="100%" role="img" aria-label="Illustration of a small shop owner receiving a helpful message on a phone">
  <ellipse cx="170" cy="178" rx="150" ry="9" fill="#ffffff" opacity="0.18"/>
  <rect x="28" y="70" width="170" height="104" rx="6" fill="#ffffff"/>
  <rect x="28" y="70" width="170" height="104" rx="6" fill="none" stroke="#C9D8FF" stroke-width="2"/>
  <g>
    <path d="M18 70 L38 40 H188 L208 70 Z" fill="#FF6B6B"/>
    <path d="M38 40 L52 40 L44 70 L18 70 Z" fill="#FFE066"/>
    <path d="M80 40 L94 40 L94 70 L70 70 Z" fill="#FFE066"/>
    <path d="M122 40 L136 40 L144 70 L120 70 Z" fill="#FFE066"/>
    <path d="M164 40 L178 40 L194 70 L170 70 Z" fill="#FFE066"/>
  </g>
  <rect x="44" y="92" width="58" height="82" rx="4" fill="#E8F0FF"/>
  <rect x="116" y="92" width="66" height="42" rx="4" fill="#E3FAF0"/>
  <circle cx="132" cy="113" r="7" fill="#12B886"/><circle cx="150" cy="113" r="7" fill="#FFA94D"/><circle cx="168" cy="113" r="7" fill="#7950F2"/>
  <rect x="62" y="120" width="22" height="18" rx="9" fill="#2F6BFF"/>
  <circle cx="73" cy="110" r="9" fill="#E0AC7E"/>
  <path d="M64 108 Q73 96 82 108 Q78 101 73 101 Q68 101 64 108 Z" fill="#2B2B2B"/>
  <path d="M69 113 Q73 116 77 113" stroke="#7A4B2A" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <rect x="226" y="34" width="86" height="146" rx="16" fill="#0A1F44"/>
  <rect x="232" y="46" width="74" height="122" rx="10" fill="#ECE5DD"/>
  <rect x="232" y="46" width="74" height="18" rx="10" fill="#128C7E"/>
  <rect x="238" y="74" width="56" height="30" rx="8" fill="#DCF8C6"/>
  <rect x="243" y="80" width="44" height="4" rx="2" fill="#7FB98A"/><rect x="243" y="88" width="36" height="4" rx="2" fill="#7FB98A"/><rect x="243" y="96" width="24" height="4" rx="2" fill="#7FB98A"/>
  <rect x="244" y="112" width="56" height="22" rx="8" fill="#FFFFFF"/>
  <rect x="249" y="118" width="40" height="4" rx="2" fill="#C5CCD8"/><rect x="249" y="125" width="28" height="4" rx="2" fill="#C5CCD8"/>
  <circle cx="294" cy="150" r="12" fill="#12B886"/>
  <path d="M288 150 L292 154 L300 145" stroke="#ffffff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="214" cy="28" r="10" fill="#FFD43B"/><text x="214" y="32" text-anchor="middle" font-size="12" font-weight="700" fill="#9A6A00">₹</text>
  <circle cx="320" cy="22" r="7" fill="#FFD43B"/><text x="320" y="25.5" text-anchor="middle" font-size="9" font-weight="700" fill="#9A6A00">₹</text>
</svg>
"""


def hero(non_activated: int, recoverable: int, tpv: float) -> str:
    return f"""
<div style="background: linear-gradient(120deg, {NAVY} 0%, #1B3F96 55%, {BLUE} 100%); border-radius: 22px;
  padding: 26px 30px; color: #FFFFFF; display: flex; gap: 24px; align-items: center; margin-bottom: 18px;">
  <div style="flex: 1.35; min-width: 0;">
    <div style="display:inline-block; background: rgba(255,255,255,0.16); border-radius: 999px; padding: 4px 12px;
      font-size: 12.5px; font-weight: 600; margin-bottom: 12px;">Built for the Razorpay Campus AI Build-a-thon · not an official Razorpay product</div>
    <div style="font-size: 34px; font-weight: 800; line-height: 1.15; margin-bottom: 8px;">Merchant Activation Recovery Copilot</div>
    <div style="font-size: 16px; opacity: 0.92; line-height: 1.55; max-width: 620px;">
      Find out why a merchant is stuck, decide what to do, and send a clear next step in their own language,
      with a person approving every message.</div>
    <div style="display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap;">
      <span style="background:#FFFFFF; color:{NAVY}; border-radius: 12px; padding: 8px 14px; font-weight: 700;">{non_activated} merchants stuck</span>
      <span style="background:#12B886; color:#FFFFFF; border-radius: 12px; padding: 8px 14px; font-weight: 700;">{recoverable} recoverable</span>
      <span style="background:#FFD43B; color:{NAVY}; border-radius: 12px; padding: 8px 14px; font-weight: 700;">₹{tpv:,.1f} lakh / month at stake</span>
    </div>
  </div>
  <div style="flex: 1; min-width: 0; max-width: 380px; height: 200px;">{HERO_ART}</div>
</div>
"""


def chip(label: str, bg: str, fg: str) -> str:
    return f'<span class="rp-chip" style="background:{bg};color:{fg};">{label}</span>'


def status_chip(recoverability: str) -> str:
    label, bg, fg = STATUS.get(recoverability, (recoverability, "#EEF0F4", "#3F4A5E"))
    return chip(label, bg, fg)


def tier_chip(tier: str | None) -> str:
    label, bg, fg = TIER.get(tier or "UNRANKED_REVIEW", TIER["UNRANKED_REVIEW"])
    return chip(label, bg, fg)
