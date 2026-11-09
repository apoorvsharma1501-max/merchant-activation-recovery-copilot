"""HTML building blocks for the app. All merchant-facing text is escaped before it is rendered."""
from html import escape

import pandas as pd

from ui.avatars import avatar_with_badge, language_chip
from ui.theme import BLUE, INK2, LINE, MUTED, NAVY, chip, status_chip, tier_chip

STEPS = ["Business details", "KYC docs", "Bank verification", "Website/App review", "Activated"]
STEP_LABEL = {"Business details": "Business details", "KYC docs": "KYC documents",
              "Bank verification": "Bank verification", "Website/App review": "Website review",
              "Activated": "Live"}
STEP_EMOJI = {"Business details": "📝", "KYC docs": "🪪", "Bank verification": "🏦",
              "Website/App review": "🌐", "Activated": "🚀"}
CAUSE_EMOJI = {"R01": "🪪", "R02": "🧾", "R03": "🏦", "R04": "🏦", "R05": "📄", "R06": "🌐", "R07": "🌐",
               "R08": "🏠", "R09": "✍️", "R10": "⛔", "R11": "🏷️", "R12": "🛡️", "R13": "⏸️"}
STEP_COLORS = ["#7950F2", "#F76707", "#1C7ED6", "#E64980", "#12B886"]


def _n(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else v


def journey(counts: dict[str, int], tpv: dict[str, float]) -> str:
    """Horizontal onboarding journey: how many merchants are stuck at each step, and how many are live."""
    top = max(counts.values()) if counts else 1
    cells = []
    for i, step in enumerate(STEPS):
        n = counts.get(step, 0)
        h = 34 + int(96 * n / top)
        color = STEP_COLORS[i]
        sub = "live" if step == "Activated" else f"stuck · ₹{tpv.get(step, 0):,.0f} L"
        arrow = "" if i == len(STEPS) - 1 else (
            f'<div style="position:absolute;right:-13px;top:50%;transform:translateY(-50%);font-size:20px;color:{MUTED};">›</div>')
        cells.append(f"""
<div style="flex:1;min-width:0;position:relative;text-align:center;">
  <div style="font-size:24px;margin-bottom:4px;">{STEP_EMOJI[step]}</div>
  <div style="height:130px;display:flex;align-items:flex-end;justify-content:center;">
    <div style="width:68%;height:{h}px;background:{color};border-radius:14px 14px 4px 4px;display:flex;align-items:flex-start;
      justify-content:center;padding-top:8px;color:#FFFFFF;font-weight:800;font-size:22px;">{n}</div></div>
  <div style="font-weight:700;color:{NAVY};font-size:14px;margin-top:8px;">{STEP_LABEL[step]}</div>
  <div class="rp-muted">{sub}</div>{arrow}
</div>""")
    return f'<div class="rp-card"><div style="display:flex;gap:14px;">{"".join(cells)}</div></div>'


FUNNEL_STAGE_LABEL = ["Signed up", "Business details done", "KYC documents done", "Bank verified", "Live"]
FUNNEL_COLORS = ["#2F6BFF", "#4C6EF5", "#7950F2", "#AE3EC9", "#12B886"]


def funnel_stages(total: int, stuck_at: dict[str, int]) -> tuple[list[tuple[str, int, int]], list[tuple[str, int]]]:
    """Funnel from 'last step reached', assuming the steps run in order.

    Returns (step, merchants who reached it, merchants still pending there) for each step, with the
    final 'Activated' step's pending value being the live merchants, and the (step, pending) list.
    """
    stages, pending, reached = [], [], total
    for step in STEPS:
        here = stuck_at.get(step, 0)
        stages.append((step, reached, here))
        if step != STEPS[-1]:
            pending.append((step, here))
            reached -= here
    return stages, pending


def funnel_figure(stages: list[tuple[str, int, int]], font_family: str):
    """Bar width = merchants who reached the step; label = merchants still pending there, as % of all stuck."""
    import plotly.graph_objects as go

    stuck_total = sum(p for s, _, p in stages if s != STEPS[-1]) or 1
    labels = [f"{STEP_EMOJI[s]}  {STEP_LABEL[s]}" for s, _, _ in stages]
    reached = [r for _, r, _ in stages]
    text, hover = [], []
    for s, r, p in stages:
        if s == STEPS[-1]:
            text.append(f"<b>{p} live</b>")
            hover.append(f"{p} merchants activated")
        else:
            text.append(f"<b>{p} pending</b>  ·  {p / stuck_total:.0%} of stuck")
            hover.append(f"{r} reached this step<br>{p} still pending here = {p / stuck_total:.0%} of the "
                         f"{stuck_total} stuck applications")
    fig = go.Figure(go.Funnel(
        y=labels, x=reached, text=text, texttemplate="%{text}", textposition="inside",
        textfont=dict(color="#FFFFFF", size=15, family=font_family),
        marker=dict(color=FUNNEL_COLORS[:len(reached)]),
        connector=dict(line=dict(color=LINE, width=1), fillcolor="#EEF2FA"),
        customdata=hover, hovertemplate="%{customdata}<extra></extra>",
    ))
    fig.update_layout(height=360, margin=dict(l=8, r=8, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family=font_family, color=NAVY, size=14),
                      hoverlabel=dict(bgcolor="#FFFFFF", font_color=NAVY))
    fig.update_yaxes(tickfont=dict(color=NAVY, size=14, family=font_family))
    return fig


def dropoff_panel(drops: list[tuple[str, int]], tpv: dict[str, float]) -> str:
    total = sum(n for _, n in drops) or 1
    rows = []
    for step, n in sorted(drops, key=lambda d: -d[1]):
        width = int(100 * n / total)
        share = n / total
        rows.append(f"""
<div style="display:flex;gap:12px;align-items:center;margin:12px 0;">
  <div style="width:42px;height:42px;border-radius:12px;background:#FFF0F0;display:flex;align-items:center;justify-content:center;
    font-size:22px;flex:0 0 42px;">{STEP_EMOJI[step]}</div>
  <div style="flex:1;min-width:0;">
    <div style="display:flex;justify-content:space-between;"><span style="font-weight:700;color:{NAVY};">{STEP_LABEL[step]}</span>
      <span style="font-weight:800;color:#E03131;">{share:.0%}</span></div>
    <div style="height:8px;background:#F4F6FA;border-radius:6px;margin-top:6px;"><div style="width:{width}%;height:8px;
      background:#FF6B6B;border-radius:6px;"></div></div>
    <div class="rp-muted" style="margin-top:3px;">{n} of {total} pending · ₹{tpv.get(step, 0):,.1f} L expected monthly TPV</div>
  </div></div>""")
    return (f'<div class="rp-card"><div class="rp-section">⏳ Pending by stage</div>{"".join(rows)}'
            f'<div class="rp-muted" style="margin-top:6px;">Share of the {total} stuck applications (stalled or '
            f'rejected) waiting at each step.</div></div>')


def cause_cards(causes: pd.DataFrame, by: str, title: str, unit: str) -> str:
    rows = causes[causes["is_catalog_cause"]].sort_values([by, "cause_code"], ascending=[False, True]).head(3)
    top = rows[by].max() or 1
    items = []
    for rank, r in enumerate(rows.itertuples(), 1):
        val = getattr(r, by)
        label = f"₹{val:,.1f} L" if unit == "tpv" else f"{int(val)} merchants"
        width = int(100 * val / top)
        items.append(f"""
<div style="display:flex;gap:12px;align-items:center;margin:10px 0;">
  <div style="width:42px;height:42px;border-radius:12px;background:#F1F5FF;display:flex;align-items:center;justify-content:center;
    font-size:22px;flex:0 0 42px;">{CAUSE_EMOJI.get(r.cause_code, "•")}</div>
  <div style="flex:1;min-width:0;">
    <div style="display:flex;justify-content:space-between;gap:8px;"><span style="font-weight:700;color:{NAVY};font-size:14px;">
      {rank}. {escape(r.cause)}</span><span style="font-weight:700;color:{BLUE};white-space:nowrap;">{label}</span></div>
    <div style="height:8px;background:#EEF2FA;border-radius:6px;margin-top:6px;"><div style="width:{width}%;height:8px;
      background:{BLUE};border-radius:6px;"></div></div>
    <div class="rp-muted" style="margin-top:3px;">{r.cause_code} · fixable: {escape(str(r.fixability))}</div>
  </div></div>""")
    return f'<div class="rp-card"><div class="rp-section">{title}</div>{"".join(items)}</div>'


def case_header(r: pd.Series, city: str | None) -> str:
    where = " · ".join(x for x in [escape(str(r["industry"] or "")), escape(city or ""),
                                   escape(str(r["business_type"] or ""))] if x)
    tpv = _n(r["expected_monthly_tpv_inr_lakh"])
    days = _n(r["days_since_last_activity"])
    return f"""
<div class="rp-card" style="display:flex;gap:18px;align-items:center;">
  {avatar_with_badge(r.name, r["industry"], 72)}
  <div style="flex:1;min-width:0;">
    <div style="font-size:22px;font-weight:800;color:{NAVY};">{escape(str(r.name))}
      <span style="font-size:15px;font-weight:600;color:{MUTED};margin-left:6px;">{escape(str(r["diagnosed_reason_code"]))}</span></div>
    <div class="rp-muted" style="margin:2px 0 8px;">{where}</div>
    {status_chip(r["recoverability"])}{tier_chip(r["priority_tier"])}{language_chip(r["preferred_language"])}
  </div>
  <div style="text-align:right;">
    <div class="rp-k">Expected monthly TPV</div><div style="font-size:22px;font-weight:800;color:{NAVY};">
      {"—" if tpv is None else f"₹{tpv:,.1f} L"}</div>
    <div class="rp-muted">{"inactivity unknown" if days is None else f"{days:g} days since last activity"}</div>
  </div>
</div>"""


def tracker(step_reached: str | None, code: str | None, status: str | None) -> str:
    """Onboarding progress: done steps green, the blocked step red (rejection) or amber (stopped), later steps grey."""
    idx = STEPS.index(step_reached) if step_reached in STEPS else -1
    stopped = code == "R13"
    nodes = []
    for i, step in enumerate(STEPS):
        if idx >= 0 and i < idx:
            bg, fg, icon, note = "#12B886", "#FFFFFF", "✓", "done"
        elif i == idx:
            if stopped:
                bg, fg, icon, note = "#F59F00", "#FFFFFF", "⏸", "stopped here"
            else:
                bg, fg, icon, note = "#E03131", "#FFFFFF", "!", "blocked here"
        else:
            bg, fg, icon, note = "#E9EDF5", MUTED, str(i + 1), ""
        line = "" if i == len(STEPS) - 1 else (
            f'<div style="position:absolute;top:19px;left:calc(50% + 22px);right:calc(-50% + 22px);height:4px;border-radius:2px;'
            f'background:{"#12B886" if idx >= 0 and i < idx else "#E9EDF5"};"></div>')
        nodes.append(f"""
<div style="flex:1;position:relative;text-align:center;">{line}
  <div style="width:42px;height:42px;border-radius:50%;background:{bg};color:{fg};margin:0 auto;display:flex;align-items:center;
    justify-content:center;font-weight:800;font-size:17px;position:relative;z-index:1;">{icon}</div>
  <div style="font-size:12.5px;font-weight:700;color:{NAVY};margin-top:6px;padding:0 6px;line-height:1.3;">{STEP_LABEL[step]}</div>
  <div style="font-size:11.5px;color:{"#E03131" if note == "blocked here" else "#B3540E" if note == "stopped here" else MUTED};">{note}</div>
</div>""")
    return f'<div class="rp-card"><div class="rp-section">Onboarding progress</div><div style="display:flex;">{"".join(nodes)}</div></div>'


def phone_preview(r: pd.Series, decision: dict | None = None) -> str:
    """WhatsApp-style preview for opted-in merchants; a call-sheet card for manual follow-up; a held state otherwise."""
    text = (decision or {}).get("text") or r["nudge_text"]
    channel = r["recommended_channel"]
    status = r["nudge_status"]
    approved = (decision or {}).get("status")
    stamp = {"approved": ("Approved by you · not sent", "#0B7A53", "#E3FAF0"),
             "escalated": ("Escalated · not sent", "#B3540E", "#FFF1E3")}.get(approved, ("Draft · awaiting approval", INK2, "#EEF0F4"))
    if status == "NO_NUDGE_HUMAN_REVIEW" or not isinstance(text, str):
        body = (f'<div style="text-align:center;padding:30px 10px;"><div style="font-size:42px;">🛡️</div>'
                f'<div style="font-weight:800;color:{NAVY};margin-top:8px;">Message held</div>'
                f'<div class="rp-muted" style="margin-top:4px;">No message is drafted or sent until a person confirms this case.</div></div>')
        return f'<div class="rp-card">{body}</div>'
    safe = escape(text).replace("\n", "<br>")
    if channel == "WhatsApp":
        return f"""
<div style="display:flex;justify-content:center;">
<div style="width:300px;background:{NAVY};border-radius:34px;padding:12px;">
  <div style="background:#ECE5DD;border-radius:24px;overflow:hidden;">
    <div style="background:#128C7E;color:#FFFFFF;padding:12px 14px;display:flex;align-items:center;gap:10px;">
      <div style="width:30px;height:30px;border-radius:50%;background:#FFFFFF;color:#128C7E;display:flex;align-items:center;
        justify-content:center;font-weight:800;">✓</div>
      <div><div style="font-weight:700;font-size:14px;">Merchant onboarding</div>
        <div style="font-size:11.5px;opacity:0.85;">WhatsApp · merchant opted in</div></div></div>
    <div style="padding:14px 12px 16px;min-height:200px;">
      <div style="background:#DCF8C6;border-radius:12px 12px 2px 12px;padding:10px 12px;font-size:13.5px;line-height:1.55;
        color:#1E2A1E;margin-left:18px;">{safe}
        <div style="text-align:right;font-size:10.5px;color:#5E7A5E;margin-top:4px;">draft</div></div>
    </div>
  </div>
  <div style="text-align:center;margin-top:8px;"><span class="rp-chip" style="background:{stamp[2]};color:{stamp[1]};margin:0;">
    {stamp[0]}</span></div>
</div></div>"""
    who = "Compliance team" if r["recoverability"] == "COMPLIANCE_REVIEW" else "Onboarding specialist"
    return f"""
<div class="rp-card" style="border-top:4px solid #7950F2;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;"><div style="font-size:28px;">📞</div>
    <div><div style="font-weight:800;color:{NAVY};">Manual follow-up</div>
    <div class="rp-muted">No WhatsApp consent{" · handled by " + who if who else ""}</div></div></div>
  <div style="background:#F6F8FC;border-radius:12px;padding:12px 14px;font-size:14px;line-height:1.6;color:{NAVY};">{safe}</div>
  <div style="margin-top:10px;"><span class="rp-chip" style="background:{stamp[2]};color:{stamp[1]};">{stamp[0]}</span></div>
</div>"""


def fact(label: str, value: str) -> str:
    return f'<div class="rp-k">{label}</div><div class="rp-v">{value}</div>'


def decided_by_chip(method: str) -> str:
    if method == "LLM_TEXT_CLASSIFICATION":
        return chip("✨ AI read the note + checks", "#F1ECFF", "#5B3CC4")
    if method == "HUMAN_REVIEW":
        return chip("👤 Needs a person", "#FFF1E3", "#B3540E")
    return chip("⚙️ Rule from the catalog", "#E8F0FF", "#1F4FBF")


def queue_card(r: pd.Series, city: str | None) -> str:
    tpv = _n(r["expected_monthly_tpv_inr_lakh"])
    rank = _n(r["priority_rank"])
    return f"""
<div class="rp-card" style="padding:14px 16px;display:flex;gap:14px;align-items:center;">
  {avatar_with_badge(r["application_id"], r["industry"], 52)}
  <div style="flex:1;min-width:0;">
    <div style="font-weight:800;color:{NAVY};">{"#" + str(int(rank)) + " · " if rank else ""}{escape(str(r["application_id"]))}
      <span style="color:{MUTED};font-weight:600;font-size:13px;">· {escape(str(r["industry"]))}{", " + escape(city) if city else ""}</span></div>
    <div style="color:{INK2};font-size:13.5px;margin:2px 0 6px;">{CAUSE_EMOJI.get(r["diagnosed_reason_code"], "•")}
      {escape(str(r["diagnosed_reason"])[:90])}</div>
    {tier_chip(r["priority_tier"])}{language_chip(r["preferred_language"])}
    {chip("WhatsApp", "#E3FAF0", "#0B7A53") if r["recommended_channel"] == "WhatsApp" else chip(str(r["recommended_channel"]), "#EEF0F4", "#3F4A5E")}
  </div>
  <div style="text-align:right;white-space:nowrap;"><div style="font-weight:800;color:{NAVY};font-size:18px;">
    {"—" if tpv is None else f"₹{tpv:,.1f} L"}</div><div class="rp-muted">{_n(r["days_since_last_activity"]) or 0:g} days idle</div></div>
</div>"""


def section(title: str, subtitle: str = "") -> str:
    sub = f'<div class="rp-muted" style="margin:-6px 0 10px;">{subtitle}</div>' if subtitle else ""
    return f'<div class="rp-section" style="font-size:20px;margin-top:14px;">{title}</div>{sub}'


__all__ = ["journey", "funnel_stages", "funnel_figure", "dropoff_panel", "STEP_LABEL","cause_cards", "case_header", "tracker", "phone_preview", "fact", "decided_by_chip",
           "queue_card", "section", "STEPS", "LINE"]
