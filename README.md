# Decision Brief Generator

A lightweight Streamlit prototype for turning raw KPI data into:
- period-over-period metric changes
- three prioritized takeaways
- recommended business actions
- an AI-ready executive-brief prompt

## Submission Summary — 100 words

I built a lightweight Decision Brief Generator that turns raw KPI data into a concise, action-oriented business summary. The prototype accepts a CSV, compares the latest period with the previous one, ranks the largest metric movements, and produces three key takeaways plus recommended actions. I deliberately separated calculation from interpretation: Python handles deterministic metric changes, while an AI-ready prompt converts those facts into executive language and explicitly avoids inventing unsupported causes. I used a self-created e-commerce dataset so no confidential information is involved. The design is simple, auditable, reusable across business datasets, and easy to deploy as a Streamlit app.

## Demo Dataset

The included `sample_data.csv` is a self-created dummy e-commerce KPI dataset, so no confidential information is used.

Public dataset file: https://github.com/theyoumnahassan/challenge1/blob/main/sample_data.csv

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy publicly with Streamlit

1. Connect this GitHub repository to Streamlit Community Cloud.
2. Choose `app.py` as the entry point.
3. Deploy and copy the resulting `streamlit.app` URL.
4. Submit the app URL, this GitHub repository, and the summary above.

## Why this design

The prototype deliberately separates calculation from interpretation:
- Python computes KPI changes deterministically.
- Business rules prioritize potentially meaningful movements.
- The generated LLM prompt asks for three ranked takeaways, actions, and explicit uncertainty handling.

This makes the output auditable while still demonstrating how AI can turn analysis into decision-ready language.
