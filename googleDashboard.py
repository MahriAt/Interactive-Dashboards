import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe

@st.cache_resource
def connection():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]
    cred = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(cred)
    sheet_id = "1zHEWKdHTFkt_9suy3ErARImM0mdrwhgLXaevfuYwt0o"

    spreadsheet  = client.open_by_key(sheet_id)
    
    return spreadsheet

@st.cache_data
def pull_data(_spreadsheet):
    worksheets = spreadsheet.worksheets()
    dfs = {}
    for sheet in worksheets:
        df = get_as_dataframe(sheet, evaluate_formulas= True)
        df.dropna(how="all", inplace=True)
        df.dropna(axis=1, how="all", inplace=True)
        dfs[sheet.title] = df
    return dfs
    


def transform_data(tickers_df, history_df):
    tickers_df["Last Trade time"] = pd.to_datetime(
        tickers_df["Last Trade time"], dayfirst=True)
    
    for col in list(tickers_df.columns[3:]):
        tickers_df[col] = pd.to_numeric(
            tickers_df[col], "coerce"
        )
    for ticker in list(tickers_df["Ticker"]):
        history_df[ticker]["Date"] = pd.to_datetime(
            history_df[ticker]["Date"], dayfirst=True
        )
        for col in ["Open", "High", "Low", "Close","Volume"]:
            history_df[ticker][col] = pd.to_numeric(
                history_df[ticker][col]
            )
        
    ticker_to_open = [
        list(history_df[t]["Open"])
        for t in list(tickers_df["Ticker"])
    ]
    tickers_df["Open"] = ticker_to_open
    return tickers_df, history_df

def display_overview(tickrs_df):
    def format_currency(val):
        return "$ {:,.2f}".format(val)
    def format_percentage(val):
        return "{:,.2f} %".format(val)
    def appl_odd_row_class(row):
        return [
            "background-color: #f8f8f8" if row.name % 2 !=0
            else "" for _ in row
        ]
    def format_change(val):
        return "color: red;" if (val < 0) else "color: green;"
    
    styled_df = tickers_df.style.format(
        {
            "Last Price": format_currency,
            "Change Prc": format_percentage
        }
    ).apply(
        appl_odd_row_class, axis=1
    ).map(
        format_change, subset=["Change Prc"]
    )
    st.dataframe(
        #styled_df,
        tickers_df,
        column_config={
            "Open": st.column_config.AreaChartColumn(
                "Last 12 Months",
                width = "large",
                help = "Open Price for the last 12 Months"
            )
        },
        hide_index=True,
        height=250,
    )
    
spreadsheet = connection()
dfs = pull_data(spreadsheet)
tickers_df = dfs["ticker"]
history_df = {t: dfs[t] for t in list(tickers_df["Ticker"])}

st.title("Stocks Dashboard")
tickers_df, history_df = transform_data(tickers_df, history_df)
display_overview(tickers_df)


ticker = st.selectbox("Chose your Ticker:", tickers_df["Ticker"].unique())
df = dfs[ticker]
#st.write(df)