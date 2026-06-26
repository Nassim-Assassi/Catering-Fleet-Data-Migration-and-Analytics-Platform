import altair as alt
import awswrangler as wr
import pandas as pd
import streamlit as st
from datetime import date
from os import environ
from dotenv import load_dotenv

from data_wranglers import (
    load_average_sale_value_per_truck_for_month,
    load_total_revenue_for_month,
    load_total_revenue_per_truck_for_month,
    load_total_sales_for_month,
    load_total_sales_per_truck_for_month,
    load_truck_day_revenue_for_month,
    load_truck_day_sales_for_month,
    load_truck_hour_revenue_for_month,
    load_truck_hour_sales_for_month,
    load_truck_names,
)


def get_formatted_month_year(year: int, month: int) -> str:
    """Returns a formatted string for the month and year."""
    return date(year, month, 1).strftime("%B %Y")

# Financial Dashboard Charts and Layout


def get_truck_colour_scale(trucks_df: pd.DataFrame) -> alt.Scale:
    """Returns a consistent Altair colour scale from a DataFrame with truck_name."""
    truck_names = (
        trucks_df["truck_name"].dropna().astype(str).unique().tolist()
    )
    return alt.Scale(domain=sorted(truck_names))


def get_truck_colour_legend(trucks_df: pd.DataFrame) -> alt.Chart:
    """Returns a standalone legend panel using the shared colour scale."""
    legend_df = (
        trucks_df[["truck_name"]]
        .dropna()
        .drop_duplicates()
        .sort_values("truck_name")
        .copy()
    )
    legend_df["truck_name"] = legend_df["truck_name"].astype(str)

    return (
        alt.Chart(legend_df)
        .mark_point(size=120, filled=True)
        .encode(
            y=alt.Y("truck_name:N", title=None,
                    axis=alt.Axis(labelFontSize=12)),
            color=alt.Color("truck_name:N",
                            scale=get_truck_colour_scale(trucks_df),
                            legend=None),
        )
    )


def create_average_revenue_per_truck_chart(df: pd.DataFrame, colour_scale: alt.Scale) -> alt.Chart:
    """Creates a bar chart showing average revenue per truck."""
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            y=alt.Y("truck_name:N", sort="-x", title="Truck Name"),
            x=alt.X("total_revenue:Q", title="Total Revenue"),
            color=alt.Color("truck_name:N", scale=colour_scale, legend=None),
        )
        .properties(width="container")
    )


def get_revenue_summary_page(config, year: int, month: int, colour_scale: alt.Scale):
    formatted_month_year = get_formatted_month_year(year, month)
    st.title(
        f"Revenue Summary ({formatted_month_year})", text_alignment="center")

    # Load all data needed for this page
    total_revenue_per_truck = load_total_revenue_per_truck_for_month(
        config["GLUE_DB_NAME"], year, month)

    average_sale_value_per_truck = load_average_sale_value_per_truck_for_month(
        config["GLUE_DB_NAME"], year, month)

    total_revenue_this_month = load_total_revenue_for_month(
        config["GLUE_DB_NAME"], year, month)

    upper_col1, upper_col2, upper_col3 = st.columns(3)
    with upper_col2:
        st.metric(label="Total Revenue:",
                  value=f"£{total_revenue_this_month}")

    st.write("Revenue Per Truck:")
    average_revenue_per_truck_chart = create_average_revenue_per_truck_chart(
        total_revenue_per_truck, colour_scale)
    st.altair_chart(average_revenue_per_truck_chart,
                    use_container_width=True)

    st.write("Average Sale Value Per Truck:")
    st.table(average_sale_value_per_truck.rename(
        columns={"truck_name": "Truck",
                 "average_sale_value": "Average Sale Value"}
    ).style.format({"Average Sale Value": "£{:.2f}"}))


# Revenue Trends Dashboard Charts and Layout

def create_truck_day_revenue_chart(df: pd.DataFrame, colour_scale: alt.Scale) -> alt.Chart:
    """Creates a line chart showing daily revenue per truck."""
    return (
        alt.Chart(df)
        .mark_line()
        .encode(
            x=alt.X("day:O", title="Day of the Month"),
            y=alt.Y("total_revenue:Q", title="Total Revenue"),
            color=alt.Color(
                "truck_name:N", scale=colour_scale, legend=None),
        )
        .properties(width="container")
    )


def create_truck_hour_revenue_chart(df: pd.DataFrame, colour_scale: alt.Scale) -> alt.Chart:
    """Creates a line chart showing hourly revenue per truck."""
    return (
        alt.Chart(df)
        .mark_line()
        .encode(
            x=alt.X("hour:O", title="Hour of the Day"),
            y=alt.Y("average_revenue:Q", title="Average Revenue"),
            color=alt.Color(
                "truck_name:N", scale=colour_scale, legend=None),
        )
        .properties(width="container")
    )


def get_revenue_trends_page(config, year: int, month: int, colour_scale: alt.Scale):
    formatted_month_year = get_formatted_month_year(year, month)
    st.title(
        f"Revenue Trends ({formatted_month_year})", text_alignment="center")

    # Load all data needed for this page
    truck_day_revenue_this_month = load_truck_day_revenue_for_month(
        config["GLUE_DB_NAME"], year, month)
    truck_hour_revenue_this_month = load_truck_hour_revenue_for_month(
        config["GLUE_DB_NAME"], year, month)

    st.write("Total Daily Revenue Per Truck:")
    truck_day_revenue_chart = create_truck_day_revenue_chart(
        truck_day_revenue_this_month, colour_scale)
    st.altair_chart(truck_day_revenue_chart, use_container_width=True)

    st.write("Average Hourly Revenue Per Truck:")
    truck_hour_revenue_chart = create_truck_hour_revenue_chart(
        truck_hour_revenue_this_month, colour_scale)
    st.altair_chart(truck_hour_revenue_chart, use_container_width=True)

# Popularity Summary page Charts and Layout


def create_total_sales_per_truck_chart(df: pd.DataFrame, colour_scale: alt.Scale) -> alt.Chart:
    """Creates a bar chart showing total sales per truck."""
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            y=alt.Y("truck_name:N", sort="-x", title="Truck Name"),
            x=alt.X("total_sales:Q", title="Total Sales"),
            color=alt.Color("truck_name:N", scale=colour_scale, legend=None),
        )
        .properties(width="container")
    )


def get_popularity_summary_page(config, year: int, month: int, colour_scale: alt.Scale):
    formatted_month_year = get_formatted_month_year(year, month)
    st.title(
        f"Popularity Summary ({formatted_month_year})", text_alignment="center")
    # Load all data needed for this page
    total_sales_this_month = load_total_sales_for_month(
        config["GLUE_DB_NAME"], year, month)
    total_sales_per_truck_this_month = load_total_sales_per_truck_for_month(
        config["GLUE_DB_NAME"], year, month)

    upper_col1, upper_col2, upper_col3 = st.columns(3)
    with upper_col2:
        st.metric(label="Total Sales:",
                  value=total_sales_this_month)

    st.write("Total Sales Per Truck:")
    total_sales_per_truck_chart = create_total_sales_per_truck_chart(
        total_sales_per_truck_this_month, colour_scale)
    st.altair_chart(total_sales_per_truck_chart,
                    use_container_width=True)


# Popularity Trends page Charts and Layout


def create_truck_day_sales_chart(df: pd.DataFrame, colour_scale: alt.Scale) -> alt.Chart:
    """Creates a line chart showing daily sales per truck."""
    return (
        alt.Chart(df)
        .mark_line()
        .encode(
            x=alt.X("day:O", title="Day of the Month"),
            y=alt.Y("total_sales:Q", title="Total Sales"),
            color=alt.Color(
                "truck_name:N", scale=colour_scale, legend=None),
        )
        .properties(width="container")
    )


def create_truck_hour_sales_chart(df: pd.DataFrame, colour_scale: alt.Scale) -> alt.Chart:
    """Creates a line chart showing hourly sales per truck."""
    return (
        alt.Chart(df)
        .mark_line()
        .encode(
            x=alt.X("hour:O", title="Hour of the Day"),
            y=alt.Y("total_sales:Q", title="Total Sales"),
            color=alt.Color(
                "truck_name:N", scale=colour_scale, legend=None),
        )
        .properties(width="container")
    )


def get_popularity_trends_page(config, year: int, month: int, colour_scale: alt.Scale):
    formatted_month_year = get_formatted_month_year(year, month)
    st.title(
        f"Popularity Trends ({formatted_month_year})", text_alignment="center")

    # Load all data needed for this page
    truck_day_sales_this_month = load_truck_day_sales_for_month(
        config["GLUE_DB_NAME"], year, month)
    truck_hour_sales_this_month = load_truck_hour_sales_for_month(
        config["GLUE_DB_NAME"], year, month)

    st.write("Total Daily Sales Per Truck:")
    truck_day_sales_chart = create_truck_day_sales_chart(
        truck_day_sales_this_month, colour_scale)
    st.altair_chart(truck_day_sales_chart, use_container_width=True)

    st.write("Average Hourly Sales Per Truck:")
    truck_hour_sales_chart = create_truck_hour_sales_chart(
        truck_hour_sales_this_month, colour_scale)
    st.altair_chart(truck_hour_sales_chart, use_container_width=True)

# Main dashboard function to select and display the appropriate page


def get_full_dashboard(config):
    # Build one shared colour scale from the full set of truck names
    trucks_df = load_truck_names(config["GLUE_DB_NAME"])
    truck_names = trucks_df["truck_name"].dropna()

    if truck_names.empty:
        st.warning("No truck names available to build chart colours.")
        return

    colour_scale = get_truck_colour_scale(trucks_df)

    selected_page = st.sidebar.selectbox(
        "Choose a dashboard",
        ("Revenue Summary", "Revenue Trends",
         "Popularity Summary", "Popularity Trends"),
    )
    st.sidebar.success("Select a dashboard above.")

    today = date.today()
    current_year = today.year
    current_month = today.month

    year_options = list(range(1990, current_year + 1))
    month_options = list(range(1, 13))

    year = st.sidebar.selectbox(
        'Year',
        year_options,
        index=year_options.index(current_year),
    )

    month = st.sidebar.selectbox(
        'Month',
        month_options,
        index=current_month - 1,
    )

    st.sidebar.write("Truck Colour Legend:")
    st.sidebar.altair_chart(get_truck_colour_legend(
        trucks_df), use_container_width=True)

    if selected_page == "Revenue Summary":
        get_revenue_summary_page(config, year, month, colour_scale)
    elif selected_page == "Revenue Trends":
        get_revenue_trends_page(config, year, month, colour_scale)
    elif selected_page == "Popularity Summary":
        get_popularity_summary_page(config, year, month, colour_scale)
    elif selected_page == "Popularity Trends":
        get_popularity_trends_page(config, year, month, colour_scale)


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    config: dict[str, str] = dict(environ)
    if "GLUE_DB_NAME" not in config:
        st.error("GLUE_DB_NAME environment variable is not set.")
    else:
        get_full_dashboard(config)
