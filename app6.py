import json
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import plotly.express as px
import random
from branca.element import Element

# --- Load JSON data ---
try:
    with open("pg.json", "r") as f:
        pg_data = json.load(f)
    df = pd.DataFrame(pg_data)
except FileNotFoundError:
    st.error("pg.json file not found. Please ensure the file exists.")
    st.stop()
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.stop()

# --- Fix Amenities and Common Area columns safely ---
if "Amenities" in df:
    df["Amenities"] = df["Amenities"].apply(lambda x: x if isinstance(x, list) else [])
else:
    df["Amenities"] = [[] for _ in range(len(df))]

if "Common Area" in df:
    df["Common Area"] = df["Common Area"].apply(lambda x: x if isinstance(x, list) else [])
else:
    df["Common Area"] = [[] for _ in range(len(df))]

# --- Ensure required columns exist ---
required_columns = [
    "Listing Title", "City", "Area", "Zone", "PG Name", "Shearing", 
    "Best Suit For", "Meals Available", "Notice Period", "Lock-in Period",
    "Non-Veg Allowed", "Opposite Gender Allowed", "Visitors Allowed",
    "Drinking Allowed", "Smoking Allowed", "Rent Price", "Security Deposit"
]

for col in required_columns:
    if col not in df.columns:
        df[col] = "" if col != "Rent Price" else 0

# --- Page Configuration ---
st.set_page_config(page_title="PG Finder Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
        padding: 1rem;
        background: linear-gradient(120deg, #a1c4fd 0%, #c2e9fb 100%);
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .pg-card {
        background-color: #f8fafc;
        border-left: 5px solid #3b82f6;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    .pg-card:hover {
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }
    .pg-title { font-size: 1.4rem; font-weight: 600; color: #1e40af; margin-bottom: 0.5rem; }
    .pg-rent { font-size: 1.2rem; font-weight: 700; color: #047857; }
    .pg-details { margin-top: 1rem; padding-top: 1rem; border-top: 1px dashed #cbd5e1; }
    .detail-row { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
    .detail-label { font-weight: 500; color: #475569; }
    .detail-value { color: #1e293b; }
    .amenities { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
    .amenity-tag { background-color: #dbeafe; color: #1d4ed8; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.875rem; }
    .map-container { height: 500px; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
    .chart-container { background-color: #ffffff; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); margin-bottom: 1.5rem; }
    .filter-section { background-color: #f1f5f9; padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem; }
    .filter-header { font-size: 1.3rem; font-weight: 600; color: #1e293b; margin-bottom: 1rem; }
    .avg-rent-highlight { color: #ef4444; font-weight: 600; }
    .below-avg-rent { color: #3b82f6; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- Main Header ---
st.markdown('<div class="main-header">🏠 PG Listings Dashboard</div>', unsafe_allow_html=True)

# --- Sidebar Filters ---
st.sidebar.markdown('<div class="filter-header">🔍 Filter Options</div>', unsafe_allow_html=True)

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

# --- Results Header ---
st.markdown(f"### 🏠 Found {len(filtered_df)} PG Listings matching your criteria")

# --- Average Rent ---
avg_rent = filtered_df["Rent Price"].mean() if not filtered_df.empty else 0
st.markdown(f"#### 💰 Average Rent: ₹{avg_rent:.2f}")

# --- PG Listings ---
st.markdown("### 📋 PG Listings")

if filtered_df.empty:
    st.warning("No PG listings match your criteria. Please adjust your filters.")
else:
    for idx, row in filtered_df.iterrows():
        rent_class = "avg-rent-highlight" if row['Rent Price'] > avg_rent else "below-avg-rent"
        with st.expander(f"**{row['PG Name']}** - {row['Shearing']} | ₹{row['Rent Price']}", expanded=False):
            # Create amenities display
            amenities_html = ""
            if row['Amenities']:
                amenities_html = "<div class='amenities'>" + \
                                "".join([f"<span class='amenity-tag'>{amenity}</span>" for amenity in row['Amenities']]) + \
                                "</div>"
            
            # Create common area display
            common_area_html = ""
            if row['Common Area']:
                common_area_html = "<div class='amenities'>" + \
                                  "".join([f"<span class='amenity-tag'>{area}</span>" for area in row['Common Area']]) + \
                                  "</div>"
            
            st.markdown(f"""
            <div class="pg-details">
                <div class="detail-row"><span class="detail-label">Listing Title:</span><span class="detail-value">{row['Listing Title']}</span></div>
                <div class="detail-row"><span class="detail-label">Location:</span><span class="detail-value">{row['Area']}, {row['City']}, {row['Zone']}</span></div>
                <div class="detail-row"><span class="detail-label">Best Suit For:</span><span class="detail-value">{row['Best Suit For']}</span></div>
                <div class="detail-row"><span class="detail-label">Meals:</span><span class="detail-value">{row['Meals Available']}</span></div>
                <div class="detail-row"><span class="detail-label">Notice Period:</span><span class="detail-value">{row['Notice Period']}</span></div>
                <div class="detail-row"><span class="detail-label">Lock-in Period:</span><span class="detail-value">{row['Lock-in Period']}</span></div>
                <div class="detail-row"><span class="detail-label">Non-Veg Allowed:</span><span class="detail-value">{row['Non-Veg Allowed']}</span></div>
                <div class="detail-row"><span class="detail-label">Opposite Gender Allowed:</span><span class="detail-value">{row['Opposite Gender Allowed']}</span></div>
                <div class="detail-row"><span class="detail-label">Visitors Allowed:</span><span class="detail-value">{row['Visitors Allowed']}</span></div>
                <div class="detail-row"><span class="detail-label">Drinking Allowed:</span><span class="detail-value">{row['Drinking Allowed']}</span></div>
                <div class="detail-row"><span class="detail-label">Smoking Allowed:</span><span class="detail-value">{row['Smoking Allowed']}</span></div>
                <div class="detail-row"><span class="detail-label">Security Deposit:</span><span class="detail-value">₹{row['Security Deposit']}</span></div>
                <div class="detail-row"><span class="detail-label">Amenities:</span></div>
                {amenities_html}
                <div class="detail-row"><span class="detail-label">Common Area:</span></div>
                {common_area_html}
            </div>
            """, unsafe_allow_html=True)

# --- Map View ---
st.markdown("### 🗺️ Map View")
if not filtered_df.empty:
    # Check if Latitude & Longitude exist
    if "Latitude" in filtered_df.columns and "Longitude" in filtered_df.columns:
        # Calculate map center only if coordinates are available
        valid_coords = filtered_df.dropna(subset=["Latitude", "Longitude"])
        if not valid_coords.empty:
            map_center = [valid_coords["Latitude"].mean(), valid_coords["Longitude"].mean()]
        else:
            map_center = [21.1458, 79.0882]  # Default center
    else:
        map_center = [21.1458, 79.0882]  # Default center

    m = folium.Map(location=map_center, zoom_start=12)
    
    for _, row in filtered_df.iterrows():
        # Only add markers if coordinates are available
        if "Latitude" in row and "Longitude" in row and pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
            lat, lon = row["Latitude"], row["Longitude"]
            color = 'red' if row['Rent Price'] > avg_rent else 'blue'
            
            # Create tooltip with location info
            tooltip_text = f"{row['PG Name']}<br>{row['Area']}, {row['City']}"
            
            popup_html = f"<b>{row['PG Name']}</b><br>Rent: ₹{row['Rent Price']}<br>"
            popup_html += "<span style='color:red;'>Above Average</span>" if row['Rent Price'] > avg_rent else "<span style='color:blue;'>Below Average</span>"
            
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=tooltip_text,
                icon=folium.Icon(color=color, icon='home', prefix='fa')
            ).add_to(m)

    # Add legend
    legend_html = f'''
         <div style="position: fixed; top: 10px; right: 10px; width: 180px; height: 110px; 
                     border:2px solid grey; z-index:9999; font-size:14px; background-color:white; padding: 10px;">
             <b>Rent Comparison</b> <br>
             <i class="fa fa-circle" style="color:red"></i> Above Average <br>
             <i class="fa fa-circle" style="color:blue"></i> Below Average <br>
             Avg: ₹{avg_rent:.2f}
         </div>'''
    m.get_root().html.add_child(Element(legend_html))

    folium_static(m, width='100%', height=500)
else:
    st.warning("No PG listings to show on the map.")

# --- Analytics Section ---
st.markdown("### 📊 Analytics")

if filtered_df.empty:
    st.warning("No data available for analytics. Please adjust your filters.")
else:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        if "Area" in filtered_df.columns:
            avg_rent_area = filtered_df.groupby("Area")["Rent Price"].mean().reset_index()
            fig1 = px.bar(avg_rent_area, x="Area", y="Rent Price", title="Average Rent by Area", color="Rent Price", color_continuous_scale="Blues")
            fig1.update_layout(title_font_size=18, xaxis_title="Area", yaxis_title="Average Rent (₹)", plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.warning("Area data not available for this chart.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        if "Shearing" in filtered_df.columns:
            shearing_count = filtered_df["Shearing"].value_counts().reset_index()
            shearing_count.columns = ["Shearing", "Count"]
            fig2 = px.pie(shearing_count, names="Shearing", values="Count", title="Shearing Type Distribution", hole=0.4)
            fig2.update_traces(textposition='inside', textinfo='percent+label')
            fig2.update_layout(title_font_size=18)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("Shearing data not available for this chart.")
        st.markdown('</div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        if "Meals Available" in filtered_df.columns:
            meals_count = filtered_df["Meals Available"].value_counts().reset_index()
            meals_count.columns = ["Meals", "Count"]
            fig3 = px.bar(meals_count, x="Meals", y="Count", title="Meals Availability", color="Meals", color_discrete_map={"Yes": "#4ade80", "No": "#f87171"})
            fig3.update_layout(title_font_size=18, xaxis_title="Meals Available", yaxis_title="Count", plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("Meals data not available for this chart.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        if "Opposite Gender Allowed" in filtered_df.columns:
            gender_count = filtered_df["Opposite Gender Allowed"].value_counts().reset_index()
            gender_count.columns = ["Policy", "Count"]
            fig4 = px.bar(gender_count, x="Policy", y="Count", title="Opposite Gender Policy", color="Policy", color_discrete_map={"Yes": "#60a5fa", "No": "#fbbf24"})
            fig4.update_layout(title_font_size=18, xaxis_title="Opposite Gender Allowed", yaxis_title="Count", plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.warning("Opposite Gender policy data not available for this chart.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Footer ---
st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding: 1rem; color: #64748b; font-size: 0.9rem;">
    PG Finder Dashboard • Data sourced from pg.json • Last updated: 2023
</div>
""", unsafe_allow_html=True)
