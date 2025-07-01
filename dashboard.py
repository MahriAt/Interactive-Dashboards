import streamlit as st
import plotly.express as px
import pandas as pd
import os
import warnings 
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Superstore", page_icon=":bar_chart:", layout="wide")
#sets the title of the app to find more icons google streamlit emoji icons

st.title(":bar_chart: Superstore EDA")
#title inside of the page

#st.markdown('<style>div.block-container{padding-top:1rem}</style>', unsafe_allow_html=True)
#apply CSS and HTML rules in the file


fl = st.file_uploader(":file_folder: upload the file", type=(["csv", "txt", "xlsx", "xls"])) #gets the file
if fl is not None:
    filename = fl.name #define the name of the file
    suffix =Path(filename).suffix
    if suffix == "xls" or suffix == "xlsx":
        df = pd.read_excel(fl, sheet_name=None, header=0)
        combined_df = pd.concat(df.values(), ignore_index=True)
        new_filename = Path(filename).with_suffix('.csv').name
        combined_df.to_csv(new_filename, index=False)
    
    st.write(filename)
    df = pd.read_csv(new_filename, encoding = "utf-8")
else:
    os.chdir(r"D:\dashboards")
    df = pd.read_csv("SuperstoreNew.csv", encoding = "utf-8")
#read the file uploaded or the file in the folder by default

col1, col2 = st.columns((2))
#define that there are 2 columns

df["Order Date"] = pd.to_datetime(df["Order Date"])

#Getting the min and max date and shows by default
startDate = pd.to_datetime(df["Order Date"]).min()
endDate = pd.to_datetime(df["Order Date"]).max()

#allow the user to selct other dates
with col1:
    date1 = pd.to_datetime(st.date_input("Start Date", startDate))

with col2:
    date2 = pd.to_datetime(st.date_input("End Date", endDate))

#change data frame according to the user input
df = df[(df["Order Date"] >= date1) & (df["Order Date"] <= date2)].copy()


st.sidebar.header("Chose your filter: ")
#Create for Region
region = st.sidebar.multiselect("Pick your region", df["Region"].unique())
if not region:
    df2 = df.copy()
else:
    df2 = df[df["Region"].isin(region)]

#Create for the state
state = st.sidebar.multiselect("Pick the State", df2["State"].unique())
if not state:
    df3 = df2.copy()
else:
    df3 = df2[df2["State"].isin(state)]

#Create for city 
city = st.sidebar.multiselect("Pick the city", df3["City"].unique())

#Filter the data based on Region State and city
if not region and not state and not city:
    filtered_df = df
elif not state and not city:
    filtered_df = df[df["Region"].isin(region)]
elif not region and not city:
    filtered_df = df[df["State"].isin(state)]
elif state and city:
    filtered_df = df3[df["State"].isin(state) & df3["City"].isin(city)]
elif region and city:
    filtered_df = df3[df["Region"].isin(region) & df3["City"].isin(city)]
elif region and state:
    filtered_df = df3[df["Region"].isin(region) & df3["State"].isin(state)]
elif city:
    filtered_df = df3[df3["City"].isin(city)]
else:
    filtered_df =df3[df3["Region"].isin(region) & df3["State"].isin(state) & df3["City"].isin(city)]

filtered_df["Sales"] = pd.to_numeric(filtered_df["Sales"], errors="coerce")
category_df = filtered_df.groupby(by = ["Category"], as_index = False)["Sales"].sum()

with col1:
    st.subheader("Category wise Sales")
    fig = px.bar(category_df, x = "Category", y = "Sales", text = ['${:,.2f}'.format(x) for x in category_df["Sales"]],
                template = "seaborn")
    st.plotly_chart(fig, use_container_width = True, height = 200)

with col2:
    st.subheader("Region wise Sales")
    fig = px.pie(filtered_df, values = "Sales", names = "Region", hole = 0.5)
    fig.update_traces(text = filtered_df["Region"], textposition = "outside")
    st.plotly_chart(fig, use_container_width = True)

cl1, cl2 = st.columns(2)
with cl1:
    with st.expander("Category_ViewData"):
        st.write(category_df)
        csv = category_df.to_csv(index = False).encode('utf-8')
        st.download_button("Download Data", data = csv, file_name = "Category.csv", mime = "text/csv",
                            help = 'Click here to download the data as a CSV file')
with cl2:
    with st.expander("Category_ViewData"):
        region = filtered_df.groupby(by = "Region", as_index = False)["Sales"].sum()
        st.write(region)
        csv = region.to_csv(index = False).encode('utf-8')
        st.download_button("Download Data", data = csv, file_name = "Region.csv", mime = "text/csv",
                            help = 'Click here to download the data as a CSV file')

filtered_df["month_year"] = filtered_df["Order Date"].dt.to_period("M")
st.subheader('Time Series Analysis')

linechart = pd.DataFrame(filtered_df.groupby(filtered_df["month_year"].dt.strftime("%Y : %b"))["Sales"].sum()).reset_index()
fig2 = px.line(linechart, x = "month_year", y = "Sales", labels = {"Seles": "Amount"}, height = 500, width = 1000, template = "gridon")
st.plotly_chart(fig2, use_container_width = True)

with st.expander("View Data of TimeSeries:"):
    st.write(linechart.T)
    csv = linechart.to_csv(index = False).encode('utf-8')
    st.download_button('Download Data',  data = csv, file_name = "TimeSeries.csv", mime = 'text/csv')
    
#Create a treem based on Regionn, Category, Sub-Category
st.subheader("Hierarchical view of Sales using TreeMap")
fig3 = px.treemap(filtered_df, path = ["Region", "Category", "Sub-Category"], values = "Sales", hover_data = ["Sales"],
                    color = "Sub-Category")
fig.update_layout(width = 800, height = 650)
st.plotly_chart(fig3, use_container_width = True)

chart1, chart2 = st.columns((2))
with chart1:
    st.subheader('Segment wise Sales')
    fig = px.pie(filtered_df, values = "Sales", names = "Segment", template = "plotly_dark")
    fig.update_traces(text = filtered_df["Segment"], textposition = "inside")
    st.plotly_chart(fig, use_container_width =True)

with chart2:
    st.subheader('Category wise Sales')
    fig = px.pie(filtered_df, values = "Sales", names = "Category", template = "gridon")
    fig.update_traces(text = filtered_df["Category"], textposition = "inside")
    st.plotly_chart(fig, use_container_width =True)

import plotly.figure_factory as ff
st.subheader(":point_right: Month wise Sub-Category Sales Summary")
with st.expander("Summary_Table"):
    df_sample = df[0:5][["Region", "State", "City", "Category", "Sales", "Profit", "Quantity"]]
    fig = ff.create_table(df_sample, colorscale = "Cividis")
    st.plotly_chart(fig, use_container_width = True)

    st.markdown("Month wise Sub-Category Table")
    filtered_df["month"] = filtered_df["Order Date"].dt.month_name()
    sub_category_Year = pd.pivot_table(data = filtered_df, values = "Sales", index = ["Sub-Category"], columns = "month")
    st.write(sub_category_Year)

#Create a scatter plot
data1 = px.scatter(filtered_df, x = "Sales", y = "Profit", size = "Quantity")
data1['layout'].update(title =dict(text = "Relationship between Sales and Profits using Scatter Plot",
                        font = dict(size=20)), xaxis = dict(title= dict(text="Sales",font=dict(size=19))),
                        yaxis = dict(title = dict(text="Profit", font = dict(size = 19))))
st.plotly_chart(data1, use_container_width = True)

with st.expander("View Data"):
    st.write(filtered_df.iloc[:500, 1:20:2])

#Download original DataSet
csv = df.to_csv(index = False).encode('utf-8')
st.download_button("Download Data", data = csv, file_name = "Data.csv", mime = "text/csv")
