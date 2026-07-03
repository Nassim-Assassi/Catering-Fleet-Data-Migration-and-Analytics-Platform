"""this file is used to load data from the database and cache it for use in the dashboard"""

import awswrangler as wr
import pandas as pd
import streamlit as st

TTL = 60 * 30


# Global Wranglers

@st.cache_data(ttl=TTL)
def load_truck_names(db_name: str, s3_output: str) -> pd.DataFrame:
    query = """
    SELECT truck_name
    FROM DIM_Truck
    """
    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df


# Revenue Summary page Wranglers


@st.cache_data(ttl=TTL)
def load_total_revenue_for_month(db_name: str, year: int, month: int, s3_output: str) -> float:
    query = f"""
    SELECT SUM(total)/100 AS total_revenue
    FROM FACT_Transaction
    WHERE year = {year}
    AND month = {month}
    """
    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df.iloc[0, 0]


@st.cache_data(ttl=TTL)
def load_total_revenue_per_truck_for_month(db_name: str, year: int, month: int, s3_output: str) -> pd.DataFrame:
    query = f"""
    SELECT truck_name, SUM(total)/100 AS total_revenue
    FROM FACT_Transaction
    JOIN DIM_Truck ON FACT_Transaction.truck_id = DIM_Truck.truck_id
    WHERE year = {year}
    AND month = {month}
    GROUP BY truck_name
    """
    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df


@st.cache_data(ttl=TTL)
def load_average_sale_value_per_truck_for_month(db_name: str, year: int, month: int, s3_output: str) -> pd.DataFrame:
    query = f"""
    SELECT truck_name, ROUND(AVG(total)/100, 2) AS average_sale_value
    FROM FACT_Transaction
    JOIN DIM_Truck ON FACT_Transaction.truck_id = DIM_Truck.truck_id
    WHERE year = {year}
    AND month = {month}
    GROUP BY truck_name
    ORDER BY average_sale_value DESC
    """
    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df


# Revenue trends page wranglers

@st.cache_data(ttl=TTL)
def load_truck_day_revenue_for_month(db_name: str, year: int, month: int, s3_output: str) -> pd.DataFrame:
    query = f"""
    SELECT truck_name, day, SUM(total)/100 AS total_revenue
    FROM FACT_Transaction
    JOIN DIM_Truck ON FACT_Transaction.truck_id = DIM_Truck.truck_id
    WHERE year = {year}
    AND month = {month}
    GROUP BY truck_name, day
    ORDER BY truck_name, day
    """
    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df


@st.cache_data(ttl=TTL)
def load_truck_hour_revenue_for_month(db_name: str, year: int, month: int, s3_output: str) -> pd.DataFrame:
    query = f"""
    SELECT truck_name, HOUR(at) AS hour, AVG(total)/100 AS average_revenue
    FROM FACT_Transaction
    JOIN DIM_Truck ON FACT_Transaction.truck_id = DIM_Truck.truck_id
    WHERE year = {year}
    AND month = {month}
    GROUP BY truck_name, HOUR(at)
    ORDER BY truck_name, HOUR(at)
    """
    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df


# Popularity Summary Wranglers

@st.cache_data(ttl=TTL)
def load_total_sales_for_month(db_name: str, year: int, month: int, s3_output: str) -> int:
    query = f"""
    SELECT COUNT(*) AS total_sales
    FROM FACT_Transaction
    WHERE year = {year}
    AND month = {month}
    """
    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df.iloc[0, 0]


@st.cache_data(ttl=TTL)
def load_total_sales_per_truck_for_month(db_name: str, year: int, month: int, s3_output: str) -> pd.DataFrame:
    query = f"""
    SELECT truck_name, COUNT(*) AS total_sales
    FROM FACT_Transaction
    JOIN DIM_Truck ON FACT_Transaction.truck_id = DIM_Truck.truck_id
    WHERE year = {year}
    AND month = {month}
    GROUP BY truck_name
    """
    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df


# Popularity Trends Wranglers

@st.cache_data(ttl=TTL)
def load_truck_day_sales_for_month(db_name: str, year: int, month: int, s3_output: str) -> pd.DataFrame:
    query = f"""
    SELECT truck_name, day, COUNT(*) AS total_sales
    FROM FACT_Transaction
    JOIN DIM_Truck ON FACT_Transaction.truck_id = DIM_Truck.truck_id
    WHERE year = {year}
    AND month = {month}
    GROUP BY truck_name, day
    ORDER BY truck_name, day
    """
    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df


@st.cache_data(ttl=TTL)
def load_truck_hour_sales_for_month(db_name: str, year: int, month: int, s3_output: str) -> pd.DataFrame:
    query = f"""
    SELECT truck_name, HOUR(at) AS hour, COUNT(*) AS total_sales
    FROM FACT_Transaction
    JOIN DIM_Truck ON FACT_Transaction.truck_id = DIM_Truck.truck_id
    WHERE year = {year}
    AND month = {month}
    GROUP BY truck_name, HOUR(at)
    ORDER BY truck_name, HOUR(at)
    """
    df = wr.athena.read_sql_query(
        sql=query,
        database=db_name,
        s3_output=s3_output,
    )
    return df


if __name__ == "__main__":
    pass
