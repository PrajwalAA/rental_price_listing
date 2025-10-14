import json
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import plotly.express as px

# --- Load JSON data ---
with open("PG.json", "r") as f:
    pg_data = json.load(f)

# Convert JSON to DataFrame for analytics
df = pd.DataFrame(pg_data)

st.title("PG Listings Dashboard")

# --- Filters ---
st.sidebar.header("Filter Options")
city = st.sidebar.selectbox("City", options=["Any"] + df["City"].unique().tolist())
shearing = st.sidebar.selectbox("Shearing", options=["Any"] + df["Shearing"].unique().tolist())
rent_max = st.sidebar.number_input("Max Rent", min_value=0, value=int(df["Rent Price"].max()))

# --- Apply Filters ---
filtered_df = df.copy()
if city != "Any":
    filtered_df = filtered_df[filtered_df["City"] == city]
if shearing != "Any":
    filtered_df = filtered_df[filtered_df["Shearing"] == shearing]
filtered_df = filtered_df[filtered_df["Rent Price"] <= rent_max]

st.subheader(f"Found {len(filtered_df)} PGs")

# --- Map View ---
st.markdown("### Map View")
# For demonstration, we'll generate dummy coordinates (replace with real lat/lon if available)
import random
filtered_df["Latitude"] = filtered_df.index.map(lambda x: 21.1458 + random.uniform(-0.01, 0.01))
filtered_df["Longitude"] = filtered_df.index.map(lambda x: 79.0882 + random.uniform(-0.01, 0.01))

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

# Average Rent by Area
avg_rent = filtered_df.groupby("Area")["Rent Price"].mean().reset_index()
fig1 = px.bar(avg_rent, x="Area", y="Rent Price", title="Average Rent by Area")
st.plotly_chart(fig1)

# Shearing Type Distribution
shearing_count = filtered_df["Shearing"].value_counts().reset_index()
shearing_count.columns = ["Shearing", "Count"]
fig2 = px.pie(shearing_count, names="Shearing", values="Count", title="Shearing Type Distribution")
st.plotly_chart(fig2)

# Meals Availability
meals_count = filtered_df["Meals Available"].value_counts().reset_index()
meals_count.columns = ["Meals", "Count"]
fig3 = px.bar(meals_count, x="Meals", y="Count", title="Meals Availability")
st.plotly_chart(fig3)

# --- List Filtered PGs ---
st.markdown("### Listings")
for idx, row in filtered_df.iterrows():
    st.markdown(f"**{row['PG Name']} ({row['Shearing']}) - ₹{row['Rent Price']}**")
    st.markdown(f"- Area: {row['Area']}, City: {row['City']}")
    st.markdown(f"- Amenities: {', '.join(row['Amenities'])}")
    st.markdown("---")
