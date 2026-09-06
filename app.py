import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Decision Brief Generator", page_icon="📊", layout="wide")

GOOD_UP = {
    "revenue", "sales", "orders", "customers", "conversion_rate",
    "avg_order_value", "profit", "margin", "retention_rate"
}
BAD_UP = {
    "churn_rate", "refund_rate", "return_rate", "support_tickets",
    "cac", "cost", "costs", "complaints", "downtime"
}

def pretty(name):
    return name.replace("_", " ").title()

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

def status(kpi, delta):
    if pd.isna(delta):
        return "⚪"
    d = direction_for(kpi)
    if d == "neutral":
        return "🔵"
    positive = delta > 0
    good = (d == "up_good" and positive) or (d == "up_bad" and not positive)
    return "🟢" if good else "🔴"

def generate_action(kpi, current, previous, delta):
    k = kpi.lower()
    abs_delta = abs(delta) if not pd.isna(delta) else 0

    if k == "revenue" and delta < -5:
        return "Investigate the revenue decline by decomposing it into traffic, conversion, order volume, and average order value."
    if k == "conversion_rate" and delta < -5:
        return "Audit the conversion funnel by channel/device and review recent landing-page, pricing, or checkout changes."
    if k == "churn_rate" and delta > 5:
        return "Run a churn cohort analysis and contact recent churned customers to identify the leading retention drivers."
    if k == "ad_spend" and delta > 10:
        return "Review campaign-level ROAS and pause or reduce spend on channels where incremental spend is not producing revenue."
    if k == "support_tickets" and delta > 10:
        return "Cluster support tickets by issue type and identify whether one product, release, or process is driving the spike."
    if k == "avg_order_value" and delta < -3:
        return "Test bundles, upsells, and merchandising changes to recover average order value."
    if abs_delta >= 10:
        return f"Investigate the {abs_delta:.1f}% movement in {pretty(kpi)} and validate whether it is driven by mix, seasonality, or a recent operational change."
    return f"Monitor {pretty(kpi)} next period and segment it by the most relevant business dimension before taking a major action."

def make_prompt(latest_label, previous_label, brief_df):
    rows = []
    for _, r in brief_df.iterrows():
        rows.append(
            f"- {r['KPI']}: current={r['Current']}, previous={r['Previous']}, change={r['Change']}"
        )
    metrics = "\n".join(rows)
    return f"""You are a senior business analyst. Turn the KPI changes below into an executive decision brief.

Period compared:
- Current: {latest_label}
- Previous: {previous_label}

Metrics:
{metrics}

Instructions:
1. Write exactly 3 key takeaways, ranked by business importance.
2. Explain the likely business implication of each takeaway without inventing causes.
3. Give 1 recommended action for each takeaway.
4. Separate observation from hypothesis.
5. Flag any conclusion that cannot be supported by the available data.
6. End with a single "Decision now" recommendation.

Keep the full response under 180 words. Use clear business language, not technical jargon.
"""

st.title("📊 Decision Brief Generator")
st.caption("Turn a raw KPI file into an executive summary, prioritized insights, and recommended actions.")

uploaded = st.file_uploader("Upload a CSV", type=["csv"])
if uploaded is None:
    df = pd.read_csv("sample_data.csv")
    st.info("Using the included dummy e-commerce dataset. Upload your own CSV to replace it.")
else:
    df = pd.read_csv(uploaded)

with st.expander("Preview raw data", expanded=False):
    st.dataframe(df, use_container_width=True)

date_candidates = [c for c in df.columns if any(x in c.lower() for x in ["date", "month", "week", "period"])]
date_col = st.selectbox("Time / period column", df.columns, index=df.columns.get_loc(date_candidates[0]) if date_candidates else 0)

df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
df = df.dropna(subset=[date_col]).sort_values(date_col)

numeric_cols = [c for c in df.columns if c != date_col and pd.api.types.is_numeric_dtype(df[c])]
selected = st.multiselect("KPIs to analyze", numeric_cols, default=numeric_cols[:7])

if len(df) < 2 or not selected:
    st.warning("The app needs at least two time periods and one numeric KPI.")
    st.stop()

latest = df.iloc[-1]
previous = df.iloc[-2]
latest_label = latest[date_col].strftime("%Y-%m-%d")
previous_label = previous[date_col].strftime("%Y-%m-%d")

records = []
for kpi in selected:
    cur = latest[kpi]
    prev = previous[kpi]
    delta = pct_change(cur, prev)
    records.append({
        "KPI": pretty(kpi),
        "raw_kpi": kpi,
        "Current": cur,
        "Previous": prev,
        "DeltaPct": delta,
        "Status": status(kpi, delta),
        "ImpactScore": abs(delta) if not pd.isna(delta) else 0
    })

result = pd.DataFrame(records).sort_values("ImpactScore", ascending=False)

st.subheader(f"Decision brief: {latest_label} vs {previous_label}")

top = result.head(3).copy()
cols = st.columns(3)
for col, (_, r) in zip(cols, top.iterrows()):
    delta_text = "n/a" if pd.isna(r["DeltaPct"]) else f"{r['DeltaPct']:+.1f}%"
    col.metric(r["KPI"], f"{r['Current']:,.2f}", delta_text)
    col.caption(f"{r['Status']} Priority signal")

st.markdown("### Three key takeaways")
for i, (_, r) in enumerate(top.iterrows(), start=1):
    change = r["DeltaPct"]
    if pd.isna(change):
        sentence = f"{r['KPI']} cannot be compared reliably with the prior period."
    else:
        verb = "increased" if change > 0 else "decreased"
        sentence = f"{r['KPI']} {verb} by **{abs(change):.1f}%**, from {r['Previous']:,.2f} to {r['Current']:,.2f}."
    st.markdown(f"**{i}. {r['Status']} {sentence}**")
    st.write(generate_action(r["raw_kpi"], r["Current"], r["Previous"], change))

st.markdown("### Recommended business action")
vals = {r["raw_kpi"]: r for _, r in result.iterrows()}
recommendation = None
if "revenue" in vals and "ad_spend" in vals:
    rev = vals["revenue"]["DeltaPct"]
    spend = vals["ad_spend"]["DeltaPct"]
    if pd.notna(rev) and pd.notna(spend) and rev < 0 and spend > 0:
        recommendation = (
            "Revenue fell while ad spend increased. Prioritize a **campaign-level efficiency review** "
            "before adding more budget: compare ROAS, conversion rate, and customer quality by channel."
        )
if recommendation is None and "churn_rate" in vals and vals["churn_rate"]["DeltaPct"] > 5:
    recommendation = (
        "Churn is the most urgent controllable risk. Prioritize a **retention diagnosis** by customer cohort, "
        "plan, acquisition source, and cancellation reason."
    )
if recommendation is None:
    lead = top.iloc[0]
    recommendation = generate_action(
        lead["raw_kpi"], lead["Current"], lead["Previous"], lead["DeltaPct"]
    )

st.success(recommendation)

brief_export = result[["KPI", "Current", "Previous", "DeltaPct"]].copy()
brief_export["Change"] = brief_export["DeltaPct"].map(lambda x: "n/a" if pd.isna(x) else f"{x:+.1f}%")
brief_export = brief_export.drop(columns=["DeltaPct"])

st.markdown("### AI-ready prompt")
prompt = make_prompt(latest_label, previous_label, brief_export)
st.code(prompt, language="text")
st.download_button(
    "Download prompt",
    data=prompt,
    file_name="decision_brief_prompt.txt",
    mime="text/plain"
)

st.caption(
    "Design note: the prototype separates calculation from interpretation. "
    "Python computes KPI deltas; the prompt constrains an LLM to prioritize evidence, avoid invented causes, and recommend actions."
)
