"""Illustrated merchant avatars, generated deterministically from the application ID.

These are cartoon characters, not photos of real people: the merchants in the data pack are synthetic.
The same application always gets the same character.
"""
import hashlib

SKIN = ["#F6CFA8", "#E3AE82", "#C98E5F", "#9A623E", "#7A4A2C"]
HAIR = ["#1E1E24", "#3B2418", "#5A3420", "#2B2B44", "#6B6B6B"]
BACKGROUND = ["#FFE3D3", "#DDE9FF", "#DDF7EA", "#FFF1BF", "#EDE3FF", "#FFDFEA", "#D9F3FF"]
SHIRT = ["#2F6BFF", "#12B886", "#F76707", "#7950F2", "#E64980", "#0CA678", "#F59F00", "#1C7ED6"]

INDUSTRY_BADGE = {
    "Apparel & Fashion": "👗", "Beauty & Wellness": "💄", "Books & Stationery": "📚",
    "Education / Coaching": "🎓", "Electronics": "🔌", "Fitness & Sports": "🏋️",
    "Gifting & Festive": "🎁", "Grocery & Food": "🛒", "Health & Pharmacy": "💊",
    "Home & Furniture": "🛋️", "SaaS / Digital Services": "💻", "Travel & Hospitality": "✈️",
}
LANGUAGE_BADGE = {
    "English": ("A", "English"), "Hinglish": ("Hi", "Hinglish"), "Hindi": ("हि", "Hindi"),
    "Marathi": ("म", "Marathi"), "Tamil": ("த", "Tamil"), "Kannada": ("ಕ", "Kannada"),
}


def _pick(seed: bytes, i: int, options: list):
    return options[seed[i] % len(options)]


def avatar_svg(key: str, size: int = 64) -> str:
    s = hashlib.md5(str(key).encode("utf-8")).digest()
    bg, skin, hair, shirt = _pick(s, 0, BACKGROUND), _pick(s, 1, SKIN), _pick(s, 2, HAIR), _pick(s, 3, SHIRT)
    style = s[4] % 5
    hair_svg = {
        0: f'<path d="M20 26 Q32 10 44 26 Q42 17 32 16 Q22 17 20 26 Z" fill="{hair}"/>',  # short
        1: f'<path d="M19 28 Q19 12 32 12 Q45 12 45 28 L46 44 Q42 40 42 30 Q32 20 22 30 Q22 40 18 44 Z" fill="{hair}"/>',  # long
        2: f'<circle cx="32" cy="11" r="6" fill="{hair}"/><path d="M20 26 Q32 12 44 26 Q42 16 32 15 Q22 16 20 26 Z" fill="{hair}"/>',  # bun
        3: f'<path d="M19 24 Q32 8 45 24 Z" fill="{shirt}"/><rect x="17" y="22" width="30" height="4" rx="2" fill="{shirt}"/>',  # cap
        4: f'<path d="M20 27 Q20 14 32 14 Q44 14 44 27 Q40 20 32 20 Q24 20 20 27 Z" fill="{hair}"/>',  # side part
    }[style]
    glasses = s[5] % 4 == 0
    glasses_svg = ('<circle cx="27.5" cy="29" r="3.6" fill="none" stroke="#1E1E24" stroke-width="1.3"/>'
                   '<circle cx="36.5" cy="29" r="3.6" fill="none" stroke="#1E1E24" stroke-width="1.3"/>'
                   '<line x1="31.1" y1="29" x2="32.9" y2="29" stroke="#1E1E24" stroke-width="1.3"/>') if glasses else ""
    return (f'<svg viewBox="0 0 64 64" width="{size}" height="{size}" role="img" aria-label="Illustrated merchant avatar">'
            f'<circle cx="32" cy="32" r="32" fill="{bg}"/>'
            f'<path d="M12 64 Q12 44 32 44 Q52 44 52 64 Z" fill="{shirt}"/>'
            f'<rect x="28" y="38" width="8" height="8" rx="3" fill="{skin}"/>'
            f'<circle cx="32" cy="29" r="12" fill="{skin}"/>'
            f'{hair_svg}'
            f'<circle cx="27.5" cy="29" r="1.5" fill="#1E1E24"/><circle cx="36.5" cy="29" r="1.5" fill="#1E1E24"/>'
            f'{glasses_svg}'
            f'<path d="M28 34.5 Q32 37.5 36 34.5" stroke="#7A3E26" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
            f'</svg>')


def avatar_with_badge(key: str, industry: str | None, size: int = 64) -> str:
    badge = INDUSTRY_BADGE.get(industry or "", "🏪")
    b = max(18, size // 3)
    return (f'<div style="position:relative;width:{size}px;height:{size}px;flex:0 0 {size}px;">{avatar_svg(key, size)}'
            f'<div title="{industry or "Business"}" style="position:absolute;right:-4px;bottom:-4px;width:{b + 6}px;height:{b + 6}px;'
            f'border-radius:50%;background:#FFFFFF;border:2px solid #E3E8F2;display:flex;align-items:center;'
            f'justify-content:center;font-size:{b - 4}px;">{badge}</div></div>')


def language_chip(language: str | None) -> str:
    glyph, name = LANGUAGE_BADGE.get(language or "", ("?", language or "Unknown"))
    return (f'<span class="rp-chip" style="background:#E8F0FF;color:#1F4FBF;"><b style="margin-right:6px">{glyph}</b>'
            f'{name}</span>')
