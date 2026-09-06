import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Decision Brief Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

GOOD_UP = {
    "revenue", "sales", "orders", "customers", "conversion_rate",
    "avg_order_value", "profit", "margin", "retention_rate"
}
BAD_UP = {
    "churn_rate", "refund_rate", "return_rate", "support_tickets",
    "cac", "cost", "costs", "complaints", "downtime"
}
MONEY_HINTS = ("revenue", "sales", "profit", "spend", "cost", "cac", "order_value", "aov")
RATE_HINTS = ("rate", "margin", "conversion", "churn", "retention", "refund", "return")

st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1280px;}
.hero {
    padding: 1.35rem 1.5rem;
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 18px;
    margin-bottom: 1rem;
}
.eyebrow {
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    opacity: .65;
}
.hero h1 {margin: .2rem 0 .25rem 0; font-size: 2.15rem;}
.hero p {margin: 0; opacity: .78;}
.signal-card {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 14px;
    padding: .85rem 1rem;
    min-height: 126px;
}
.signal-label {font-size: .8rem; opacity: .65; margin-bottom: .3rem;}
.signal-value {font-size: 1.15rem; font-weight: 700; margin-bottom: .25rem;}
.signal-copy {font-size: .9rem; line-height: 1.35; opacity: .86;}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.22);
    padding: .85rem 1rem;
    border-radius: 14px;
}
</style>
""", unsafe_allow_html=True)


def pretty(name):
    return name.replace("_", " ").strip().title()


def direction_for(kpi):
    k = kpi.lower()
    if k in GOOD_UP:
        return "up_good"
    if k in BAD_UP:
        return "up_bad"
    return "neutral"


def pct_change(current, previous):
    if pd.isna(current) or pd.isna(previous) or previous == 0:
        return np.nan
    return (current - previous) / abs(previous) * 100


def format_value(kpi, value):
    if pd.isna(value):
        return "n/a"
    k = kpi.lower()
    if any(h in k for h in MONEY_HINTS):
        return f"${value:,.0f}" if abs(value) >= 100 else f"${value:,.2f}"
    if any(h in k for h in RATE_HINTS):
        return f"{value:,.2f}%"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def signal_state(kpi, delta):
    if pd.isna(delta):
        return "neutral"
    d = direction_for(kpi)
    if d == "neutral":
        return "neutral"
    is_good = (d == "up_good" and delta > 0) or (d == "up_bad" and delta < 0)
    return "good" if is_good else "bad"


def signal_icon(state):
    return {"good": "🟢", "bad": "🔴", "neutral": "🔵"}.get(state, "⚪")


def anomaly_z(series):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 4:
        return np.nan
    hist = s.iloc[:-1]
    if len(hist) < 3:
        return np.nan
    std = hist.std(ddof=0)
    if std == 0 or pd.isna(std):
        return 0.0
    return (s.iloc[-1] - hist.mean()) / std


def priority_score(kpi, delta, z):
    magnitude = 0 if pd.isna(delta) else min(abs(delta) * 2.4, 55)
    anomaly = 0 if pd.isna(z) else min(abs(z) * 12, 30)
    risk_bonus = 12 if signal_state(kpi, delta) == "bad" else 0
    return int(round(min(100, magnitude + anomaly + risk_bonus)))


def priority_label(score):
    if score >= 65:
        return "High"
    if score >= 35:
        return "Medium"
    return "Watch"


def generate_action(kpi, delta):
    k = kpi.lower()
    if pd.isna(delta):
        return f"Validate the data quality for {pretty(kpi)} before making a decision."
    if k == "revenue" and delta < -5:
        return "Decompose revenue into traffic, conversion, order volume, and average order value before changing budget."
    if k == "conversion_rate" and delta < -5:
        return "Audit the funnel by channel and device, then review recent landing-page, pricing, and checkout changes."
    if k == "churn_rate" and delta > 5:
        return "Run a churn cohort analysis and inspect cancellation reasons before launching a broad retention campaign."
    if k == "ad_spend" and delta > 10:
        return "Review campaign-level ROAS and marginal efficiency before adding more media budget."
    if k == "support_tickets" and delta > 10:
        return "Cluster ticket topics and check whether one release, product area, or process is driving the spike."
    if k == "avg_order_value" and delta < -3:
        return "Test bundles, upsells, and merchandising changes to recover average order value."
    if abs(delta) >= 10:
        return f"Investigate the {abs(delta):.1f}% movement in {pretty(kpi)} by segment before taking a major action."
    return f"Monitor {pretty(kpi)} next period and segment the metric before making a structural change."


def build_pattern_scan(records):
    vals = {r["raw_kpi"]: r for r in records}
    patterns = []

    def delta(name):
        row = vals.get(name)
        return np.nan if row is None else row["DeltaPct"]

    rev, spend = delta("revenue"), delta("ad_spend")
    conv, tickets = delta("conversion_rate"), delta("support_tickets")
    churn = delta("churn_rate")
    orders, aov = delta("orders"), delta("avg_order_value")

    if pd.notna(rev) and pd.notna(spend) and rev < 0 and spend > 0:
        patterns.append({
            "name": "Efficiency leakage",
            "strength": "High",
            "evidence": f"Revenue changed {rev:+.1f}% while ad spend changed {spend:+.1f}%.",
            "hypothesis": "Marketing efficiency or traffic quality may have weakened.",
            "action": "Compare ROAS, conversion, and customer quality by channel before increasing spend."
        })
    if pd.notna(conv) and pd.notna(tickets) and conv < 0 and tickets > 0:
        patterns.append({
            "name": "Customer friction signal",
            "strength": "High",
            "evidence": f"Conversion changed {conv:+.1f}% while support tickets changed {tickets:+.1f}%.",
            "hypothesis": "A product, checkout, or service issue may be affecting purchase completion.",
            "action": "Review top ticket themes alongside funnel drop-off by device and channel."
        })
    if pd.notna(churn) and pd.notna(tickets) and churn > 0 and tickets > 0:
        patterns.append({
            "name": "Retention risk",
            "strength": "High",
            "evidence": f"Churn changed {churn:+.1f}% while support tickets changed {tickets:+.1f}%.",
            "hypothesis": "Customer experience issues may be contributing to retention pressure.",
            "action": "Link churn cohorts to recent support contacts and cancellation reasons."
        })
    if pd.notna(orders) and pd.notna(aov) and orders < 0 and abs(aov) < 3:
        patterns.append({
            "name": "Volume-led slowdown",
            "strength": "Medium",
            "evidence": f"Orders changed {orders:+.1f}% while average order value was relatively stable at {aov:+.1f}%.",
            "hypothesis": "The topline change is more likely volume-related than basket-size-related.",
            "action": "Prioritize acquisition and conversion diagnostics before discounting or changing pricing."
        })
    return patterns


def decision_now(result, patterns):
    if patterns:
        p = patterns[0]
        return p["action"], f"{p['name']} is the clearest cross-metric pattern in the latest period.", "High"
    lead = result.iloc[0]
    action = generate_action(lead["raw_kpi"], lead["DeltaPct"])
    confidence = "Medium" if lead["PriorityScore"] >= 35 else "Low"
    rationale = (
        f"{lead['KPI']} has the highest priority score ({lead['PriorityScore']}/100) "
        f"based on movement magnitude, historical unusualness, and business direction."
    )
    return action, rationale, confidence


def make_prompt(latest_label, previous_label, result, patterns):
    metric_rows = []
    for _, r in result.iterrows():
        metric_rows.append(
            f"- {r['KPI']}: current={r['CurrentFormatted']}, previous={r['PreviousFormatted']}, "
            f"change={r['Change']}, priority={r['Priority']}, anomaly_z={r['AnomalyText']}"
        )
    pattern_rows = "\n".join(
        f"- {p['name']}: evidence={p['evidence']} hypothesis={p['hypothesis']}"
        for p in patterns
    ) or "- No cross-metric pattern met the rule-based threshold."

    return f"""You are a senior business analyst writing for an executive audience.

Create a decision brief for {latest_label} versus {previous_label}.

KPI evidence:
{chr(10).join(metric_rows)}

Rule-based pattern scan:
{pattern_rows}

Instructions:
1. Write exactly 3 takeaways, ranked by business importance.
2. For each takeaway, label:
   - Evidence: only what the supplied metrics directly show.
   - Hypothesis: a plausible explanation, clearly marked as unverified.
   - Action: one concrete next step.
3. Do not invent causes, benchmarks, customer segments, or external context.
4. Prioritize cross-metric evidence over isolated percentage changes.
5. End with:
   - Decision now: one recommendation.
   - Confidence: High, Medium, or Low, with one sentence explaining why.
6. Keep the complete brief under 200 words.

Use plain business language and make trade-offs explicit.
"""


st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">AI decision intelligence prototype</div>
        <h1>Decision Brief Generator</h1>
        <p>From raw KPI data → prioritized signals → business action, with evidence and hypotheses kept separate.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload a CSV", type=["csv"])
    st.caption("No upload? The app uses a self-created dummy e-commerce dataset.")

if uploaded is None:
    df = pd.read_csv("sample_data.csv")
    source_label = "Demo dataset"
else:
    df = pd.read_csv(uploaded)
    source_label = uploaded.name

date_candidates = [c for c in df.columns if any(x in c.lower() for x in ["date", "month", "week", "period"])]
default_date_idx = df.columns.get_loc(date_candidates[0]) if date_candidates else 0

with st.sidebar:
    date_col = st.selectbox("Time / period column", df.columns, index=default_date_idx)

df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
df = df.dropna(subset=[date_col]).sort_values(date_col)

numeric_cols = [c for c in df.columns if c != date_col and pd.api.types.is_numeric_dtype(df[c])]
with st.sidebar:
    selected = st.multiselect("KPIs to analyze", numeric_cols, default=numeric_cols[:8])
    st.divider()
    st.markdown(f"**Source:** {source_label}")
    st.markdown(f"**Rows:** {len(df)}")
    st.markdown(f"**Periods:** {df[date_col].nunique()}")

if len(df) < 2 or not selected:
    st.warning("The app needs at least two time periods and one numeric KPI.")
    st.stop()

latest = df.iloc[-1]
previous = df.iloc[-2]
latest_label = latest[date_col].strftime("%b %Y")
previous_label = previous[date_col].strftime("%b %Y")

records = []
for kpi in selected:
    cur = latest[kpi]
    prev = previous[kpi]
    delta = pct_change(cur, prev)
    z = anomaly_z(df[kpi])
    score = priority_score(kpi, delta, z)
    state = signal_state(kpi, delta)
    records.append({
        "KPI": pretty(kpi),
        "raw_kpi": kpi,
        "Current": cur,
        "Previous": prev,
        "CurrentFormatted": format_value(kpi, cur),
        "PreviousFormatted": format_value(kpi, prev),
        "DeltaPct": delta,
        "Change": "n/a" if pd.isna(delta) else f"{delta:+.1f}%",
        "State": state,
        "Status": signal_icon(state),
        "AnomalyZ": z,
        "AnomalyText": "n/a" if pd.isna(z) else f"{z:+.2f}",
        "PriorityScore": score,
        "Priority": priority_label(score),
    })

result = pd.DataFrame(records).sort_values(["PriorityScore", "DeltaPct"], ascending=[False, False])
patterns = build_pattern_scan(records)
action, rationale, confidence = decision_now(result, patterns)

tabs = st.tabs(["Executive brief", "Trend explorer", "AI prompt", "Method"])

with tabs[0]:
    st.caption(f"Comparing **{latest_label}** with **{previous_label}** · {len(df)} periods available")

    top = result.head(4)
    cols = st.columns(4)
    for col, (_, r) in zip(cols, top.iterrows()):
        delta_text = None if pd.isna(r["DeltaPct"]) else f"{r['DeltaPct']:+.1f}% vs prior"
        col.metric(
            label=f"{r['Status']} {r['KPI']}",
            value=r["CurrentFormatted"],
            delta=delta_text,
            delta_color="off",
        )
        col.caption(f"{r['Priority']} priority · score {r['PriorityScore']}/100")

    st.markdown("### Decision now")
    c1, c2 = st.columns([2.2, 1])
    with c1:
        st.success(action)
        st.caption(rationale)
    with c2:
        st.metric("Decision confidence", confidence)
        st.caption("Based on data depth and whether multiple KPIs support the same signal.")

    st.markdown("### Three key takeaways")
    for i, (_, r) in enumerate(result.head(3).iterrows(), start=1):
        if pd.notna(r["DeltaPct"]):
            verb = "increased" if r["DeltaPct"] > 0 else "decreased"
            evidence = (
                f"{r['KPI']} {verb} by {abs(r['DeltaPct']):.1f}%, "
                f"from {r['PreviousFormatted']} to {r['CurrentFormatted']}."
            )
        else:
            evidence = f"{r['KPI']} could not be compared reliably with the prior period."

        if pd.notna(r["AnomalyZ"]) and abs(r["AnomalyZ"]) >= 2:
            unusual = f" This is unusual versus prior history (z={r['AnomalyZ']:+.2f})."
        else:
            unusual = ""

        st.markdown(f"**{i}. {r['Status']} {r['KPI']} · {r['Priority']} priority**")
        st.write(f"**Evidence:** {evidence}{unusual}")
        st.write(f"**Action:** {generate_action(r['raw_kpi'], r['DeltaPct'])}")

    st.markdown("### Cross-metric pattern scan")
    if patterns:
        pcols = st.columns(min(3, len(patterns)))
        for col, p in zip(pcols, patterns[:3]):
            with col:
                st.markdown(
                    f"""
                    <div class="signal-card">
                        <div class="signal-label">{p['strength']} confidence pattern</div>
                        <div class="signal-value">{p['name']}</div>
                        <div class="signal-copy">{p['evidence']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.caption(f"Hypothesis: {p['hypothesis']}")
    else:
        st.info("No cross-metric rule fired. The app is prioritizing individual KPI movements instead of forcing a narrative.")

    with st.expander("Full priority table"):
        display = result[[
            "KPI", "CurrentFormatted", "PreviousFormatted", "Change",
            "Priority", "PriorityScore", "AnomalyText"
        ]].rename(columns={
            "CurrentFormatted": "Current",
            "PreviousFormatted": "Previous",
            "PriorityScore": "Score",
            "AnomalyText": "Anomaly z",
        })
        st.dataframe(display, use_container_width=True, hide_index=True)

with tabs[1]:
    st.markdown("### Trend explorer")
    trend_kpi = st.selectbox("Choose a KPI", selected, format_func=pretty, key="trend_kpi")
    trend = df[[date_col, trend_kpi]].dropna().set_index(date_col)

    st.line_chart(trend, use_container_width=True)

    latest_delta = result.loc[result["raw_kpi"] == trend_kpi, "DeltaPct"].iloc[0]
    latest_z = result.loc[result["raw_kpi"] == trend_kpi, "AnomalyZ"].iloc[0]
    t1, t2, t3 = st.columns(3)
    t1.metric("Latest value", format_value(trend_kpi, trend.iloc[-1, 0]))
    t2.metric("Period change", "n/a" if pd.isna(latest_delta) else f"{latest_delta:+.1f}%")
    t3.metric("Historical anomaly", "n/a" if pd.isna(latest_z) else f"{latest_z:+.2f} z")

    if pd.notna(latest_z) and abs(latest_z) >= 2:
        st.warning("The latest value is more than two standard deviations from its prior-period mean. Treat it as a diagnostic flag, not proof of a cause.")
    else:
        st.info("The latest value is not an extreme historical outlier under this simple z-score check.")

    st.markdown("#### Raw trend data")
    st.dataframe(
        df[[date_col, trend_kpi]].tail(12).rename(columns={trend_kpi: pretty(trend_kpi)}),
        use_container_width=True,
        hide_index=True,
    )

with tabs[2]:
    st.markdown("### AI-ready executive prompt")
    st.write(
        "The model is asked to interpret calculated evidence—not calculate the KPIs itself. "
        "That reduces arithmetic errors and makes unsupported assumptions easier to spot."
    )
    prompt = make_prompt(latest_label, previous_label, result, patterns)
    st.code(prompt, language="text")
    st.download_button(
        "Download prompt",
        data=prompt,
        file_name="decision_brief_prompt.txt",
        mime="text/plain",
        use_container_width=False,
    )

with tabs[3]:
    st.markdown("### How the prototype thinks")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("**1 · Calculate**")
        st.write("Period-over-period changes are computed in Python, not delegated to an LLM.")
    with m2:
        st.markdown("**2 · Prioritize**")
        st.write("A transparent 0–100 score combines change magnitude, historical unusualness, and whether movement is directionally good or bad.")
    with m3:
        st.markdown("**3 · Interpret**")
        st.write("Cross-metric rules identify patterns, then the generated AI prompt separates evidence, hypotheses, actions, and confidence.")

    st.markdown("#### Priority score")
    st.code(
        "priority = change magnitude (max 55) + anomaly strength (max 30) + adverse-direction bonus (12)",
        language="text",
    )

    st.markdown("#### Guardrails")
    st.markdown(
        """
- **No invented causality:** patterns produce hypotheses, not claims.
- **Auditability:** every recommendation is traceable to supplied metrics or an explicit rule.
- **Human judgment remains:** anomaly scores flag unusual values; they do not prove root cause.
- **No confidential data:** the included dataset is self-created dummy data.
        """
    )

    with st.expander("Preview source data"):
        st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "Prototype purpose: demonstrate how AI can sit on top of reliable calculations to produce clearer, faster business decisions."
)
