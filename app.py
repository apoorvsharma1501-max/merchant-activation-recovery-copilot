"""Streamlit interface: Merchant Activation Recovery & Diagnosis Copilot.

Run:  .venv\\Scripts\\streamlit run app.py
Nothing here sends a message. Every draft and recommendation needs human approval.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

import config
from core import pipeline
from core.output_builder import write_outputs

load_dotenv(config.ROOT / ".env")
st.set_page_config(page_title="Activation Recovery Copilot", page_icon="🧭", layout="wide")

# --- Theme-aware chart tokens (reference palette from the dataviz guidance) ------
_theme = getattr(getattr(st, "context", None), "theme", None)
IS_DARK = getattr(_theme, "type", "light") == "dark"
TOKENS = {
    "series": "#3987e5" if IS_DARK else "#2a78d6",
    "ink": "#f0efec" if IS_DARK else "#0b0b0b",
    "ink2": "#c3c2b7" if IS_DARK else "#52514e",
    "muted": "#898781",
    "grid": "#2c2c2a" if IS_DARK else "#e1e0d9",
    "axis": "#383835" if IS_DARK else "#c3c2b7",
}

MODE_LABELS = {
    "cache": "Saved AI answers (free, reproducible)",
    "off": "Rules only (no AI)",
    "live": "Live AI (calls Anthropic, costs money)",
}
RECOVERABILITY_LABELS = {
    "RECOVERABLE": "Recoverable",
    "NOT_RECOVERABLE_CLOSE": "Close (not recoverable)",
    "COMPLIANCE_REVIEW": "Compliance review",
    "NEEDS_HUMAN_REVIEW": "Needs human review",
}


def fmt_missing(value, suffix: str = "") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
        return "— (missing)"
    return f"{value}{suffix}"


def decided_by(method: str) -> str:
    return "AI (Claude) + checks" if method == "LLM_TEXT_CLASSIFICATION" else (
        "Person" if method == "HUMAN_REVIEW" else "Rule")


def hbar(labels, values, hover_name: str, value_fmt: str = "{:g}", height: int | None = None) -> go.Figure:
    """Single-series horizontal bar: one hue, thin rounded bars, recessive grid, hover on every bar."""
    labels, values = list(labels), list(values)
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h", width=0.55,
        marker=dict(color=TOKENS["series"], cornerradius=4),
        text=[value_fmt.format(v) for v in values], textposition="outside",
        textfont=dict(color=TOKENS["ink2"], size=12), cliponaxis=False,
        hovertemplate=f"%{{y}}<br>{hover_name}: %{{x}}<extra></extra>",
    ))
    fig.update_layout(
        height=height or max(160, 46 * len(labels) + 40), margin=dict(l=8, r=48, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
        font=dict(color=TOKENS["ink2"], size=13), bargap=0.35,
        hoverlabel=dict(bgcolor="#1a1a19" if IS_DARK else "#ffffff", font_color=TOKENS["ink"]),
    )
    fig.update_xaxes(showgrid=True, gridcolor=TOKENS["grid"], gridwidth=1, zeroline=True,
                     zerolinecolor=TOKENS["axis"], tickfont=dict(color=TOKENS["muted"]))
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=TOKENS["ink2"]))
    return fig


def chart(fig: go.Figure, table: pd.DataFrame, key: str) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)
    with st.expander("Table view"):
        st.dataframe(table, hide_index=True, width="stretch")


# --- Sidebar ---------------------------------------------------------------------
with st.sidebar:
    st.header("Run settings")
    source = st.radio("Workbook", ["Supplied data pack", "Upload a workbook"], index=0)
    upload = st.file_uploader("Excel workbook (.xlsx)", type=["xlsx"]) if source == "Upload a workbook" else None

    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    modes = ["cache", "off"] + (["live"] if has_key else [])
    mode = st.selectbox("AI mode", modes, format_func=MODE_LABELS.get, index=0)
    if not has_key:
        st.caption("Live AI is unavailable: no ANTHROPIC_API_KEY in `.env`. Saved answers still work.")
    st.selectbox("LLM provider", ["Anthropic"], disabled=True)
    st.selectbox("Model", [config.LLM_MODEL], disabled=True)
    if mode == "live":
        st.warning("Live mode calls the Anthropic API for anything not already saved. "
                   "A full run on new data costs roughly $0.50–$3.")
    run_clicked = st.button("Run analysis", type="primary", width="stretch")

    st.divider()
    st.warning("**Drafts and recommendations only.** Nothing is sent. Every message, closure and "
               "compliance route needs approval by a person.", icon="⚠️")


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
            st.error(f"Could not process the workbook: {e}")
            st.stop()

run: pipeline.PipelineRun = st.session_state["run"]
res = run.results
ex = run.executive

st.title("Merchant Activation Recovery & Diagnosis Copilot")
st.caption(f"Source: `{run.data.source_file}` · AI mode: {MODE_LABELS[st.session_state['run_mode']]} · "
           f"Model: {run.llm.model} · Synthetic data only")

tab_overview, tab_queue, tab_nudge, tab_audit = st.tabs(
    ["Overview", "Application work queue", "Merchant nudge review", "Evaluation & audit"])

# --- Tab 1: Overview -------------------------------------------------------------
with tab_overview:
    c = st.columns(6)
    c[0].metric("Non-activated", ex["non_activated_processed"], help="Stalled + Rejected applications processed")
    c[1].metric("Recoverable", ex["recoverable"])
    c[2].metric("Close (R10)", ex["not_recoverable_close"])
    c[3].metric("Compliance review", ex["compliance_review"])
    c[4].metric("Human review flagged", ex["human_review_flagged"])
    c[5].metric("TPV at stake (Rs lakh)", f"{ex['expected_monthly_tpv_at_stake_lakh']:,.1f}",
                help="Expected monthly TPV at stake: sum of merchants' declared expected monthly TPV for "
                     "RECOVERABLE applications. Not recovered TPV, revenue or a forecast.")
    st.caption("TPV in Rs lakh (1 lakh = 100,000). *Expected monthly TPV* is what merchants declared at signup.")

    left, right = st.columns(2)
    with left:
        st.subheader("Outcome for non-activated applications")
        out = res["recoverability"].map(RECOVERABILITY_LABELS).value_counts().reindex(
            RECOVERABILITY_LABELS.values(), fill_value=0)
        chart(hbar(out.index, out.values, "Applications"),
              out.rename_axis("Outcome").reset_index(name="Applications"), "outcome")
    with right:
        st.subheader("Where non-activated applications stopped")
        steps = res["step_reached"].fillna("— (missing)").value_counts()
        chart(hbar(steps.index, steps.values, "Applications"),
              steps.rename_axis("Step reached").reset_index(name="Applications"), "steps")

    st.subheader("Top three systemic causes")
    from core import analytics  # local import keeps module order simple

    by_count = analytics.top_causes(run.causes, "applications")
    by_tpv = analytics.top_causes(run.causes, "expected_monthly_tpv_represented_lakh")
    l2, r2 = st.columns(2)
    with l2:
        st.markdown("**By number of applications**")
        chart(hbar(by_count["cause_code"] + " · " + by_count["cause"], by_count["applications"], "Applications"),
              by_count[["cause_code", "cause", "applications", "fixability"]], "top_count")
    with r2:
        st.markdown("**By expected monthly TPV (Rs lakh)**")
        chart(hbar(by_tpv["cause_code"] + " · " + by_tpv["cause"], by_tpv["expected_monthly_tpv_represented_lakh"],
                   "Rs lakh", "{:,.1f}"),
              by_tpv[["cause_code", "cause", "expected_monthly_tpv_represented_lakh", "fixability"]], "top_tpv")

    l3, r3 = st.columns(2)
    with l3:
        st.markdown("**Fixable rejections, excluding abandonment**")
        st.markdown("By count: " + "; ".join(ex["top3_fixable_rejections_by_count"]))
        st.markdown("By TPV: " + "; ".join(ex["top3_fixable_rejections_by_tpv"]))
    with r3:
        st.markdown("**Abandoned with no rejection (R13): where they stopped**")
        chart(hbar(run.steps["step_reached"], run.steps["applications"], "Applications"), run.steps, "abandon")

    with st.expander("All causes"):
        st.dataframe(run.causes, hide_index=True, width="stretch")

# --- Tab 2: Work queue ------------------------------------------------------------
with tab_queue:
    f = st.columns([1.2, 1, 1, 1, 1, 1])
    search = f[0].text_input("Search application ID", placeholder="e.g. A3051")
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
    q = q.assign(decided_by=q["diagnosis_method"].map(decided_by),
                 _r=q["priority_rank"].fillna(10_000)).sort_values(["_r", "application_id"])
    view = q[["application_id", "application_status", "diagnosed_reason_code", "recoverability", "priority_tier",
              "priority_rank", "recommended_channel", "human_review_required", "decided_by"]]

    st.caption(f"{len(view)} of {len(res)} non-activated applications. Click a row to see the full record.")
    event = st.dataframe(view, hide_index=True, width="stretch", on_select="rerun",
                         selection_mode="single-row", key="queue_table",
                         column_config={"priority_rank": st.column_config.NumberColumn("rank", format="%d"),
                                        "human_review_required": st.column_config.CheckboxColumn("human review")})
    rows = event.selection.rows if event and event.selection else []
    chosen_id = view.iloc[rows[0]]["application_id"] if rows else (view.iloc[0]["application_id"] if len(view) else None)

    if chosen_id:
        r = res.set_index("application_id").loc[chosen_id]
        st.divider()
        st.subheader(f"{chosen_id} · {r['diagnosed_reason_code']}")
        badge = decided_by(r["diagnosis_method"])
        if r["recoverability"] == "COMPLIANCE_REVIEW":
            st.error("Compliance case: route to the Compliance team. Never share the reason with the merchant.",
                     icon="🛑")
        elif r["recoverability"] == "NOT_RECOVERABLE_CLOSE":
            st.warning("Close politely. Do not suggest any workaround.", icon="⚠️")
        if r["human_review_required"]:
            st.warning(f"Human review required: {r['review_reasons']}", icon="👤")

        a, b, c3 = st.columns(3)
        with a:
            st.markdown("**Diagnosis**")
            st.markdown(f"Decided by: **{badge}** (`{r['diagnosis_method']}`)")
            st.markdown(f"Reason: {fmt_missing(r['diagnosed_reason'])}")
            st.markdown(f"Status: `{r['diagnosis_status']}`")
            st.markdown(f"Evidence: {fmt_missing(r['diagnosis_evidence'])}")
            if isinstance(r["ai_explanation"], str):
                st.markdown(f"AI's reason: _{r['ai_explanation']}_")
        with b:
            st.markdown("**Decision**")
            st.markdown(f"Fixable (catalog): **{r['fixability']}**")
            st.markdown(f"Recoverability: **{RECOVERABILITY_LABELS.get(r['recoverability'], r['recoverability'])}**")
            st.markdown(f"Recommended action: {r['recommended_action']}")
            if r["priority_status"] == "OK":
                st.markdown(f"Priority: **{r['priority_tier']}** (rank {int(r['priority_rank'])}, "
                            f"score {r['priority_score']})")
            elif r["priority_status"] == "NEEDS_DATA_REVIEW":
                st.markdown("Priority: not ranked – TPV or days inactive missing (needs data review)")
            else:
                st.markdown("Priority: not ranked – only recoverable cases are ranked for outreach")
            st.markdown(f"Channel: {r['recommended_channel']}")
        with c3:
            st.markdown("**Source record**")
            st.markdown(f"Status: {fmt_missing(r['application_status'])} · Step: {fmt_missing(r['step_reached'])}")
            st.markdown(f"Original code: {fmt_missing(r['rejection_code_original'])}")
            st.markdown(f"Reviewer text: {fmt_missing(r['rejection_message_original'])}")
            st.markdown(f"Expected TPV: {fmt_missing(r['expected_monthly_tpv_inr_lakh'], ' lakh')} · "
                        f"Days inactive: {fmt_missing(r['days_since_last_activity'])}")
            st.markdown(f"Language: {fmt_missing(r['preferred_language'])} · "
                        f"WhatsApp opt-in: {fmt_missing(r['whatsapp_opted_in'])}")
            if r["data_flags"]:
                st.markdown(f"Data flags: {r['data_flags']}")
        st.markdown("**Merchant message**")
        if isinstance(r["nudge_text"], str) and r["nudge_status"] != "NO_NUDGE_HUMAN_REVIEW":
            st.code(r["nudge_text"], language=None, wrap_lines=True)
            st.caption(f"Draft – not sent. Full review in the *Merchant nudge review* tab. Status: {r['nudge_status']}")
        else:
            st.info(f"No message drafted ({r['nudge_status']}). {r['nudge_brief']}")

# --- Tab 3: Nudge review ---------------------------------------------------------
with tab_nudge:
    order = res.assign(_r=res["priority_rank"].fillna(10_000)).sort_values(["_r", "application_id"])
    pick = st.selectbox(
        "Application", order["application_id"],
        format_func=lambda i: (f"{i} · {order.set_index('application_id').loc[i, 'preferred_language']} · "
                               f"{order.set_index('application_id').loc[i, 'nudge_status']}"))
    n = res.set_index("application_id").loc[pick]

    safety = {True: "Passed", False: "Failed"}.get(n["nudge_safety_check_passed"], "Not run")
    m = st.columns(4)
    m[0].markdown(f"**Language**  \n{fmt_missing(n['nudge_language'])}")
    m[1].markdown(f"**Recommended channel**  \n{n['recommended_channel']}")
    m[2].markdown(f"**WhatsApp opt-in**  \n{'Yes' if n['whatsapp_allowed'] else 'No'}",
                  help="WhatsApp is recommended only when the merchant explicitly opted in.")
    m[3].markdown(f"**Automatic safety checks**  \n{safety}")

    if n["recoverability"] == "COMPLIANCE_REVIEW":
        st.error("Compliance case. Only the neutral 'under review' wording may be used, and only after the "
                 "Compliance team approves.", icon="🛑")
    if not n["whatsapp_allowed"]:
        st.info("Merchant has NOT opted in to WhatsApp. Use manual follow-up only.", icon="🚫")

    if isinstance(n["nudge_text"], str):
        left, right = st.columns(2)
        with left:
            st.markdown(f"**Draft message ({n['nudge_language']})**")
            st.code(n["nudge_text"], language=None, wrap_lines=True)
        with right:
            st.markdown("**English back-translation** (written by the same model; a check, not proof)")
            st.code(n["nudge_english_back_translation"] or "", language=None, wrap_lines=True)
        st.caption(f"Status: `{n['nudge_status']}` · Written by: {n['nudge_model']} "
                   f"({n['nudge_prompt_version']}) · **Not sent.** Approval by a person is required.")
        if n["nudge_safety_issues"]:
            st.warning(f"Check results: {n['nudge_safety_issues']}")
    else:
        st.info(f"No message drafted ({n['nudge_status']}). {n['nudge_safety_issues'] or ''}")
    with st.expander("What the message was allowed to say (the brief)"):
        st.write(n["nudge_brief"])

    drafts = res[res["nudge_text"].notna()][["application_id", "preferred_language", "recommended_channel",
                                              "nudge_status", "nudge_safety_check_passed", "nudge_text",
                                              "nudge_english_back_translation"]]
    st.download_button("Download all drafts (CSV)", drafts.to_csv(index=False).encode("utf-8-sig"),
                       "p3_draft_messages.csv", "text/csv")

# --- Tab 4: Evaluation & audit ---------------------------------------------------
with tab_audit:
    u = run.summary["ai_usage"]
    a = st.columns(5)
    a[0].metric("Decided by rules", int(res["diagnosis_method"].isin(["CATALOG_RULE", "INACTIVITY_RULE"]).sum()))
    a[1].metric("AI-classified", int((res["diagnosis_method"] == "LLM_TEXT_CLASSIFICATION").sum()))
    hr = res[res["human_review_required"] | res["recoverability"].eq("NEEDS_HUMAN_REVIEW")]
    a[2].metric("Unknown / human review", len(hr), help="Rows listed in the 'Unknown or human-review cases' table")
    a[3].metric("Safety-check failures", int((res["nudge_safety_check_passed"] == False).sum()))  # noqa: E712
    a[4].metric("API calls this run", u["api_calls"], help=f"Saved answers reused: {u['cache_hits']}")

    st.markdown(f"**Provenance** · model `{run.llm.model}` · diagnosis prompt `{config.DIAGNOSIS_PROMPT_VERSION}` · "
                f"nudge prompt `{config.NUDGE_PROMPT_VERSION}` · rules `{config.RULE_VERSION}` · "
                f"run `{res['run_timestamp_utc'].iloc[0] if len(res) else '—'}` · "
                f"tokens in/out this run {u['input_tokens']:,}/{u['output_tokens']:,}")
    if u.get("disabled_reason"):
        st.error(f"AI was disabled during this run: {u['disabled_reason']}")

    st.subheader("Rule coverage")
    cov = res["diagnosis_method"].value_counts()
    chart(hbar(cov.index, cov.values, "Applications"), cov.rename_axis("Method").reset_index(name="Applications"),
          "coverage")

    st.subheader("AI-classified cases")
    ai = res[res["diagnosis_method"] == "LLM_TEXT_CLASSIFICATION"]
    st.dataframe(ai[["application_id", "rejection_message_original", "diagnosed_reason_code", "diagnosis_evidence",
                     "ai_explanation", "recoverability", "human_review_required"]],
                 hide_index=True, width="stretch")

    st.subheader("Unknown or human-review cases")
    if len(hr):
        st.dataframe(hr[["application_id", "diagnosed_reason_code", "recoverability", "review_reasons"]],
                     hide_index=True, width="stretch")
    else:
        st.success("None in this run.")

    st.subheader("Safety-check failures")
    sf = res[res["nudge_safety_check_passed"] == False]  # noqa: E712
    if len(sf):
        st.dataframe(sf[["application_id", "preferred_language", "nudge_safety_issues", "nudge_text"]],
                     hide_index=True, width="stretch")
    else:
        st.success("No drafted message failed the automatic checks. (Checks do not prove translation quality.)")

    st.subheader("Priority weight sensitivity")
    st.dataframe(run.sensitivity, hide_index=True, width="stretch")

    st.subheader("Data validation issues")
    issues = pd.DataFrame([i.__dict__ for i in run.data.issues])
    if len(issues):
        st.dataframe(issues, hide_index=True)
    else:
        st.success("No data issues found.")

    st.subheader("Downloads")
    d1, d2 = st.columns(2)
    d1.download_button("Full results (CSV)", res.to_csv(index=False).encode("utf-8-sig"), "p3_results.csv",
                       "text/csv", width="stretch")
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_outputs(run.data, res, run.audit, run.summary, Path(tmp), extra_sheets={
            "work_queue": run.work_queue, "causes": run.causes,
            "abandonment_by_step": run.steps, "priority_sensitivity": run.sensitivity})
        xlsx_bytes = paths["xlsx"].read_bytes()
    d2.download_button("Full results (Excel, all sheets)", xlsx_bytes, "p3_results.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
