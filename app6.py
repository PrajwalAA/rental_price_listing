import json
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import plotly.express as px
import random

# --- Load JSON data ---
with open("pg.json", "r") as f:
    pg_data = json.load(f)

df = pd.DataFrame(pg_data)

st.title("PG Listings Dashboard")

# --- Sidebar Filters with Dropdowns ---
st.sidebar.header("Filter Options")

listing_title = st.sidebar.selectbox("Listing Title", options=["Any"] + df["Listing Title"].unique().tolist())
city = st.sidebar.selectbox("City", options=["Any"] + df["City"].unique().tolist())
area = st.sidebar.selectbox("Area", options=["Any"] + df["Area"].unique().tolist())
zone = st.sidebar.selectbox("Zone", options=["Any"] + df["Zone"].dropna().unique().tolist())
pg_name = st.sidebar.selectbox("PG Name", options=["Any"] + df["PG Name"].unique().tolist())
shearing = st.sidebar.selectbox("Shearing", options=["Any"] + df["Shearing"].unique().tolist())
best_suit_for = st.sidebar.selectbox("Best Suit For", options=["Any"] + df["Best Suit For"].unique().tolist())
meals = st.sidebar.selectbox("Meals Available", options=["Any", "Yes", "No"])
notice_period = st.sidebar.selectbox("Notice Period", options=["Any"] + df["Notice Period"].unique().tolist())
lock_in_period = st.sidebar.selectbox("Lock-in Period", options=["Any"] + df["Lock-in Period"].unique().tolist())
non_veg = st.sidebar.selectbox("Non-Veg Allowed", options=["Any", "Yes", "No"])
opposite_gender = st.sidebar.selectbox("Opposite Gender Allowed", options=["Any", "Yes", "No"])
visitors = st.sidebar.selectbox("Visitors Allowed", options=["Any", "Yes", "No"])
drinking = st.sidebar.selectbox("Drinking Allowed", options=["Any", "Yes", "No"])
smoking = st.sidebar.selectbox("Smoking Allowed", options=["Any", "Yes", "No"])
rent_max = st.sidebar.number_input("Max Rent", min_value=0, value=int(df["Rent Price"].max()))

# --- Apply Filters ---
filtered_df = df.copy()

def filter_dropdown(df, column, value):
    if value != "Any":
        return df[df[column] == value]
    return df

filtered_df = filter_dropdown(filtered_df, "Listing Title", listing_title)
filtered_df = filter_dropdown(filtered_df, "City", city)
filtered_df = filter_dropdown(filtered_df, "Area", area)
filtered_df = filter_dropdown(filtered_df, "Zone", zone)
filtered_df = filter_dropdown(filtered_df, "PG Name", pg_name)
filtered_df = filter_dropdown(filtered_df, "Shearing", shearing)
filtered_df = filter_dropdown(filtered_df, "Best Suit For", best_suit_for)
if meals != "Any":
    filtered_df = filtered_df[filtered_df["Meals Available"] == meals]
filtered_df = filter_dropdown(filtered_df, "Notice Period", notice_period)
filtered_df = filter_dropdown(filtered_df, "Lock-in Period", lock_in_period)
if non_veg != "Any":
    filtered_df = filtered_df[filtered_df["Non-Veg Allowed"] == non_veg]
if opposite_gender != "Any":
    filtered_df = filtered_df[filtered_df["Opposite Gender Allowed"] == opposite_gender]
if visitors != "Any":
    filtered_df = filtered_df[filtered_df["Visitors Allowed"] == visitors]
if drinking != "Any":
    filtered_df = filtered_df[filtered_df["Drinking Allowed"] == drinking]
if smoking != "Any":
    filtered_df = filtered_df[filtered_df["Smoking Allowed"] == smoking]
filtered_df = filtered_df[filtered_df["Rent Price"] <= rent_max]

st.subheader(f"Found {len(filtered_df)} PGs")

# --- Map View ---
st.markdown("### Map View")
filtered_df.loc[:, "Latitude"] = filtered_df.index.map(lambda x: 21.1458 + random.uniform(-0.01, 0.01))
filtered_df.loc[:, "Longitude"] = filtered_df.index.map(lambda x: 79.0882 + random.uniform(-0.01, 0.01))

m = folium.Map(location=[21.1458, 79.0882], zoom_start=12)
for idx, row in filtered_df.iterrows():
    folium.Marker(
        location=[row["Latitude"], row["Longitude"]],
        popup=f"{row['PG Name']} ({row['Rent Price']})",
        tooltip=row["Area"]
    ).add_to(m)
folium_static(m)

# --- Analytics ---
st.markdown("### Analytics")
if not filtered_df.empty:
    avg_rent = filtered_df.groupby("Area")["Rent Price"].mean().reset_index()
    fig1 = px.bar(avg_rent, x="Area", y="Rent Price", title="Average Rent by Area")
    st.plotly_chart(fig1)

    shearing_count = filtered_df["Shearing"].value_counts().reset_index()
    shearing_count.columns = ["Shearing", "Count"]
    fig2 = px.pie(shearing_count, names="Shearing", values="Count", title="Shearing Type Distribution")
    st.plotly_chart(fig2)

    meals_count = filtered_df["Meals Available"].value_counts().reset_index()
    meals_count.columns = ["Meals", "Count"]
    fig3 = px.bar(meals_count, x="Meals", y="Count", title="Meals Availability")
    st.plotly_chart(fig3)

# --- List Filtered PGs ---
st.markdown("### Listings")
for idx, row in filtered_df.iterrows():
    st.markdown(f"**{row['PG Name']} ({row['Shearing']}) - ₹{row['Rent Price']}**")
    st.markdown(f"- Listing Title: {row['Listing Title']}")
    st.markdown(f"- Area: {row['Area']}, City: {row['City']}, Zone: {row['Zone']}")
    st.markdown(f"- Best Suit For: {row['Best Suit For']}")
    st.markdown(f"- Meals: {row['Meals Available']}, Notice: {row['Notice Period']}, Lock-in: {row['Lock-in Period']}")
    st.markdown(f"- Non-Veg Allowed: {row['Non-Veg Allowed']}, Opposite Gender Allowed: {row['Opposite Gender Allowed']}")
    st.markdown(f"- Visitors Allowed: {row['Visitors Allowed']}, Drinking Allowed: {row['Drinking Allowed']}, Smoking Allowed: {row['Smoking Allowed']}")
    st.markdown(f"- Amenities: {', '.join(row.get('Amenities', []))}")
    st.markdown(f"- Common Area: {', '.join(row.get('Common Area', []))}")
    st.markdown(f"- Security Deposit: ₹{row['Security Deposit']}")
    st.markdown("---")
