# Decision Brief Generator

A lightweight Streamlit prototype for turning raw KPI data into:
- period-over-period metric changes
- three prioritized takeaways
- recommended business actions
- an AI-ready executive-brief prompt

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy publicly
1. Put `app.py`, `sample_data.csv`, and `requirements.txt` in a GitHub repository.
2. Connect the repository to Streamlit Community Cloud.
3. Choose `app.py` as the entry point and deploy.
4. Submit the resulting `streamlit.app` URL.

## Demo data
The included dataset is self-created dummy e-commerce KPI data, so no confidential information is used.

## Why this design
The prototype deliberately separates calculation from interpretation:
- Python computes KPI changes deterministically.
- Business rules prioritize potentially meaningful movements.
- The generated LLM prompt asks for three ranked takeaways, actions, and explicit uncertainty handling.

This makes the output auditable while still demonstrating how AI can turn analysis into decision-ready language.
