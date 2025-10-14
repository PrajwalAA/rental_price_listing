import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
from collections import defaultdict
import re
import math
from math import radians, sin, cos, sqrt, atan2
import requests

# Set page configuration
st.set_page_config(
    page_title="Commercial Property Search - Nagpur",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"  # Changed to collapsed since we're not using sidebar
)

# --- Load properties from JSON file ---
@st.cache_data
def load_properties():
    try:
        with open("commercial_data.json", "r") as f:
            properties = json.load(f)
            # Filter properties to only include those in Nagpur
            nagpur_properties = [p for p in properties if 
                              p.get("city", "").lower() == "nagpur" or 
                              p.get("area", "").lower().find("nagpur") != -1]
            return nagpur_properties
    except FileNotFoundError:
        st.error("Error: 'commercial_data.json' not found. Please ensure the file exists.")
        return []
    except json.JSONDecodeError:
        st.error("Error: Could not decode 'commercial_data.json'. Please check its format.")
        return []

properties_data = load_properties()

# --- Helper for normalization ---
def normalize_facility_name(facility_name):
    return str(facility_name).replace(" ", "_").lower().strip()

# --- Haversine formula for distance calculation ---
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    # Radius of earth in kilometers
    r = 6371
    return c * r

# --- Geocoding function to get coordinates from area name in Nagpur ---
@st.cache_data
def geocode_area(area_name):
    """
    Get latitude and longitude for an area name in Nagpur using Nominatim API.
    Returns a tuple (lat, lng) or None if not found.
    """
    try:
        # Using Nominatim API for geocoding (free and no API key required)
        # Append "Nagpur, India" to ensure we get locations within Nagpur
        url = f"https://nominatim.openstreetmap.org/search?q={area_name}, Nagpur, India&format=json&limit=1"
        headers = {
            "User-Agent": "PropertySearchApp/1.0"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        return None
    except Exception as e:
        st.warning(f"Geocoding error for {area_name}: {str(e)}")
        return None

# --- Function to format property details ---
def format_property(prop, distance=None):
    property_id = prop.get("property_id", "N/A")
    title = prop.get("listing_title", "N/A")
    city = prop.get("city", "N/A")
    area = prop.get("area", "N/A")
    zone = prop.get("zone", "N/A")
    location_hub = prop.get("location_hub", "N/A")
    property_type = prop.get("property_type", "N/A")
    ownership = prop.get("ownership", "N/A")
    size = prop.get("size_in_sqft", "N/A")
    carpet_area = prop.get("carpet_area_sqft", "N/A")
    floor_no = prop.get("floor_no", "N/A")
    total_floors = prop.get("total_floors", "N/A")
    rent = prop.get("rent_price", "N/A")
    security_deposit = prop.get("security_deposit", "N/A")
    brokerage = prop.get("brokerage", "N/A")
    possession_status = prop.get("possession_status", "N/A")
    property_age = prop.get("property_age", "N/A")
    negotiable = prop.get("negotiable", "N/A")
    lock_in_period = prop.get("charges", {}).get("lock_in_period_in_months", "N/A")
    
    # Format facilities that are available (value 1)
    facilities = []
    for fac, val in prop.get("facilities", {}).items():
        if val == 1:
            facilities.append(fac.replace('_', ' ').title())
    facilities_str = ", ".join(facilities) if facilities else "None"
    
    # Format available floors
    floors = []
    for floor, val in prop.get("floor_availability", {}).items():
        if val == 1:
            floors.append(floor.replace('_', ' ').title())
    floors_str = ", ".join(floors) if floors else "None"
    
    # Format furnishing status
    furnishing_status = "Furnished" if prop.get("facilities", {}).get("furnishing") == 1 else "Unfurnished"
    
    # Add distance information if available
    distance_text = ""
    if distance is not None:
        distance_text = f"**Distance from you:** {distance:.2f} km\n\n"
    
    return (
        f"**ID:** {property_id} | **Rent:** ₹{rent} | **Size:** {size} sqft | **Carpet Area:** {carpet_area} sqft\n\n"
        f"{distance_text}"
        f"**Title:** {title}\n\n"
        f"**Location:** {city}, {area}, {zone}\n"
        f"**Hub:** {location_hub} | **Type:** {property_type} | **Ownership:** {ownership}\n"
        f"**Floor:** {floor_no} of {total_floors}\n"
        f"**Security Deposit:** ₹{security_deposit} | **Brokerage:** {brokerage}\n"
        f"**Possession:** {possession_status} | **Age:** {property_age} years | **Negotiable:** {negotiable}\n"
        f"**Lock-in Period:** {lock_in_period} months | **Furnishing:** {furnishing_status}\n\n"
        f"**Facilities:** {facilities_str}\n"
        f"**Available Floors:** {floors_str}"
    )

# --- Function to filter properties by multiple criteria ---
def filter_properties(data, filters):
    """Filter properties based on multiple criteria (AND logic)."""
    filtered = data.copy()
    
    # Apply each filter separately (AND logic)
    for filter_type, value in filters.items():
        if filter_type == "city" and value:
            filtered = [p for p in filtered if p.get("city", "").lower() == value.lower()]
        
        elif filter_type == "area" and value:
            # Handle both single value and list of values
            if isinstance(value, list):
                filtered = [p for p in filtered if p.get("area", "").lower() in [v.lower() for v in value]]
            else:
                filtered = [p for p in filtered if p.get("area", "").lower() == value.lower()]
        
        elif filter_type == "zone" and value:
            # Handle both single value and list of values
            if isinstance(value, list):
                filtered = [p for p in filtered if p.get("zone", "").lower() in [v.lower() for v in value]]
            else:
                filtered = [p for p in filtered if p.get("zone", "").lower() == value.lower()]
        
        elif filter_type == "property_type" and value:
            # Handle both single value and list of values
            if isinstance(value, list):
                filtered = [p for p in filtered if p.get("property_type", "").lower() in [v.lower() for v in value]]
            else:
                filtered = [p for p in filtered if p.get("property_type", "").lower() == value.lower()]
        
        elif filter_type == "ownership" and value:
            # Handle both single value and list of values
            if isinstance(value, list):
                filtered = [p for p in filtered if p.get("ownership", "").lower() in [v.lower() for v in value]]
            else:
                filtered = [p for p in filtered if p.get("ownership", "").lower() == value.lower()]
        
        elif filter_type == "possession_status" and value:
            # Handle both single value and list of values
            if isinstance(value, list):
                filtered = [p for p in filtered if p.get("possession_status", "").lower() in [v.lower() for v in value]]
            else:
                filtered = [p for p in filtered if p.get("possession_status", "").lower() == value.lower()]
        
        elif filter_type == "location_hub" and value:
            # Handle both single value and list of values
            if isinstance(value, list):
                filtered = [p for p in filtered if p.get("location_hub", "").lower() in [v.lower() for v in value]]
            else:
                filtered = [p for p in filtered if p.get("location_hub", "").lower() == value.lower()]
        
        elif filter_type == "property_id" and value:
            filtered = [p for p in filtered if p.get("property_id", "").lower() == value.lower()]
        
        elif filter_type == "floor_no" and value:
            # Handle both single value and list of values
            if isinstance(value, list):
                filtered = [p for p in filtered if p.get("floor_no", "").lower() in [v.lower() for v in value]]
            else:
                filtered = [p for p in filtered if p.get("floor_no", "").lower() == value.lower()]
        
        elif filter_type == "min_rent" and value is not None:
            filtered = [p for p in filtered if p.get("rent_price", 0) >= value]
        
        elif filter_type == "max_rent" and value is not None:
            filtered = [p for p in filtered if p.get("rent_price", float('inf')) <= value]
        
        elif filter_type == "min_size" and value is not None:
            filtered = [p for p in filtered if p.get("size_in_sqft", 0) >= value]
        
        elif filter_type == "max_size" and value is not None:
            filtered = [p for p in filtered if p.get("size_in_sqft", float('inf')) <= value]
        
        elif filter_type == "min_carpet_area" and value is not None:
            filtered = [p for p in filtered if p.get("carpet_area_sqft", 0) >= value]
        
        elif filter_type == "max_carpet_area" and value is not None:
            filtered = [p for p in filtered if p.get("carpet_area_sqft", float('inf')) <= value]
        
        elif filter_type == "min_age" and value is not None:
            filtered = [p for p in filtered if p.get("property_age", 0) >= value]
        
        elif filter_type == "max_age" and value is not None:
            filtered = [p for p in filtered if p.get("property_age", float('inf')) <= value]
        
        elif filter_type == "min_security_deposit" and value is not None:
            filtered = [p for p in filtered if p.get("security_deposit", 0) >= value]
        
        elif filter_type == "max_security_deposit" and value is not None:
            filtered = [p for p in filtered if p.get("security_deposit", float('inf')) <= value]
        
        elif filter_type == "min_total_floors" and value is not None:
            filtered = [p for p in filtered if p.get("total_floors", 0) >= value]
        
        elif filter_type == "max_total_floors" and value is not None:
            filtered = [p for p in filtered if p.get("total_floors", float('inf')) <= value]
        
        elif filter_type == "min_lock_in_period" and value is not None:
            filtered = [p for p in filtered if p.get("charges", {}).get("lock_in_period_in_months", 0) >= value]
        
        elif filter_type == "max_lock_in_period" and value is not None:
            filtered = [p for p in filtered if p.get("charges", {}).get("lock_in_period_in_months", float('inf')) <= value]
        
        elif filter_type == "furnishing" and value:
            # value will be either "furnished" or "unfurnished"
            furnishing_value = 1 if value.lower() == "furnished" else 0
            filtered = [p for p in filtered if p.get("facilities", {}).get("furnishing") == furnishing_value]
        
        elif filter_type == "brokerage" and value:
            filtered = [p for p in filtered if p.get("brokerage", "").lower() == value.lower()]
        
        elif filter_type == "negotiable" and value:
            filtered = [p for p in filtered if p.get("negotiable", "").lower() == value.lower()]
        
        elif filter_type == "facilities" and value:
            # Normalize user facilities
            user_facilities = [normalize_facility_name(f) for f in value]
            # Filter properties that have ALL the selected facilities (AND logic)
            temp_filtered = []
            for p in filtered:
                facilities = p.get("facilities", {})
                # Check if the property has every facility in user_facilities
                if all(facilities.get(fac) == 1 for fac in user_facilities):
                    temp_filtered.append(p)
            filtered = temp_filtered
        
        elif filter_type == "floor" and value:
            # Normalize user floor selection
            user_floor = normalize_facility_name(value)
            # Filter properties that have the selected floor available
            filtered = [p for p in filtered if p.get("floor_availability", {}).get(user_floor) == 1]
    
    return filtered

# --- Function to get unique values for a field ---
def get_unique_values(data, field):
    """Get unique values for a specific field from the data."""
    values = set()
    for p in data:
        value = p.get(field)
        if value:
            values.add(str(value))
    return sorted(values)

# --- Function to get all available facilities ---
def get_all_facilities(data):
    """Get all facilities that are available in any property."""
    facilities = set()
    for p in data:
        for fac, val in p.get("facilities", {}).items():
            if val == 1:
                facilities.add(fac.replace('_', ' ').title())
    return sorted(facilities)

# --- Function to get all available floors ---
def get_all_floors(data):
    """Get all floors that are available in any property."""
    floors = set()
    for p in data:
        for floor, val in p.get("floor_availability", {}).items():
            if val == 1:
                floors.add(floor.replace('_', ' ').title())
    return sorted(floors)

# --- Function to compare properties side by side ---
def compare_properties_side_by_side(data, property_ids):
    """Compare multiple properties side by side in table format."""
    selected = [p for p in data if str(p.get("property_id", "")).lower() in property_ids]
    
    if not selected:
        st.warning("⚠️ No properties found for the given IDs.")
        return
    
    # Collect all possible comparison keys
    comparison_keys = set()
    for p in selected:
        comparison_keys.update(p.keys())
        if isinstance(p.get("facilities"), dict):
            comparison_keys.update([f"Facility: {k}" for k in p["facilities"].keys()])
        if isinstance(p.get("floor_availability"), dict):
            comparison_keys.update([f"Floor: {k}" for k in p["floor_availability"].keys()])
    
    # Always show Property ID and Rent Price first for property comparison
    display_order = ["property_id", "rent_price"]
    remaining_keys = sorted(k for k in comparison_keys if k not in display_order)
    comparison_keys = display_order + remaining_keys
    
    # Build rows
    rows = []
    for key in comparison_keys:
        row = [key.replace('_', ' ').title()]
        for p in selected:
            value = "N/A"
            if key.startswith("Facility: "):
                fname = key.split(": ", 1)[1]
                value = "✅" if p.get("facilities", {}).get(fname) == 1 else "❌"
            elif key.startswith("Floor: "):
                fname = key.split(": ", 1)[1]
                value = "✅" if p.get("floor_availability", {}).get(fname) == 1 else "❌"
            else:
                value = p.get(key, "N/A")
            
            # Format some values
            if key in ["rent_price", "security_deposit"]:
                value = f"₹{value}" if value != "N/A" else value
            elif key in ["size_in_sqft", "carpet_area_sqft"]:
                value = f"{value} sqft" if value != "N/A" else value
            elif key == "brokerage":
                value = "Yes" if value == "yes" else "No"
            
            row.append(value)
        rows.append(row)
    
    headers = ["Attribute"] + [f"ID {p.get('property_id', 'N/A')}" for p in selected]
    
    # Create a DataFrame for better display
    df = pd.DataFrame(rows, columns=headers)
    st.dataframe(df.style.set_properties(**{'text-align': 'left'}), use_container_width=True)

# --- Function to create property map ---
def create_property_map(properties, user_location=None):
    """Create a Folium map with property markers for Nagpur."""
    # Default to Nagpur coordinates
    nagpur_lat, nagpur_lon = 21.1458, 79.0882
    
    # Create a map centered around Nagpur
    m = folium.Map(location=[nagpur_lat, nagpur_lon], zoom_start=12)
    
    # Add tile layer
    folium.TileLayer('OpenStreetMap').add_to(m)
    
    # Add user location marker if provided
    if user_location:
        folium.Marker(
            location=user_location,
            popup="Your Location",
            tooltip="You are here",
            icon=folium.Icon(color='black', icon='user')
        ).add_to(m)
    
    # Calculate distances if user location is provided
    distances = []
    if user_location:
        user_lat, user_lon = user_location
        for prop in properties:
            # Try to get coordinates from property data
            if "latitude" in prop and "longitude" in prop:
                prop_lat, prop_lon = prop["latitude"], prop["longitude"]
            else:
                # Try to geocode the area name within Nagpur
                coords = geocode_area(prop.get("area", "N/A"))
                if coords:
                    prop_lat, prop_lon = coords
                else:
                    # Skip if we can't get coordinates
                    continue
            
            # Calculate distance using Haversine formula
            distance = haversine_distance(user_lat, user_lon, prop_lat, prop_lon)
            distances.append(distance)
            prop["distance_from_user"] = distance
        
        # Calculate average distance
        avg_distance = sum(distances) / len(distances) if distances else 0
    else:
        avg_distance = None
    
    # Add property markers
    for prop in properties:
        property_id = prop.get('property_id', 'N/A')
        rent_price = prop.get('rent_price', 'N/A')
        area = prop.get('area', 'N/A')
        size = prop.get('size_in_sqft', 'Unknown')
        property_type = prop.get('property_type', 'N/A')
        
        # Get coordinates for the property
        if "latitude" in prop and "longitude" in prop:
            lat, lon = prop["latitude"], prop["longitude"]
        else:
            # Try to geocode the area name within Nagpur
            coords = geocode_area(area)
            if coords:
                lat, lon = coords
            else:
                # Skip if we can't get coordinates
                continue
        
        # Create popup text
        distance_text = ""
        marker_color = 'blue'
        
        if user_location and "distance_from_user" in prop:
            distance = prop["distance_from_user"]
            distance_text = f"<b>Distance:</b> {distance:.2f} km"
            
            # Set marker color based on distance compared to average
            if avg_distance is not None:
                if distance < avg_distance:
                    marker_color = 'blue'  # Below average (closer)
                else:
                    marker_color = 'red'   # Above average (farther)
        
        popup_text = f"""
        <b>ID:</b> {property_id}<br>
        <b>Rent:</b> ₹{rent_price}<br>
        <b>Area:</b> {area}<br>
        <b>Size:</b> {size} sqft<br>
        <b>Type:</b> {property_type}<br>
        {distance_text}
        """
        
        # Add marker to the map
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=250),
            tooltip=f"ID: {property_id} | Rent: ₹{rent_price}",
            icon=folium.Icon(color=marker_color, icon='home')
        ).add_to(m)
    
    # Add legend for distance colors
    if user_location and avg_distance is not None:
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 150px; height: 80px; 
                    border:2px solid grey; z-index:9999; font-size:14px;
                    background-color:white;
                    ">&nbsp; <b>Distance Legend</b> <br>
                    &nbsp; <i class="fa fa-map-marker fa-2x" style="color:blue"></i> Below Average <br>
                    &nbsp; <i class="fa fa-map-marker fa-2x" style="color:red"></i> Above Average
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
    
    return m, avg_distance

# --- Main App ---
def main():
    # Header
    st.title("🏢 Commercial Property Search - Nagpur")
    st.markdown("Find your perfect commercial property in Nagpur with our advanced search and comparison tools")
    
    # Initialize session state for filters
    if 'filters' not in st.session_state:
        st.session_state.filters = {}
    
    # Initialize session state for user location
    if 'user_location' not in st.session_state:
        st.session_state.user_location = None
    
    # Initialize session state for filtered properties
    if 'filtered_properties' not in st.session_state:
        st.session_state.filtered_properties = properties_data
    
    # Get unique values for dropdowns
    cities = get_unique_values(properties_data, "city")
    areas = get_unique_values(properties_data, "area")
    zones = get_unique_values(properties_data, "zone")
    property_types = get_unique_values(properties_data, "property_type")
    ownerships = get_unique_values(properties_data, "ownership")
    possession_statuses = get_unique_values(properties_data, "possession_status")
    location_hubs = get_unique_values(properties_data, "location_hub")
    floor_nos = get_unique_values(properties_data, "floor_no")
    facilities = get_all_facilities(properties_data)
    floors = get_all_floors(properties_data)
    
    # Add Nagpur city badge at the top
    st.markdown("### 🔍 Search in Nagpur City")
    st.info("All search results are limited to properties within Nagpur city limits.")
    
    # User location section
    st.subheader("📍 Your Location")
    col1, col2 = st.columns(2)
    
    with col1:
        location_method = st.radio(
            "Select location method",
            ["Enter Manually", "Use Current Location"]
        )
    
    with col2:
        if location_method == "Enter Manually":
            lat_col, lon_col = st.columns(2)
            with lat_col:
                lat = st.number_input("Latitude", value=21.1458, format="%.6f")
            with lon_col:
                lon = st.number_input("Longitude", value=79.0882, format="%.6f")
            if st.button("Set Location"):
                st.session_state.user_location = (lat, lon)
                st.success("Location set successfully!")
        else:
            if st.button("Get My Current Location"):
                # This is a placeholder - in a real app, you would use browser geolocation
                # For demo purposes, we'll use a default location in Nagpur
                st.session_state.user_location = (21.1458, 79.0882)
                st.success("Using default Nagpur location. In a real app, this would get your current location.")
    
    # Display current user location if set
    if st.session_state.user_location:
        st.info(f"Your location: {st.session_state.user_location[0]:.6f}, {st.session_state.user_location[1]:.6f}")
    
    # Search Filters section
    st.subheader("🔍 Search Filters")
    search_mode = st.radio(
        "Select Search Mode",
        ["Simple Search", "Advanced Search", "Compare Properties"]
    )
    
    # Simple Search Mode
    if search_mode == "Simple Search":
        with st.expander("Quick Search Options", expanded=True):
            # Quick search options
            quick_search = st.selectbox(
                "Select search criteria",
                ["Rent Price", "Area", "Property Type", "Size"]
            )
            
            if quick_search == "Rent Price":
                rent_option = st.radio(
                    "Rent preference",
                    ["Below budget", "Above budget", "Exact amount", "Range"]
                )
                
                if rent_option == "Below budget":
                    max_rent = st.number_input("Maximum rent (₹)", min_value=1000, value=20000, step=1000)
                    st.session_state.filters["max_rent"] = max_rent
                elif rent_option == "Above budget":
                    min_rent = st.number_input("Minimum rent (₹)", min_value=1000, value=10000, step=1000)
                    st.session_state.filters["min_rent"] = min_rent
                elif rent_option == "Exact amount":
                    exact_rent = st.number_input("Exact rent (₹)", min_value=1000, value=15000, step=1000)
                    st.session_state.filters["min_rent"] = exact_rent
                    st.session_state.filters["max_rent"] = exact_rent
                else:  # Range
                    col1, col2 = st.columns(2)
                    with col1:
                        min_rent = st.number_input("Min rent (₹)", min_value=1000, value=10000, step=1000)
                    with col2:
                        max_rent = st.number_input("Max rent (₹)", min_value=1000, value=25000, step=1000)
                    st.session_state.filters["min_rent"] = min_rent
                    st.session_state.filters["max_rent"] = max_rent
                    
            elif quick_search == "Area":
                area = st.selectbox("Select area in Nagpur", ["Any"] + areas)
                if area != "Any":
                    st.session_state.filters["area"] = area
                
            elif quick_search == "Property Type":
                prop_type = st.selectbox("Select property type", ["Any"] + property_types)
                if prop_type != "Any":
                    st.session_state.filters["property_type"] = prop_type
                
            elif quick_search == "Size":
                size_option = st.radio(
                    "Size preference",
                    ["Below size", "Above size", "Exact size", "Range"]
                )
                
                if size_option == "Below size":
                    max_size = st.number_input("Maximum size (sqft)", min_value=100, value=2000, step=100)
                    st.session_state.filters["max_size"] = max_size
                elif size_option == "Above size":
                    min_size = st.number_input("Minimum size (sqft)", min_value=100, value=1000, step=100)
                    st.session_state.filters["min_size"] = min_size
                elif size_option == "Exact size":
                    exact_size = st.number_input("Exact size (sqft)", min_value=100, value=1500, step=100)
                    st.session_state.filters["min_size"] = exact_size
                    st.session_state.filters["max_size"] = exact_size
                else:  # Range
                    col1, col2 = st.columns(2)
                    with col1:
                        min_size = st.number_input("Min size (sqft)", min_value=100, value=1000, step=100)
                    with col2:
                        max_size = st.number_input("Max size (sqft)", min_value=100, value=2000, step=100)
                    st.session_state.filters["min_size"] = min_size
                    st.session_state.filters["max_size"] = max_size
    
    # Advanced Search Mode
    elif search_mode == "Advanced Search":
        with st.expander("Advanced Filter Options", expanded=True):
            # Display current property count
            st.markdown(f"📊 Showing all {len(st.session_state.filtered_properties)} properties")
            
            st.markdown("### Search Options:")
            
            # 1. Size (sqft)
            st.markdown("1. **Size (sqft)**")
            col1, col2 = st.columns(2)
            with col1:
                min_size = st.number_input("Min", min_value=0, value=0, key="min_size")
            with col2:
                max_size = st.number_input("Max", min_value=0, value=10000, key="max_size")
            
            # 2. Carpet Area (sqft)
            st.markdown("2. **Carpet Area (sqft)**")
            col1, col2 = st.columns(2)
            with col1:
                min_carpet = st.number_input("Min", min_value=0, value=0, key="min_carpet")
            with col2:
                max_carpet = st.number_input("Max", min_value=0, value=10000, key="max_carpet")
            
            # 3. Age of Property
            st.markdown("3. **Age of Property**")
            col1, col2 = st.columns(2)
            with col1:
                min_age = st.number_input("Min", min_value=0, value=0, key="min_age")
            with col2:
                max_age = st.number_input("Max", min_value=0, value=50, key="max_age")
            
            # 4. Brokerage
            st.markdown("4. **Brokerage**")
            brokerage = st.multiselect("Select", ["Yes", "No"], key="brokerage")
            
            # 5. Property ID
            st.markdown("5. **Property ID**")
            property_id = st.text_input("Enter ID", key="property_id")
            
            # 6. Furnishing
            st.markdown("6. **Furnishing**")
            furnishing = st.multiselect("Select", ["Furnished", "Unfurnished"], key="furnishing")
            
            # 7. Security Deposit
            st.markdown("7. **Security Deposit**")
            col1, col2 = st.columns(2)
            with col1:
                min_deposit = st.number_input("Min", min_value=0, value=0, key="min_deposit")
            with col2:
                max_deposit = st.number_input("Max", min_value=0, value=1000000, key="max_deposit")
            
            # 8. Rent Price
            st.markdown("8. **Rent Price**")
            col1, col2 = st.columns(2)
            with col1:
                min_rent = st.number_input("Min", min_value=0, value=0, key="min_rent")
            with col2:
                max_rent = st.number_input("Max", min_value=0, value=100000, key="max_rent")
            
            # 9. Area
            st.markdown("9. **Area**")
            area = st.multiselect("Select", areas, key="area")
            
            # 10. Zone
            st.markdown("10. **Zone**")
            zone = st.multiselect("Select", zones, key="zone")
            
            # 11. Floor Number
            st.markdown("11. **Floor Number**")
            floor_no = st.multiselect("Select", floor_nos, key="floor_no")
            
            # 12. Total Floors
            st.markdown("12. **Total Floors**")
            col1, col2 = st.columns(2)
            with col1:
                min_total_floors = st.number_input("Min", min_value=0, value=0, key="min_total_floors")
            with col2:
                max_total_floors = st.number_input("Max", min_value=0, value=100, key="max_total_floors")
            
            # 13. Property Type
            st.markdown("13. **Property Type**")
            property_type = st.multiselect("Select", property_types, key="property_type")
            
            # 14. Ownership
            st.markdown("14. **Ownership**")
            ownership = st.multiselect("Select", ownerships, key="ownership")
            
            # 15. Possession Status
            st.markdown("15. **Possession Status**")
            possession_status = st.multiselect("Select", possession_statuses, key="possession_status")
            
            # 16. Location Hub
            st.markdown("16. **Location Hub**")
            location_hub = st.multiselect("Select", location_hubs, key="location_hub")
            
            # 17. Facilities
            st.markdown("17. **Facilities**")
            selected_facilities = st.multiselect("Select", facilities, key="facilities")
            
            # 18. Lock-in Period
            st.markdown("18. **Lock-in Period**")
            col1, col2 = st.columns(2)
            with col1:
                min_lock_in = st.number_input("Min (months)", min_value=0, value=0, key="min_lock_in")
            with col2:
                max_lock_in = st.number_input("Max (months)", min_value=0, value=60, key="max_lock_in")
            
            # Action buttons
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Reset all filters"):
                    st.session_state.filters = {}
                    st.session_state.filtered_properties = properties_data
                    st.rerun()
            with col2:
                if st.button("View current properties"):
                    # Build filters dictionary
                    filters = {}
                    
                    # Size filters
                    if min_size > 0:
                        filters["min_size"] = min_size
                    if max_size > 0:
                        filters["max_size"] = max_size
                    
                    # Carpet area filters
                    if min_carpet > 0:
                        filters["min_carpet_area"] = min_carpet
                    if max_carpet > 0:
                        filters["max_carpet_area"] = max_carpet
                    
                    # Age filters
                    if min_age > 0:
                        filters["min_age"] = min_age
                    if max_age > 0:
                        filters["max_age"] = max_age
                    
                    # Brokerage filter
                    if brokerage:
                        # Handle multiple selections
                        if len(brokerage) == 1:
                            filters["brokerage"] = brokerage[0].lower()
                        else:
                            # For multiple selections, we need to handle it differently
                            # We'll create a custom filter for this
                            filters["brokerage_list"] = [b.lower() for b in brokerage]
                    
                    # Property ID filter
                    if property_id:
                        filters["property_id"] = property_id
                    
                    # Furnishing filter
                    if furnishing:
                        # Handle multiple selections
                        if len(furnishing) == 1:
                            filters["furnishing"] = furnishing[0].lower()
                        else:
                            # For multiple selections, we need to handle it differently
                            # We'll create a custom filter for this
                            filters["furnishing_list"] = [f.lower() for f in furnishing]
                    
                    # Security deposit filters
                    if min_deposit > 0:
                        filters["min_security_deposit"] = min_deposit
                    if max_deposit > 0:
                        filters["max_security_deposit"] = max_deposit
                    
                    # Rent filters
                    if min_rent > 0:
                        filters["min_rent"] = min_rent
                    if max_rent > 0:
                        filters["max_rent"] = max_rent
                    
                    # Area filter
                    if area:
                        filters["area"] = area
                    
                    # Zone filter
                    if zone:
                        filters["zone"] = zone
                    
                    # Floor number filter
                    if floor_no:
                        filters["floor_no"] = floor_no
                    
                    # Total floors filters
                    if min_total_floors > 0:
                        filters["min_total_floors"] = min_total_floors
                    if max_total_floors > 0:
                        filters["max_total_floors"] = max_total_floors
                    
                    # Property type filter
                    if property_type:
                        filters["property_type"] = property_type
                    
                    # Ownership filter
                    if ownership:
                        filters["ownership"] = ownership
                    
                    # Possession status filter
                    if possession_status:
                        filters["possession_status"] = possession_status
                    
                    # Location hub filter
                    if location_hub:
                        filters["location_hub"] = location_hub
                    
                    # Facilities filter
                    if selected_facilities:
                        filters["facilities"] = selected_facilities
                    
                    # Lock-in period filters
                    if min_lock_in > 0:
                        filters["min_lock_in_period"] = min_lock_in
                    if max_lock_in > 0:
                        filters["max_lock_in_period"] = max_lock_in
                    
                    # Apply filters
                    st.session_state.filters = filters
                    st.session_state.filtered_properties = filter_properties(properties_data, filters)
                    st.rerun()
    
    # Compare Properties Mode
    else:  # Compare Properties
        with st.expander("Property Comparison Options", expanded=True):
            property_ids = st.text_input(
                "Enter property IDs to compare (comma separated)",
                help="Example: Property_1, Property_2, Property_3"
            )
            if property_ids:
                st.session_state.filters["compare"] = property_ids
    
    # Apply filters button (for non-advanced search modes)
    if search_mode != "Advanced Search":
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Apply Filters", type="primary"):
                # Build filters dictionary
                filters = {}
                
                # Simple Search filters
                if search_mode == "Simple Search":
                    # Filters are already set in the session state
                    filters = st.session_state.filters.copy()
                
                # Apply filters
                st.session_state.filters = filters
                if search_mode == "Compare Properties" and "compare" in filters:
                    # For comparison mode, we don't filter the properties
                    st.session_state.filtered_properties = properties_data
                else:
                    st.session_state.filtered_properties = filter_properties(properties_data, filters)
        with col2:
            if st.button("Reset Filters"):
                st.session_state.filters = {}
                st.session_state.filtered_properties = properties_data
                st.rerun()
    
    # Display current filters
    if st.session_state.filters and search_mode != "Advanced Search":
        st.subheader("Active Filters")
        cols = st.columns(4)
        for i, (filter_type, value) in enumerate(st.session_state.filters.items()):
            if filter_type in ["min_rent", "max_rent", "min_size", "max_size", 
                              "min_carpet_area", "max_carpet_area", 
                              "min_age", "max_age", 
                              "min_security_deposit", "max_security_deposit",
                              "min_total_floors", "max_total_floors",
                              "min_lock_in_period", "max_lock_in_period"]:
                with cols[i % 4]:
                    st.text(f"{filter_type.replace('_', ' ').title()}: {value}")
            else:
                with cols[i % 4]:
                    st.text(f"{filter_type.replace('_', ' ').title()}: {value}")
    
    # Main content area
    if st.session_state.filters:
        # Handle comparison mode
        if search_mode == "Compare Properties" and "compare" in st.session_state.filters:
            property_ids = [pid.strip().lower() for pid in st.session_state.filters["compare"].split(",")]
            if len(property_ids) < 2:
                st.warning("⚠️ Please enter at least two Property IDs to compare.")
            else:
                st.header("Property Comparison")
                compare_properties_side_by_side(properties_data, property_ids)
        else:
            # Display results
            if not st.session_state.filtered_properties:
                st.warning("❌ No properties found matching your criteria in Nagpur.")
            else:
                st.success(f"✅ Found {len(st.session_state.filtered_properties)} properties matching your criteria in Nagpur.")
                
                # Create tabs for different views
                tab1, tab2, tab3 = st.tabs(["List View", "Map View", "Analytics"])
                
                with tab1:
                    # Group by property type
                    grouped_results = defaultdict(list)
                    for prop in st.session_state.filtered_properties:
                        property_type = prop.get("property_type", "Other/Unspecified Type")
                        grouped_results[property_type].append(prop)
                    
                    # Display results grouped by property type
                    for prop_type, props in grouped_results.items():
                        st.subheader(f"🏠 Property Type: {str(prop_type).title()} ({len(props)} results)")
                        
                        # Create columns for better layout
                        cols = st.columns(2)
                        for i, prop in enumerate(props):
                            # Get distance if user location is set
                            distance = prop.get("distance_from_user", None) if st.session_state.user_location else None
                            
                            with cols[i % 2]:
                                with st.expander(f"ID: {prop.get('property_id', 'N/A')} | Rent: ₹{prop.get('rent_price', 'N/A')}"):
                                    st.markdown(format_property(prop, distance))
                
                with tab2:
                    st.subheader("Property Locations in Nagpur")
                    
                    # Create and display the map
                    try:
                        property_map, avg_distance = create_property_map(st.session_state.filtered_properties, st.session_state.user_location)
                        folium_static(property_map, width=700, height=500)
                        
                        # Add map controls explanation
                        st.markdown("""
                        **Map Controls:**
                        - Click on markers to see property details
                        - Zoom in/out using the + and - buttons or mouse wheel
                        - Drag to move around the map
                        - Your location is shown with a black marker
                        - Property markers are color-coded by distance:
                          - Blue: Below average distance from you
                          - Red: Above average distance from you
                        """)
                        
                        # Display average distance
                        if avg_distance is not None:
                            st.info(f"📏 Average distance from your location: {avg_distance:.2f} km")
                    except Exception as e:
                        st.error(f"Error displaying map: {str(e)}")
                        st.info("Please check if you have a stable internet connection for map loading.")
                
                with tab3:
                    st.subheader("Property Analytics for Nagpur")
                    
                    # Create analytics visualizations
                    if st.session_state.filtered_properties:
                        # Convert to DataFrame for easier analysis
                        df = pd.DataFrame(st.session_state.filtered_properties)
                        
                        # Rent distribution
                        st.subheader("Rent Distribution in Nagpur")
                        fig_rent = px.histogram(
                            df, 
                            x="rent_price", 
                            nbins=20,
                            title="Distribution of Property Rents in Nagpur",
                            labels={"rent_price": "Rent (₹)", "count": "Number of Properties"}
                        )
                        st.plotly_chart(fig_rent, use_container_width=True)
                        
                        # Property types
                        st.subheader("Property Types in Nagpur")
                        type_counts = df["property_type"].value_counts()
                        fig_types = px.pie(
                            values=type_counts.values,
                            names=type_counts.index,
                            title="Distribution of Property Types in Nagpur"
                        )
                        st.plotly_chart(fig_types, use_container_width=True)
                        
                        # Area distribution
                        if "area" in df.columns:
                            st.subheader("Properties by Area in Nagpur")
                            area_counts = df["area"].value_counts()
                            fig_area = px.bar(
                                x=area_counts.index,
                                y=area_counts.values,
                                labels={"x": "Area", "y": "Number of Properties"},
                                title="Properties by Area in Nagpur"
                            )
                            st.plotly_chart(fig_area, use_container_width=True)
                        
                        # Size vs Rent scatter plot
                        st.subheader("Size vs Rent")
                        fig_scatter = px.scatter(
                            df,
                            x="size_in_sqft",
                            y="rent_price",
                            color="property_type",
                            hover_name="listing_title",
                            labels={"size_in_sqft": "Size (sqft)", "rent_price": "Rent (₹)"},
                            title="Size vs Rent by Property Type"
                        )
                        st.plotly_chart(fig_scatter, use_container_width=True)
                        
                        # Property age distribution
                        st.subheader("Property Age Distribution")
                        fig_age = px.histogram(
                            df,
                            x="property_age",
                            nbins=15,
                            title="Distribution of Property Ages",
                            labels={"property_age": "Age (years)", "count": "Number of Properties"}
                        )
                        st.plotly_chart(fig_age, use_container_width=True)
                        
                        # Furnishing status
                        furnishing_counts = {"Furnished": 0, "Unfurnished": 0}
                        for prop in st.session_state.filtered_properties:
                            if prop.get("facilities", {}).get("furnishing") == 1:
                                furnishing_counts["Furnished"] += 1
                            else:
                                furnishing_counts["Unfurnished"] += 1
                        
                        st.subheader("Furnishing Status")
                        fig_furnishing = px.pie(
                            values=list(furnishing_counts.values()),
                            names=list(furnishing_counts.keys()),
                            title="Distribution of Furnishing Status"
                        )
                        st.plotly_chart(fig_furnishing, use_container_width=True)
                        
                        # Distance distribution if user location is set
                        if st.session_state.user_location and "distance_from_user" in df.columns:
                            st.subheader("Distance Distribution from Your Location")
                            fig_distance = px.histogram(
                                df,
                                x="distance_from_user",
                                nbins=15,
                                title="Distribution of Property Distances from Your Location",
                                labels={"distance_from_user": "Distance (km)", "count": "Number of Properties"}
                            )
                            # Add average distance line
                            avg_distance = df["distance_from_user"].mean()
                            fig_distance.add_vline(x=avg_distance, line_dash="dash", line_color="red",
                                                 annotation_text=f"Avg: {avg_distance:.2f} km")
                            st.plotly_chart(fig_distance, use_container_width=True)
                            
                            # Distance bar graph with average line
                            st.subheader("Property Distance from Your Location")
                            # Create a bar chart for each property's distance
                            bar_data = df[['property_id', 'distance_from_user']].copy()
                            bar_data['property_label'] = 'ID: ' + bar_data['property_id']
                            
                            # Create a bar chart with conditional coloring
                            fig_bar = go.Figure()
                            # Add bars below average in blue
                            below_avg = bar_data[bar_data['distance_from_user'] <= avg_distance]
                            fig_bar.add_trace(go.Bar(
                                x=below_avg['property_label'],
                                y=below_avg['distance_from_user'],
                                name='Below Average',
                                marker_color='blue'
                            ))
                            # Add bars above average in red
                            above_avg = bar_data[bar_data['distance_from_user'] > avg_distance]
                            fig_bar.add_trace(go.Bar(
                                x=above_avg['property_label'],
                                y=above_avg['distance_from_user'],
                                name='Above Average',
                                marker_color='red'
                            ))
                            
                            fig_bar.update_layout(
                                title=f"Property Distance from Your Location (Average: {avg_distance:.2f} km)",
                                xaxis_title="Property ID",
                                yaxis_title="Distance (km)",
                                barmode='group'
                            )
                            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        # Display welcome message and sample properties
        st.header("Welcome to Commercial Property Search - Nagpur")
        st.markdown("""
        Use the filters above to find properties that match your criteria in Nagpur. 
        You can search by various attributes like rent, area, property type, and more.
        
        **Features:**
        - Simple and advanced search modes
        - Property comparison tool
        - Visual analytics
        - Interactive map view with distance calculations
        - Detailed property information
        - Facilities and nearby amenities filtering
        """)
        
        # Display some sample properties
        st.subheader("Featured Properties in Nagpur")
        sample_properties = properties_data[:4] if len(properties_data) >= 4 else properties_data
        
        cols = st.columns(2)
        for i, prop in enumerate(sample_properties):
            with cols[i % 2]:
                with st.expander(f"ID: {prop.get('property_id', 'N/A')} | Rent: ₹{prop.get('rent_price', 'N/A')}"):
                    st.markdown(format_property(prop))

# Add JavaScript for geolocation
st.components.v1.html("""
<script>
window.addEventListener('message', function(event) {
    if (event.data.type === 'geolocation') {
        // Send the geolocation data to Streamlit
        fetch('/_st_geolocation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(event.data.data)
        });
    }
});
</script>
""", height=0)

# Add a hidden endpoint to receive geolocation data
@st.cache_data
def handle_geolocation(data):
    st.session_state.geolocation_data = data

if __name__ == "__main__":
    main()
