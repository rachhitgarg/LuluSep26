"""
LuLu UAE Sales Dashboard  (app.py)
==================================
A Streamlit dashboard built on SYNTHETIC (made-up) LuLu-style sales data.

How the filters work
--------------------
1. GLOBAL filters (date range + emirates) sit in the box at the top.
   They change EVERY chart on the page.
2. LOCAL filters sit behind the "Filters" button on each chart.
   They change ONLY that one chart, on top of the global filters.

Why each chart is wrapped in @st.fragment
-----------------------------------------
Normally, touching ANY widget makes Streamlit re-run the whole script.
A "fragment" is a piece of the page that can re-run on its own.
So when you change a chart's local filter, only that chart is redrawn.

Run it on your own computer:
    pip install -r requirements.txt
    streamlit run app.py
"""

from datetime import timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# =============================================================================
# 1. PAGE SETUP  (must be the first Streamlit command in the file)
# =============================================================================
st.set_page_config(page_title="LuLu UAE Sales Dashboard", page_icon="🛒", layout="wide")

# =============================================================================
# 2. SETTINGS USED ACROSS THE APP
# =============================================================================
# The CSV sits in the same folder as this file. Building the path from
# __file__ means it is found both on your laptop and on Streamlit Cloud.
DATA_FILE = Path(__file__).parent / "lulu_sales_data.csv"

CATEGORIES = ["Fresh", "Grocery", "Fashion", "Home Decor", "Electronics", "Furniture"]
EMIRATES = ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Umm Al Quwain"]
AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]
FESTIVE_SEASONS = ["White Friday", "DSF", "Ramadan", "Back to School"]

# Each category always gets the SAME colour in every chart, so viewers
# learn the colours once and can read every chart faster.
CATEGORY_COLORS = {
    "Fresh": "#2E9E5B",
    "Grocery": "#E0A526",
    "Fashion": "#C2408A",
    "Home Decor": "#2A9D8F",
    "Electronics": "#3A6FD8",
    "Furniture": "#8C5A3C",
}
OTHER_COLORS = ["#3A6FD8", "#2A9D8F", "#E0A526", "#C2408A"]   # for charts not split by category
CHART_HEIGHT = 380                                          # same height for every chart

# The measures a user can choose, and the column each one comes from.
METRIC_COLUMNS = {
    "Net sales (AED)": "Net_Sales_AED",
    "Profit (AED)": "Profit_AED",
    "Units sold": "Units_Sold",
    "Transactions": "Transaction_ID",
}


# =============================================================================
# 3. LOAD THE DATA
# =============================================================================
# @st.cache_data = "read the file once, then remember it".
# Without it, the CSV would be re-read every time anyone clicks anything.
#
# ➡️ LIVE VERSION (later): change this to @st.cache_data(ttl=5)
#    so Streamlit re-reads the file every 5 seconds and picks up new rows.
@st.cache_data
def load_data():
    return pd.read_csv(DATA_FILE, parse_dates=["Timestamp", "Date"])


# =============================================================================
# 4. HELPER FUNCTIONS  (small reusable pieces used by the charts)
# =============================================================================
def aed(value):
    """Turn a number into a short money label, e.g. 1234567 -> 'AED 1.23M'."""
    if abs(value) >= 1_000_000:
        return f"AED {value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"AED {value / 1_000:.1f}K"
    return f"AED {value:,.0f}"


def filter_rows(data, start, end, emirates):
    """Keep only rows between two dates AND inside the chosen emirates."""
    in_dates = data["Date"].between(pd.Timestamp(start), pd.Timestamp(end))
    in_emirates = data["Emirate"].isin(emirates)
    return data[in_dates & in_emirates]


def chosen_emirates():
    """Emirates picked in the global filter. Picking nothing means 'all emirates'."""
    return st.session_state["global_emirates"] or EMIRATES


def get_global_data():
    """Every chart starts here: the full data with the GLOBAL filters applied.

    The global widgets save their values in st.session_state (Streamlit's
    memory), so any chart can read them, even when only that chart re-runs.
    """
    start, end = st.session_state["global_dates"]
    return filter_rows(load_data(), start, end, chosen_emirates())


def emirates_in(data):
    """Emirates that appear in the data, in our standard order."""
    present = set(data["Emirate"])
    return [e for e in EMIRATES if e in present]


def summarise(data, group_by, metric):
    """Group the data (e.g. by Category) and calculate one measure per group.

    Most measures are simple totals. Two need special maths:
      * Transactions      -> count the rows
      * Profit margin (%) -> total profit / total net sales x 100
      * Average rating    -> the average (mean) of the ratings
    """
    groups = data.groupby(group_by)
    if metric == "Transactions":
        result = groups["Transaction_ID"].count()
    elif metric == "Profit margin (%)":
        result = groups["Profit_AED"].sum() / groups["Net_Sales_AED"].sum() * 100
    elif metric == "Average rating (1-5)":
        result = groups["Customer_Rating"].mean()
    else:
        result = groups[METRIC_COLUMNS[metric]].sum()
    return result.rename(metric).reset_index()


def card_header(title, wide=False):
    """Draw a chart title with a 'Filters' button on its right.

    Returns the pop-over (the little menu that opens when you click the
    button). Anything created inside  `with card_header(...):`  goes in it.
    """
    title_col, button_col = st.columns([6, 1] if wide else [3, 1], vertical_alignment="center")
    title_col.markdown(f"#### {title}")
    return button_col.popover("Filters", icon=":material/tune:", width="stretch")


def local_select(label, options, key):
    """A dropdown that never gets 'stuck' on an option that has disappeared.

    Example: you pick 'Ajman' in a chart, then remove Ajman in the global
    filter. The old choice is no longer valid, so we reset it to the first
    option ('All ...') before drawing the dropdown.
    """
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    return st.selectbox(label, options, key=key)


def show_active_filters(*choices):
    """The filters hide inside a pop-over, so print the current choices under the title."""
    st.caption("Showing: " + ", ".join(choices))


def no_data_message():
    st.info("No transactions match these filters. Widen them using the Filters button.")


def style(fig):
    """Give every Plotly chart the same size, margins and legend position."""
    fig.update_layout(
        height=CHART_HEIGHT,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
    )
    return fig


# =============================================================================
# 5. THE CHARTS
# Each function below draws one card: title + Filters button + chart.
# @st.fragment lets each card re-run on its own when its local filters change.
#
# ➡️ LIVE VERSION (later): change @st.fragment to @st.fragment(run_every="5s")
#    and the card will refresh itself every 5 seconds.
# =============================================================================

# ----------------------------------------------------------------- KPI strip
def calc_kpis(data):
    """The five headline numbers for a slice of data."""
    net = data["Net_Sales_AED"].sum()
    count = len(data)
    return {
        "net": net,
        "transactions": count,
        "units": data["Units_Sold"].sum(),
        "avg_value": net / count if count else 0,
        "margin": data["Profit_AED"].sum() / net * 100 if net else 0,
    }


def pct_change(now, before):
    """'+12.3%' style change label, or None when there is nothing to compare with."""
    if before is None or before == 0:
        return None
    return f"{(now - before) / abs(before) * 100:+.1f}%"


@st.fragment
def kpi_row():
    data = get_global_data()

    # Compare with the period just before, of the same length.
    # (With the full year selected there is no earlier data, so no arrows.)
    start, end = st.session_state["global_dates"]
    period_days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)
    previous = filter_rows(load_data(), prev_start, prev_end, chosen_emirates())

    now = calc_kpis(data)
    before = calc_kpis(previous) if not previous.empty else {k: None for k in now}

    # Month-by-month values for the small sparkline inside each KPI box
    by_month = data.groupby(data["Date"].dt.to_period("M"))
    monthly_net = by_month["Net_Sales_AED"].sum()
    monthly_count = by_month["Transaction_ID"].count()
    sparklines = {
        "net": monthly_net.round(0).tolist(),
        "transactions": monthly_count.tolist(),
        "units": by_month["Units_Sold"].sum().tolist(),
        "avg_value": (monthly_net / monthly_count).round(1).tolist(),
        "margin": (by_month["Profit_AED"].sum() / monthly_net * 100).round(1).tolist(),
    }

    margin_delta = None if before["margin"] is None else f"{now['margin'] - before['margin']:+.1f} pts"
    compare_help = "Arrow = change vs the previous period of the same length (shown when that period is in the data)."

    boxes = [
        ("Net sales", aed(now["net"]), pct_change(now["net"], before["net"]), "net"),
        ("Transactions", f"{now['transactions']:,}", pct_change(now["transactions"], before["transactions"]), "transactions"),
        ("Units sold", f"{now['units']:,}", pct_change(now["units"], before["units"]), "units"),
        ("Avg. transaction value", aed(now["avg_value"]), pct_change(now["avg_value"], before["avg_value"]), "avg_value"),
        ("Profit margin", f"{now['margin']:.1f}%", margin_delta, "margin"),
    ]
    for column, (label, value, delta, spark_key) in zip(st.columns(5), boxes):
        column.metric(label, value, delta, border=True, help=compare_help,
                      chart_data=sparklines[spark_key], chart_type="area")


# --------------------------------------------------------- Sales by category
@st.fragment
def sales_by_category_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Sales by category"):
            emirate = local_select("Emirate", ["All emirates"] + emirates_in(data), key="cat_emirate")
            metric = st.radio("Measure", list(METRIC_COLUMNS), key="cat_metric")

        if emirate != "All emirates":
            data = data[data["Emirate"] == emirate]
        show_active_filters(emirate, metric)
        if data.empty:
            return no_data_message()

        summary = summarise(data, "Category", metric)
        fig = px.bar(summary, x=metric, y="Category", orientation="h", text_auto=".3s",
                     color="Category", color_discrete_map=CATEGORY_COLORS)
        fig.update_layout(showlegend=False, yaxis_title=None)
        fig.update_yaxes(categoryorder="total ascending")   # biggest bar at the top
        st.plotly_chart(style(fig), key="chart_category")


# ------------------------------------------------- Emirate x Category heatmap
@st.fragment
def emirate_heatmap_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Emirate × category heatmap"):
            metric = st.radio("Measure", ["Net sales (AED)", "Profit (AED)", "Profit margin (%)", "Transactions"],
                              key="heat_metric")
            channel = st.selectbox("Sales channel", ["All channels", "In-store", "Online", "Click & Collect"],
                                   key="heat_channel")

        if channel != "All channels":
            data = data[data["Sales_Channel"] == channel]
        show_active_filters(metric, channel)
        if data.empty:
            return no_data_message()

        # Turn the long table into a grid: one row per emirate, one column per category
        grid = (summarise(data, ["Emirate", "Category"], metric)
                .pivot(index="Emirate", columns="Category", values=metric)
                .reindex(index=emirates_in(data), columns=CATEGORIES))

        is_margin = metric == "Profit margin (%)"
        if not is_margin:
            grid = grid.fillna(0)   # no sales = 0 (a margin with no sales is left blank)

        fig = px.imshow(
            grid, aspect="auto",
            text_auto=".1f" if is_margin else ".3s",
            # Margin can be negative, so use red-yellow-green centred on 0
            color_continuous_scale="RdYlGn" if is_margin else "Greens",
            color_continuous_midpoint=0 if is_margin else None,
            labels=dict(x="", y="", color=""),
        )
        st.plotly_chart(style(fig), key="chart_heatmap")


# ------------------------------------------------------------ Sales over time
@st.fragment
def trend_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Sales over time", wide=True):
            chosen = st.multiselect("Categories", CATEGORIES, placeholder="All categories", key="trend_categories")
            grain = st.segmented_control("Group dates by", ["Daily", "Weekly", "Monthly"],
                                         default="Monthly", required=True, key="trend_grain")
            metric = st.radio("Measure", ["Net sales (AED)", "Profit (AED)", "Units sold", "Transactions"],
                              key="trend_metric")
            split = st.toggle("One line per category", value=True, key="trend_split")
            show_seasons = st.toggle("Shade festive seasons", value=True, key="trend_seasons")

        if chosen:
            data = data[data["Category"].isin(chosen)]
        show_active_filters(", ".join(chosen) if chosen else "All categories", grain, metric)
        if data.empty:
            return no_data_message()

        # Put every date into a bucket: its day, its week or its month
        freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[grain]
        data = data.assign(Period=data["Date"].dt.to_period(freq).dt.start_time)

        summary = summarise(data, ["Period", "Category"] if split else "Period", metric)
        fig = px.line(summary, x="Period", y=metric, markers=grain != "Daily",
                      color="Category" if split else None, category_orders={"Category": CATEGORIES},
                      color_discrete_map=CATEGORY_COLORS, color_discrete_sequence=["#34495E"])
        fig.update_layout(xaxis_title=None)

        if show_seasons:
            # Find each season's first and last day from the Promotion column
            everything = load_data()
            first_shown, last_shown = data["Date"].min(), data["Date"].max()
            for season in FESTIVE_SEASONS:
                days = everything.loc[everything["Promotion"] == season, "Date"]
                if days.max() >= first_shown and days.min() <= last_shown:   # only if it's in view
                    fig.add_vrect(x0=days.min(), x1=days.max(), fillcolor="#E0A526", opacity=0.12,
                                  line_width=0, annotation_text=season, annotation_position="top left",
                                  annotation_font_size=11)

        st.plotly_chart(style(fig), key="chart_trend")


# --------------------------------------------------- Channel / payment mix
@st.fragment
def mix_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("How customers buy and pay"):
            view = st.radio("Break down by", ["Sales channel", "Payment method"], key="mix_view")
            category = st.selectbox("Category", ["All categories"] + CATEGORIES, key="mix_category")
            metric = st.radio("Measure", ["Net sales (AED)", "Transactions"], key="mix_metric")

        if category != "All categories":
            data = data[data["Category"] == category]
        show_active_filters(view, category, metric)
        if data.empty:
            return no_data_message()

        column = "Sales_Channel" if view == "Sales channel" else "Payment_Method"
        summary = summarise(data, column, metric)
        fig = px.pie(summary, names=column, values=metric, hole=0.55,
                     color_discrete_sequence=OTHER_COLORS)
        fig.update_traces(textinfo="percent", sort=True)
        st.plotly_chart(style(fig), key="chart_mix")


# ------------------------------------------------------ Promotion impact
@st.fragment
def promotion_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Do deeper discounts cost margin?"):
            category = st.selectbox("Category", ["All categories"] + CATEGORIES, key="promo_category")
            emirate = local_select("Emirate", ["All emirates"] + emirates_in(data), key="promo_emirate")

        if category != "All categories":
            data = data[data["Category"] == category]
        if emirate != "All emirates":
            data = data[data["Emirate"] == emirate]
        show_active_filters(category, emirate)
        if data.empty:
            return no_data_message()

        groups = data.groupby("Promotion")
        summary = pd.DataFrame({
            "Avg. discount (%)": groups["Discount_Pct"].mean(),
            "Profit margin (%)": groups["Profit_AED"].sum() / groups["Net_Sales_AED"].sum() * 100,
            "Transactions": groups["Transaction_ID"].count(),
        }).sort_values("Avg. discount (%)").reset_index()

        # Show how many transactions sit behind each bar (n=...). Few transactions
        # = a less reliable bar, and it is honest to show that.
        summary["Promotion"] = summary["Promotion"] + "<br>(n=" + summary["Transactions"].astype(str) + ")"

        # Reshape to 'long' format so Plotly can draw two bars side by side
        long = summary.melt(id_vars="Promotion", value_vars=["Avg. discount (%)", "Profit margin (%)"],
                            var_name="Measure", value_name="Percent")
        fig = px.bar(long, x="Promotion", y="Percent", color="Measure", barmode="group", text_auto=".1f",
                     color_discrete_map={"Avg. discount (%)": "#E0A526", "Profit margin (%)": "#2E9E5B"})
        fig.update_layout(xaxis_title=None, yaxis_title="%")
        st.plotly_chart(style(fig), key="chart_promo")


# ------------------------------------------------------ Customer profile
@st.fragment
def customer_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Who is buying"):
            category = st.selectbox("Category", ["All categories"] + CATEGORIES, key="cust_category")
            loyalty = st.radio("Customers", ["All customers", "Loyalty members", "Non-members"], key="cust_loyalty")
            metric = st.radio("Measure", ["Net sales (AED)", "Transactions", "Average rating (1-5)"],
                              key="cust_metric")

        if category != "All categories":
            data = data[data["Category"] == category]
        if loyalty != "All customers":
            data = data[data["Loyalty_Member"] == ("Yes" if loyalty == "Loyalty members" else "No")]
        show_active_filters(category, loyalty, metric)
        if data.empty:
            return no_data_message()

        summary = summarise(data, ["Age_Group", "Gender"], metric)
        fig = px.bar(summary, x="Age_Group", y=metric, color="Gender", barmode="group",
                     text_auto=".2f" if metric.startswith("Average") else ".3s",
                     category_orders={"Age_Group": AGE_GROUPS},
                     color_discrete_map={"Female": "#4C5B7A", "Male": "#A3B4CC"},
                     labels={"Age_Group": "Age group"})
        st.plotly_chart(style(fig), key="chart_customers")


# ------------------------------------------------- Top sub-categories table
@st.fragment
def top_products_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Top sub-categories"):
            chosen = st.multiselect("Categories", CATEGORIES, placeholder="All categories", key="top_categories")
            sort_by = st.selectbox("Rank by", ["Net sales (AED)", "Profit (AED)", "Units sold",
                                               "Transactions", "Profit margin (%)"], key="top_sort")
            top_n = st.slider("How many to show", 5, 30, 10, key="top_n")

        if chosen:
            data = data[data["Category"].isin(chosen)]
        show_active_filters(", ".join(chosen) if chosen else "All categories", f"top {top_n} by {sort_by}")
        if data.empty:
            return no_data_message()

        groups = data.groupby(["Sub_Category", "Category"])
        table = pd.DataFrame({
            "Net sales (AED)": groups["Net_Sales_AED"].sum(),
            "Profit (AED)": groups["Profit_AED"].sum(),
            "Units sold": groups["Units_Sold"].sum(),
            "Transactions": groups["Transaction_ID"].count(),
        })
        table["Profit margin (%)"] = table["Profit (AED)"] / table["Net sales (AED)"] * 100
        table = table.sort_values(sort_by, ascending=False).head(top_n).reset_index()

        st.dataframe(
            table, hide_index=True, height=CHART_HEIGHT,
            column_config={
                "Sub_Category": st.column_config.TextColumn("Sub-category", pinned=True),
                "Category": st.column_config.TextColumn(width="small"),
                # A bar inside the cell makes the biggest sellers easy to spot
                "Net sales (AED)": st.column_config.ProgressColumn(
                    "Net sales", format="compact", color="#2E9E5B", width="small",
                    min_value=0, max_value=float(table["Net sales (AED)"].max())),
                "Profit (AED)": st.column_config.NumberColumn("Profit", format="compact", width="small"),
                "Units sold": st.column_config.NumberColumn("Units", width="small"),
                "Transactions": st.column_config.NumberColumn("Txns", width="small"),
                "Profit margin (%)": st.column_config.NumberColumn("Margin", format="%.1f%%", width="small"),
            },
        )


# ------------------------------------------------------ Raw data explorer
@st.fragment
def data_explorer_card():
    data = get_global_data()
    all_columns = list(data.columns)
    starter_columns = ["Transaction_ID", "Timestamp", "Emirate", "Store_Name", "Category",
                       "Sub_Category", "Units_Sold", "Net_Sales_AED", "Profit_AED", "Promotion"]
    with st.container(border=True):
        with card_header("Raw data", wide=True):
            columns = st.multiselect("Columns to show", all_columns, default=starter_columns, key="raw_columns")
            category = st.selectbox("Category", ["All categories"] + CATEGORIES, key="raw_category")

        if category != "All categories":
            data = data[data["Category"] == category]
        columns = columns or all_columns          # nothing picked = show every column
        show_active_filters(category, f"{len(data):,} rows", f"{len(columns)} of {len(all_columns)} columns")

        st.dataframe(data[columns], hide_index=True, height=300)
        st.download_button("Download these rows as CSV", data[columns].to_csv(index=False),
                           file_name="lulu_sales_filtered.csv", mime="text/csv",
                           icon=":material/download:", on_click="ignore")


# =============================================================================
# 6. PAGE LAYOUT  (this is the part that actually draws the page, top to bottom)
# =============================================================================
df = load_data()
first_day, last_day = df["Date"].min().date(), df["Date"].max().date()

st.title("🛒 LuLu UAE Sales Dashboard")
st.caption(f"Synthetic data for teaching, not real LuLu figures. {len(df):,} transactions "
           f"from {first_day:%d %b %Y} to {last_day:%d %b %Y}.")

# ---- Global filters (they change every chart) ----
with st.container(border=True):
    date_col, emirate_col = st.columns([1, 2])
    date_col.date_input("Date range", value=(first_day, last_day), min_value=first_day,
                        max_value=last_day, format="DD/MM/YYYY", key="global_dates")
    emirate_col.multiselect("Emirates", EMIRATES, placeholder="All emirates", key="global_emirates")
    st.caption("These two filters change every chart. Each chart's Filters button changes only that chart.")

# While someone is picking dates, the date box holds just the first date.
# Wait until both dates are chosen before drawing anything.
if len(st.session_state["global_dates"]) != 2:
    st.info("Pick an end date to finish setting the date range.")
    st.stop()

if get_global_data().empty:
    st.warning("No transactions in this date range and emirate selection. Widen the global filters.")
    st.stop()

# ---- KPIs ----
kpi_row()

# ---- Charts: two per row, wide charts get the full row ----
left, right = st.columns(2)
with left:
    sales_by_category_card()
with right:
    emirate_heatmap_card()

trend_card()

left, right = st.columns(2)
with left:
    mix_card()
with right:
    promotion_card()

left, right = st.columns(2)
with left:
    customer_card()
with right:
    top_products_card()

data_explorer_card()
