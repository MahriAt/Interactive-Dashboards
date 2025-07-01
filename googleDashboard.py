from itertools import islice
import streamlit as st
import pandas as pd
import plotly
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import json
import os
from datetime import datetime
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
        styled_df,
        #tickers_df,
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
@st.fragment
def display_symbol_history(tickers_df, history_df):
    left_widget, right_widget, _ = st.columns([1, 1, 1.5])
    selected_ticker = left_widget.selectbox(
        "Currently Showing",
        list(history_df.keys())
    )
    selected_period = right_widget.selectbox(
        "Period",
        ("Week", "Month", "Trimester", "Year"),
        2
    )
    
    history_df = history_df[selected_ticker]
    
    history_df = history_df.set_index("Date")
    mapping_period = {
        "Week": 7,
        "Month": 31,
        "Trimester": 90,
        "Year" : 365
    }
    today = datetime.today().date()
    delay_days = mapping_period[selected_period]
    history_df = history_df[
        (today - pd.Timedelta(delay_days, unit="d")):today
    ]
    f_candle = plot_candlestick(history_df)
    left_chart, right_indicator = st.columns([3, 1])
    with left_chart:
        st.plotly_chart(f_candle, use_container_width= True)
        
    with right_indicator:
        l, r = st.columns(2)
        
        with l:
            st.metric(
                "Lowesr Volume Day Trade",
                f'{history_df["Volume"].min():,}'
            )
            st.metric(
                "Lowest Close Price",
                f'{history_df["Close"].min():,} $'
            )
        with r:
            st.metric(
                "Highest Volume Day Trade",
                f'{history_df["Volume"].max():,}'
            )
            st.metric(
                "Highest Close Price",
                f'{history_df["Close"].max():,} $'
            )
        with st.container():
            st.metric(
                "Average Daily Volume",
                f'{int(history_df["Volume"].mean()):,}'
            )
            st.metric(
                "Current Shares",
                "{:,} $".format(
                    tickers_df.loc[tickers_df["Ticker"] == selected_ticker,
                               "Shares"].values[0]
                )
            )
    
def plot_candlestick(history_df):
    f_candle = make_subplots(
        rows = 2,
        cols = 1,
        shared_xaxes = True,
        row_heights = [0.7, 0.3],
        vertical_spacing = 0.1
    )
    f_candle.add_trace(
        go.Candlestick(
            x = history_df.index,
            open = history_df["Open"],
            high = history_df["High"],
            low = history_df["Low"],
            close = history_df["Close"],
            name = "Dollars"
        ),
        row = 1,
        col = 1
    )
    f_candle.add_trace(
        go.Bar(
            x = history_df.index,
            y = history_df["Volume"],
            name = "Volume Traded"
        ),
        row = 2,
        col = 1
    )
    f_candle.update_layout(
        title = "Stock Price Trends",
        showlegend = True,
        xaxis_rangeslider_visible = False,
        yaxis1 = dict(title = "OHLC"),
        yaxis2 = dict(title = "Volume"),
        hovermode = "x"
    )
    f_candle.update_layout(
        title_font_family = "Open Sans",
        title_font_color = "#174C4F",
        title_font_size = 32,
        font_size = 16,
        margin = dict(l=80, r=80, t=100, b=80, pad=0),
        height = 500
    )
    f_candle.update_xaxes(title_text= "Date", row=2, col=1)
    f_candle.update_traces(selector = dict(name= "Dollars"))
    return f_candle

def batched(iterable, n_cols):
    if n_cols < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n_cols)):
        yield batch

def plot_sparkline(data):
    fig_spark = go.Figure(
        data=go.Scatter(
            y=data,
            mode="lines",
            fill="tozeroy",
            line_color="red",
            fillcolor="pink"
        )
    )
    fig_spark.update_traces(hovertemplate="Price: $ %{y:.2f}")
    fig_spark.update_xaxes(visible=False, fixedrange=True)
    fig_spark.update_yaxes(visible=False, fixedrange=True)
    fig_spark.update_layout(
        showlegend=False,
        plot_bgcolor= "white",
        height=50,
        margin=dict(t=10, l=0, b=0, r=0, pad=0),
        
    )
    
    return fig_spark
def display_watchlist_card(Ticker, Symbol_Name, Last_price, Change_Prc,Open):
    with st.container(border=True):
        st.html(f'<span class="watchlist_card"></span>')
        tl, tr = st.columns([2, 1])
        bl, br = st.columns([1, 1])
        
        with tl:
            st.html(f'<span class= "watchlist_symbol_name"></span>')
            st.markdown(f"{Symbol_Name}")
        with tr:
            st.html(f'<span class= "watchlist_ticker"></span>')
            st.markdown(f"{Ticker}")
            negative_gradient = float(Change_Prc)< 0
            st.markdown(
                f""":{'red'
                    if negative_gradient
                    else 'green'}[{'▼' if negative_gradient else '▲'} {Change_Prc} %]"""
            )
        with bl:
            with st.container():
                st.html(f'<span class= "watchlist_price_label"></span>')
                st.markdown("Current Value")
            with st.container():
                st.html(f'<span class= "watchlist_price_value"></span>')
                st.markdown(f"$ {Last_price: .2f}")
        with br:
            
            fig_spark = plot_sparkline(Open)
            st.plotly_chart(
                fig_spark,
                config = dict(displayModeBar = False),
                use_container_width= True
            )
def display_watchlist(tickers_df):
    n_cols = 4
    tickers_df.columns = [c.replace(" ", "_") for c in tickers_df.columns]
    for row in batched(tickers_df.itertuples(), n_cols):
        cols = st.columns(n_cols)
        for col, ticker in zip(cols, row):
            if ticker:
                with col:
                    display_watchlist_card(
                        ticker.Ticker,
                        ticker.Symbol_Name,
                        ticker.Last_price,
                        ticker.Change_Prc,
                        ticker.Open
                    )


###############################################
#------------------Main-----------------------#
###############################################
spreadsheet = connection()
dfs = pull_data(spreadsheet)
tickers_df = dfs["ticker"]
history_df = {t: dfs[t] for t in list(tickers_df["Ticker"])}
tickers_df, history_df = transform_data(tickers_df, history_df)

st.title("Stocks Dashboard")
display_watchlist(tickers_df)
st.divider()
#display_overview(tickers_df)
display_symbol_history(tickers_df, history_df)
