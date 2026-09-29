# LuLu UAE Sales Dashboard (teaching demo)

A Streamlit dashboard on **synthetic** LuLu-style sales data: 1,000 transactions across
6 categories and all 7 emirates, Oct 2025 to Sep 2026. These are not real LuLu figures.

## Files

| File | What it is |
|---|---|
| `app.py` | The dashboard |
| `lulu_sales_data.csv` | The dataset (1,000 rows, 26 columns) |
| `generate_data.py` | Creates the dataset. Change `N_ROWS` or `SEED` and re-run for new data |
| `requirements.txt` | Python packages Streamlit Cloud installs |

## Run on your computer

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push all four files to the root of a GitHub repository.
2. Go to share.streamlit.io, choose **Create app**, and pick the repository.
3. Set **Main file path** to `app.py` and deploy.

## How the filters work

- **Global filters** (date range, emirates) at the top change every chart.
- Each chart's **Filters** button holds local filters that change only that chart,
  on top of the global filters.
- Every chart is an `@st.fragment`, so changing a local filter redraws only that chart.
