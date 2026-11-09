"""Streamlit interface: Merchant Activation Recovery Copilot.

Run:  .venv\\Scripts\\streamlit run app.py
Nothing here sends a message. Approve / edit / escalate only record a decision for this session.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

import config
from core import nudge_safety, pipeline
from core.output_builder import write_outputs
from schemas.labels import RecommendedAction
from ui import components as ui
from ui.avatars import INDUSTRY_BADGE
from ui.theme import BLUE, CSS, INK2, LINE, MUTED, NAVY, STATUS, hero

load_dotenv(config.ROOT / ".env")
st.set_page_config(page_title="Activation Recovery Copilot", page_icon="🚀", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

MODE_LABELS = {
    "cache": "Saved AI answers (free, reproducible)",
    "off": "Rules only (no AI)",
    "live": "Live AI (calls Anthropic, costs money)",
}
OUTCOME_COLORS = {"Recoverable": "#12B886", "Close, no workaround": "#868E96",
                  "Compliance review": "#7950F2", "Needs a person": "#F08C00"}


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def fmt_missing(value, suffix: str = "") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
        return "— (missing)"
    return f"{value}{suffix}"


def hbar(labels, values, hover_name: str, value_fmt: str = "{:g}", colors=None) -> go.Figure:
    """Horizontal bars with labels on the axis (identity never by color alone) and hover on every bar."""
    labels, values = list(labels), list(values)
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h", width=0.6,
        marker=dict(color=colors or BLUE, cornerradius=6),
        text=[value_fmt.format(v) for v in values], textposition="outside",
        textfont=dict(color=INK2, size=13), cliponaxis=False,
        hovertemplate=f"%{{y}}<br>{hover_name}: %{{x}}<extra></extra>",
    ))
    fig.update_layout(height=max(170, 48 * len(labels) + 40), margin=dict(l=8, r=56, t=8, b=8),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      font=dict(color=INK2, size=13), hoverlabel=dict(bgcolor="#FFFFFF", font_color=NAVY))
    fig.update_xaxes(showgrid=True, gridcolor=LINE, zeroline=True, zerolinecolor=LINE, tickfont=dict(color=MUTED))
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=NAVY))
    return fig


def chart(fig: go.Figure, table: pd.DataFrame, key: str) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)
    with st.expander("Table view"):
        st.dataframe(table, hide_index=True, width="stretch")


# --- Session decisions (approve / edit / escalate). Never sends anything. --------------
if "decisions" not in st.session_state:
    st.session_state["decisions"] = {}
DECISIONS: dict = st.session_state["decisions"]


def record(app_id: str, status: str, text: str | None = None, note: str = "") -> None:
    DECISIONS[app_id] = {"status": status, "text": text, "note": note,
                         "time": datetime.now().strftime("%H:%M:%S")}


def decision_log() -> pd.DataFrame:
    rows = [{"application_id": k, "decision": v["status"], "edited_message": v.get("text") or "",
             "note": v.get("note", ""), "time": v["time"]} for k, v in DECISIONS.items()]
    return pd.DataFrame(rows, columns=["application_id", "decision", "edited_message", "note", "time"])


def actions(app_id: str, r: pd.Series, key: str) -> None:
    """Approve / edit / escalate. Held cases can only be escalated to a person."""
    current = DECISIONS.get(app_id, {}).get("status")
    if current:
        st.success(f"Your decision: **{current}** at {DECISIONS[app_id]['time']}. Nothing has been sent.", icon="📝")
    held = r["nudge_status"] == "NO_NUDGE_HUMAN_REVIEW" or not isinstance(r["nudge_text"], str)
    if held:
        reason = st.selectbox("Escalate to", ["Compliance team", "Onboarding lead", "Risk operations"], key=f"{key}_to")
        if st.button("👤 Escalate for a decision", key=f"{key}_esc", width="stretch"):
            record(app_id, "escalated", note=f"to {reason}")
            st.rerun()
        return
    if st.button("✅ Approve draft", key=f"{key}_ok", width="stretch", type="primary"):
        record(app_id, "approved", DECISIONS.get(app_id, {}).get("text"))
        st.rerun()
    c2, c3 = st.columns(2)
    editing = c2.toggle("✏️ Edit message", key=f"{key}_edit")
    if c3.button("👤 Escalate", key=f"{key}_esc", width="stretch"):
        record(app_id, "escalated", note="specialist asked for a second opinion")
        st.rerun()
    if editing:
        draft = DECISIONS.get(app_id, {}).get("text") or r["nudge_text"]
        new = st.text_area("Edit the message", draft, height=170, key=f"{key}_txt")
        try:
            action = RecommendedAction(r["recommended_action"])
        except ValueError:
            action = RecommendedAction.CORRECTIVE_NUDGE
        english = r["preferred_language"] in ("English",)
        issues = nudge_safety.check(new, new if english else "", r["preferred_language"], action,
                                    str(r["nudge_brief"]), r["step_reached"])
        if issues:
            st.warning("Automatic checks flag this edit: " + "; ".join(issues))
        else:
            st.caption("Automatic checks pass (links, numbers, script, compliance words). A person still approves it.")
        if st.button("Save edit and approve", key=f"{key}_save"):
            record(app_id, "approved (edited)", new)
            st.rerun()


# --- Sidebar ----------------------------------------------------------------------------
with st.sidebar:
    html(f'<div style="display:flex;gap:10px;align-items:center;margin-bottom:6px;"><div style="font-size:30px;">🚀</div>'
         f'<div><div style="font-weight:800;color:{NAVY};">Recovery copilot</div>'
         f'<div class="rp-muted">Run settings</div></div></div>')
    source = st.radio("Workbook", ["Supplied data pack", "Upload a workbook"], index=0)
    upload = st.file_uploader("Excel workbook (.xlsx)", type=["xlsx"]) if source == "Upload a workbook" else None
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    modes = ["cache", "off"] + (["live"] if has_key else [])
    mode = st.selectbox("AI mode", modes, format_func=MODE_LABELS.get, index=0)
    if not has_key:
        st.caption("This demo shows saved AI results, so every visit gives the same answers. Live AI is switched off.")
    st.selectbox("LLM provider", ["Anthropic"], disabled=True)
    st.selectbox("Model", [config.LLM_MODEL], disabled=True)
    if mode == "live":
        st.warning("Live mode calls the Anthropic API for anything not already saved. A full run on new data costs "
                   "roughly $0.50 to $3.")
    run_clicked = st.button("Run analysis", type="primary", width="stretch")
    st.divider()
    st.info("**Drafts and recommendations only.** Nothing is sent. Every message, closure and compliance route "
            "needs a person's approval.", icon="🛡️")
    if DECISIONS:
        st.metric("Your decisions this session", len(DECISIONS))


def _execute(mode: str, upload) -> pipeline.PipelineRun:
    if upload is None:
        return pipeline.run(config.DEFAULT_WORKBOOK, mode)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / upload.name
        path.write_bytes(upload.getvalue())
        return pipeline.run(path, mode)


if source == "Upload a workbook" and run_clicked and upload is None:
    st.sidebar.error("Choose a workbook to upload first.")
elif run_clicked or "run" not in st.session_state:
    with st.spinner("Running analysis…"):
        try:
            st.session_state["run"] = _execute(mode, upload)
            st.session_state["run_mode"] = mode
        except Exception as e:  # show validation problems instead of a stack trace
            st.session_state.pop("run", None)
            st.error(f"Couldn't process the workbook: {e}")
            st.stop()

run: pipeline.PipelineRun = st.session_state["run"]
res = run.results
ex = run.executive
cities = run.data.applications.set_index("application_id")["city"].to_dict()

html(hero(ex["non_activated_processed"], ex["recoverable"], ex["expected_monthly_tpv_at_stake_lakh"]))
st.caption(f"Source: `{run.data.source_file}` · AI mode: {MODE_LABELS[st.session_state['run_mode']]} · "
           f"Model: {run.llm.model} · Synthetic data only")

tab_overview, tab_queue, tab_nudge, tab_audit = st.tabs(
    ["Overview", "Application work queue", "Merchant nudge review", "Evaluation & audit"])

# --- Tab 1: Overview -------------------------------------------------------------------
with tab_overview:
    c = st.columns(6)
    c[0].metric("Non-activated", ex["non_activated_processed"], help="Stalled + Rejected applications processed")
    c[1].metric("Recoverable", ex["recoverable"])
    c[2].metric("Close (R10)", ex["not_recoverable_close"])
    c[3].metric("Compliance review", ex["compliance_review"])
    c[4].metric("Human review flagged", ex["human_review_flagged"])
    c[5].metric("TPV at stake (Rs lakh)", f"{ex['expected_monthly_tpv_at_stake_lakh']:,.1f}",
                help="Expected monthly TPV at stake: sum of merchants' declared expected monthly TPV for RECOVERABLE "
                     "applications. Not recovered TPV, revenue or a forecast.")

    html(ui.section("Onboarding journey", "Where all 100 applicants are today. KYC documents is the bottleneck."))
    apps = run.data.applications
    counts = apps["step_reached"].value_counts().to_dict()
    tpv_step = pd.to_numeric(res["expected_monthly_tpv_inr_lakh"]).groupby(res["step_reached"]).sum().to_dict()
    html(ui.journey(counts, tpv_step))

    left, right = st.columns(2)
    with left:
        html(ui.cause_cards(run.causes, "applications", "🔥 Top causes by number of merchants", "count"))
    with right:
        html(ui.cause_cards(run.causes, "expected_monthly_tpv_represented_lakh", "💰 Top causes by expected TPV", "tpv"))

    left, right = st.columns([1.15, 1])
    with left:
        html(ui.section("Start here", f"Highest-priority recoverable merchants. The top 17 hold "
                        f"{ex['tpv_at_stake_by_tier_lakh'].get('HIGH', 0) / ex['expected_monthly_tpv_at_stake_lakh']:.0%} "
                        "of the TPV at stake."))
        for _, q in res[res["priority_tier"] == "HIGH"].sort_values("priority_rank").head(4).iterrows():
            html(ui.queue_card(q, cities.get(q["application_id"])))
    with right:
        html(ui.section("Outcome for the 75 stuck merchants"))
        out = res["recoverability"].map(lambda v: STATUS[v][0]).value_counts().reindex(list(OUTCOME_COLORS), fill_value=0)
        chart(hbar(out.index, out.values, "Merchants", colors=[OUTCOME_COLORS[k] for k in out.index]),
              out.rename_axis("Outcome").reset_index(name="Merchants"), "outcome")
        html(ui.section("Stopped without a rejection (R13)"))
        chart(hbar(run.steps["step_reached"], run.steps["applications"], "Merchants", colors="#F59F00"),
              run.steps, "abandon")

    with st.expander("All causes"):
        st.dataframe(run.causes, hide_index=True, width="stretch")

# --- Tab 2: Work queue -----------------------------------------------------------------
with tab_queue:
    f = st.columns([1.2, 1, 1, 1, 1, 1])
    search = f[0].text_input("Search application ID", placeholder="A3051")
    sel_rec = f[1].multiselect("Recoverability", sorted(res["recoverability"].unique()))
    sel_dx = f[2].multiselect("Diagnosis status", sorted(res["diagnosis_status"].unique()))
    sel_lang = f[3].multiselect("Language", sorted(res["preferred_language"].dropna().unique()))
    sel_step = f[4].multiselect("Onboarding step", sorted(res["step_reached"].dropna().unique()))
    sel_tier = f[5].multiselect("Priority", ["HIGH", "MEDIUM", "LOW", "UNRANKED_REVIEW"])

    q = res.copy()
    if search:
        q = q[q["application_id"].str.contains(search.strip(), case=False, na=False)]
    for col, chosen in [("recoverability", sel_rec), ("diagnosis_status", sel_dx), ("preferred_language", sel_lang),
                        ("step_reached", sel_step), ("priority_tier", sel_tier)]:
        if chosen:
            q = q[q[col].isin(chosen)]
    q = q.assign(_r=q["priority_rank"].fillna(10_000)).sort_values(["_r", "application_id"])
    view = pd.DataFrame({
        "": [INDUSTRY_BADGE.get(i, "🏪") for i in q["industry"]],
        "application_id": q["application_id"],
        "business": q["industry"],
        "cause": q["diagnosed_reason_code"],
        "decision": q["recoverability"].map(lambda v: STATUS[v][0]),
        "priority": q["priority_tier"],
        "rank": q["priority_rank"],
        "TPV (Rs L)": q["expected_monthly_tpv_inr_lakh"],
        "channel": q["recommended_channel"],
        "language": q["preferred_language"],
        "your decision": [DECISIONS.get(a, {}).get("status", "") for a in q["application_id"]],
    })
    st.caption(f"{len(view)} of {len(res)} stuck merchants. Click a row to open the case.")
    event = st.dataframe(view, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                         key="queue_table", row_height=44,
                         column_config={"": st.column_config.TextColumn("", width="small"),
                                        "rank": st.column_config.NumberColumn("rank", format="%d")})
    rows = event.selection.rows if event and event.selection else []
    chosen_id = view.iloc[rows[0]]["application_id"] if rows else (view.iloc[0]["application_id"] if len(view) else None)

    if chosen_id:
        r = res.set_index("application_id").loc[chosen_id]
        st.divider()
        html(ui.case_header(r, cities.get(chosen_id)))
        if r["recoverability"] == "COMPLIANCE_REVIEW":
            st.error("Compliance case: route to the Compliance team. Never share the reason with the merchant.", icon="🛑")
        elif r["recoverability"] == "NOT_RECOVERABLE_CLOSE":
            st.warning("Close politely. Don't suggest any workaround.", icon="⚠️")
        if r["human_review_required"]:
            st.warning(f"Human review required: {r['review_reasons']}", icon="👤")

        left, right = st.columns([1.25, 1])
        with left:
            html(ui.tracker(r["step_reached"], r["diagnosed_reason_code"], r["application_status"]))
            ai_reason = (f'<div class="rp-k">AI\'s reason</div><div class="rp-v"><i>{ui.escape(r["ai_explanation"])}</i></div>'
                         if isinstance(r["ai_explanation"], str) else "")
            if r["priority_status"] == "OK":
                prio = f"{r['priority_tier']} · rank {int(r['priority_rank'])} · score {r['priority_score']}"
            elif r["priority_status"] == "NEEDS_DATA_REVIEW":
                prio = "Not ranked: TPV or days inactive missing"
            else:
                prio = "Not ranked: only recoverable cases are ranked for outreach"
            html(f"""
<div class="rp-card">
  <div class="rp-section">Diagnosis</div>
  {ui.decided_by_chip(r["diagnosis_method"])}
  <div class="rp-quote">“{ui.escape(fmt_missing(r["rejection_message_original"]))}”
    <div class="rp-muted" style="margin-top:4px;">Reviewer note · original code {ui.escape(fmt_missing(r["rejection_code_original"]))}</div></div>
  {ui.fact("What went wrong", ui.escape(fmt_missing(r["diagnosed_reason"])))}
  {ui.fact("Evidence used", ui.escape(fmt_missing(r["diagnosis_evidence"])))}
  {ai_reason}
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 18px;margin-top:6px;">
    <div>{ui.fact("Fixable (catalog)", ui.escape(str(r["fixability"])))}</div>
    <div>{ui.fact("Next action", ui.escape(str(r["recommended_action"])))}</div>
    <div>{ui.fact("Priority", ui.escape(prio))}</div>
    <div>{ui.fact("Channel", ui.escape(str(r["recommended_channel"])) + " · WhatsApp opt-in " + ui.escape(fmt_missing(r["whatsapp_opted_in"])))}</div>
  </div>
  {"" if not r["data_flags"] else ui.fact("Data flags", ui.escape(str(r["data_flags"])))}
</div>""")
        with right:
            html(ui.section("Merchant message"))
            html(ui.phone_preview(r, DECISIONS.get(chosen_id)))
            actions(chosen_id, r, f"q_{chosen_id}")

# --- Tab 3: Nudge review --------------------------------------------------------------
with tab_nudge:
    order = res.assign(_r=res["priority_rank"].fillna(10_000)).sort_values(["_r", "application_id"]).set_index("application_id")
    icon = {"DRAFTED": "💬", "NEUTRAL_COMPLIANCE": "🛡️", "NO_NUDGE_HUMAN_REVIEW": "⏸️", "NOT_GENERATED": "…"}
    pick = st.selectbox("Application", order.index,
                        format_func=lambda i: f"{icon.get(order.loc[i, 'nudge_status'], '•')} {i} · "
                                              f"{order.loc[i, 'preferred_language']} · {order.loc[i, 'recommended_channel']}"
                                              + (f" · {DECISIONS[i]['status']}" if i in DECISIONS else ""))
    n = order.loc[pick]
    html(ui.case_header(n, cities.get(pick)))
    left, right = st.columns([1, 1.1])
    with left:
        html(ui.phone_preview(n, DECISIONS.get(pick)))
    with right:
        if n["recoverability"] == "COMPLIANCE_REVIEW":
            st.error("Compliance case. Only the neutral 'under review' wording may be used, and only after the "
                     "Compliance team approves.", icon="🛑")
        if not bool(n["whatsapp_allowed"]):
            st.info("Merchant has NOT opted in to WhatsApp. Manual follow-up only.", icon="🚫")
        safety = {True: "✅ Passed", False: "❌ Failed"}.get(n["nudge_safety_check_passed"], "— Not run")
        back = n["nudge_english_back_translation"] if isinstance(n["nudge_english_back_translation"], str) else ""
        html(f"""
<div class="rp-card">
  <div class="rp-section">English translation for the reviewer</div>
  <div style="background:#F6F8FC;border-radius:12px;padding:12px 14px;color:{NAVY};line-height:1.6;font-size:14px;">
    {ui.escape(back) or '<span class="rp-muted">No draft for this case.</span>'}</div>
  <div class="rp-muted" style="margin-top:8px;">Written by the same model as the draft, so it's a check, not proof.</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 18px;margin-top:12px;">
    <div>{ui.fact("Automatic safety checks", safety)}</div>
    <div>{ui.fact("Written by", ui.escape(str(n["nudge_model"])) + " · " + ui.escape(str(n["nudge_prompt_version"])))}</div>
  </div>
  {"" if not n["nudge_safety_issues"] else ui.fact("Check notes", ui.escape(str(n["nudge_safety_issues"])))}
</div>""")
        actions(pick, n, f"n_{pick}")
        with st.expander("What the message was allowed to say (the brief)"):
            st.write(n["nudge_brief"])

    html(ui.section("Your decisions this session", "Recorded here only. Nothing is sent to any merchant."))
    log = decision_log()
    if len(log):
        st.dataframe(log, hide_index=True, width="stretch")
        st.download_button("Download decision log (CSV)", log.to_csv(index=False).encode("utf-8-sig"),
                           "decision_log.csv", "text/csv")
    else:
        st.caption("No decisions yet. Approve, edit or escalate a draft above.")
    drafts = res[res["nudge_text"].notna()][["application_id", "preferred_language", "recommended_channel",
                                              "nudge_status", "nudge_safety_check_passed", "nudge_text",
                                              "nudge_english_back_translation"]]
    st.download_button("Download all drafts (CSV)", drafts.to_csv(index=False).encode("utf-8-sig"),
                       "p3_draft_messages.csv", "text/csv")

# --- Tab 4: Evaluation & audit -------------------------------------------------------------
with tab_audit:
    u = run.summary["ai_usage"]
    hr = res[res["human_review_required"] | res["recoverability"].eq("NEEDS_HUMAN_REVIEW")]
    a = st.columns(5)
    a[0].metric("Decided by rules", int(res["diagnosis_method"].isin(["CATALOG_RULE", "INACTIVITY_RULE"]).sum()))
    a[1].metric("AI-classified", int((res["diagnosis_method"] == "LLM_TEXT_CLASSIFICATION").sum()))
    a[2].metric("Unknown / human review", len(hr), help="Rows listed in the 'Unknown or human-review cases' table")
    a[3].metric("Safety-check failures", int((res["nudge_safety_check_passed"] == False).sum()))  # noqa: E712
    a[4].metric("API calls this run", u["api_calls"], help=f"Saved answers reused: {u['cache_hits']}")

    html(f"""<div class="rp-card"><div class="rp-section">🔎 Provenance</div>
<span class="rp-chip" style="background:#E8F0FF;color:#1F4FBF;">model {run.llm.model}</span>
<span class="rp-chip" style="background:#F1ECFF;color:#5B3CC4;">diagnosis prompt {config.DIAGNOSIS_PROMPT_VERSION}</span>
<span class="rp-chip" style="background:#F1ECFF;color:#5B3CC4;">message prompt {config.NUDGE_PROMPT_VERSION}</span>
<span class="rp-chip" style="background:#E3FAF0;color:#0B7A53;">rules {config.RULE_VERSION}</span>
<span class="rp-chip" style="background:#EEF0F4;color:#3F4A5E;">run {res['run_timestamp_utc'].iloc[0] if len(res) else '—'}</span>
<span class="rp-chip" style="background:#EEF0F4;color:#3F4A5E;">tokens in/out {u['input_tokens']:,}/{u['output_tokens']:,}</span>
</div>""")
    if u.get("disabled_reason"):
        st.error(f"AI was disabled during this run: {u['disabled_reason']}")

    html(ui.section("Who decided each case"))
    cov = res["diagnosis_method"].map({"CATALOG_RULE": "Rule: reviewer code", "INACTIVITY_RULE": "Rule: stopped, no rejection",
                                       "LLM_TEXT_CLASSIFICATION": "AI: read free-text note",
                                       "HUMAN_REVIEW": "Person"}).value_counts()
    chart(hbar(cov.index, cov.values, "Cases", colors=["#2F6BFF", "#1C7ED6", "#7950F2", "#F08C00"][:len(cov)]),
          cov.rename_axis("Decided by").reset_index(name="Cases"), "coverage")

    html(ui.section("AI-classified cases"))
    ai = res[res["diagnosis_method"] == "LLM_TEXT_CLASSIFICATION"]
    st.dataframe(ai[["application_id", "rejection_message_original", "diagnosed_reason_code", "diagnosis_evidence",
                     "ai_explanation", "recoverability", "human_review_required"]], hide_index=True, width="stretch")

    html(ui.section("Unknown or human-review cases"))
    if len(hr):
        st.dataframe(hr[["application_id", "diagnosed_reason_code", "recoverability", "review_reasons"]],
                     hide_index=True, width="stretch")
    else:
        st.success("None in this run.")

    html(ui.section("Safety-check failures"))
    sf = res[res["nudge_safety_check_passed"] == False]  # noqa: E712
    if len(sf):
        st.dataframe(sf[["application_id", "preferred_language", "nudge_safety_issues", "nudge_text"]],
                     hide_index=True, width="stretch")
    else:
        st.success("No drafted message failed the automatic checks. (Checks don't prove translation quality.)")

    html(ui.section("Priority weight sensitivity"))
    share = ex.get("priority_effective_tpv_share")
    if share is not None:
        st.caption(f"Nominal weights {config.PRIORITY_WEIGHT_TPV:.0%} TPV / {config.PRIORITY_WEIGHT_RECENCY:.0%} "
                   f"recency. Because inactivity only spans a few weeks, TPV in practice drives about "
                   f"**{share:.0%}** of the score's variation in this data.")
    st.dataframe(run.sensitivity, hide_index=True, width="stretch")

    html(ui.section("Data validation issues"))
    issues = pd.DataFrame([i.__dict__ for i in run.data.issues])
    if len(issues):
        st.dataframe(issues, hide_index=True)
    else:
        st.success("No data issues found.")

    html(ui.section("Downloads"))
    d1, d2 = st.columns(2)
    d1.download_button("Full results (CSV)", res.to_csv(index=False).encode("utf-8-sig"), "p3_results.csv",
                       "text/csv", width="stretch")
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_outputs(run.data, res, run.audit, run.summary, Path(tmp),
                              extra_sheets=run.extra_sheets(), front_sheets=run.front_sheets())
        xlsx_bytes = paths["xlsx"].read_bytes()
    d2.download_button("Full results (Excel, all sheets)", xlsx_bytes, "p3_results.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
