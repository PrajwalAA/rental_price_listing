import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import re

# Set page configuration
st.set_page_config(
    page_title="Commercial Property Search",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load properties from JSON file ---
@st.cache_data
def load_properties():
    try:
        with open("commercial_data.json", "r") as f:
            return json.load(f)
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

# --- Function to format property details ---
def format_property(prop):
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
    
    return {
        "ID": property_id,
        "Title": title,
        "Location": f"{city}, {area}, {zone}",
        "Hub": location_hub,
        "Type": property_type,
        "Ownership": ownership,
        "Size (sqft)": size,
        "Carpet Area (sqft)": carpet_area,
        "Floor": f"{floor_no} of {total_floors}",
        "Rent (₹)": rent,
        "Security Deposit (₹)": security_deposit,
        "Brokerage": brokerage,
        "Possession": possession_status,
        "Age (years)": property_age,
        "Negotiable": negotiable,
        "Lock-in Period (months)": lock_in_period,
        "Furnishing": furnishing_status,
        "Facilities": facilities_str,
        "Available Floors": floors_str
    }

# --- Function to filter properties by multiple criteria ---
def filter_properties(data, filters):
    """Filter properties based on multiple criteria (AND logic)."""
    filtered = data.copy()
    
    # Apply each filter separately (AND logic)
    for filter_type, value in filters.items():
        if filter_type == "city" and value:
            filtered = [p for p in filtered if p.get("city", "").lower() == value.lower()]
        
        elif filter_type == "area" and value:
            filtered = [p for p in filtered if p.get("area", "").lower() == value.lower()]
        
        elif filter_type == "zone" and value:
            filtered = [p for p in filtered if p.get("zone", "").lower() == value.lower()]
        
        elif filter_type == "property_type" and value:
            filtered = [p for p in filtered if p.get("property_type", "").lower() == value.lower()]
        
        elif filter_type == "ownership" and value:
            filtered = [p for p in filtered if p.get("ownership", "").lower() == value.lower()]
        
        elif filter_type == "possession_status" and value:
            filtered = [p for p in filtered if p.get("possession_status", "").lower() == value.lower()]
        
        elif filter_type == "location_hub" and value:
            filtered = [p for p in filtered if p.get("location_hub", "").lower() == value.lower()]
        
        elif filter_type == "property_id" and value:
            filtered = [p for p in filtered if p.get("property_id", "").lower() == value.lower()]
        
        elif filter_type == "floor_no" and value:
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

# --- Main App ---
def main():
    # Header
    st.title("🏢 Commercial Property Search")
    st.markdown("Find your perfect commercial property with our advanced search filters")
    
    # Initialize session state for filters
    if 'filters' not in st.session_state:
        st.session_state.filters = {}
    
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
    
    # Sidebar for filters
    st.sidebar.header("🔍 Search Filters")
    
    # 1. Size (sqft)
    st.sidebar.subheader("1. Size (sqft)")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_size = st.number_input("Min Size", min_value=0, value=0, key="min_size")
    with col2:
        max_size = st.number_input("Max Size", min_value=0, value=10000, key="max_size")
    
    # 2. Carpet Area (sqft)
    st.sidebar.subheader("2. Carpet Area (sqft)")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_carpet = st.number_input("Min Carpet", min_value=0, value=0, key="min_carpet")
    with col2:
        max_carpet = st.number_input("Max Carpet", min_value=0, value=10000, key="max_carpet")
    
    # 3. Age of Property
    st.sidebar.subheader("3. Age of Property")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_age = st.number_input("Min Age", min_value=0, value=0, key="min_age")
    with col2:
        max_age = st.number_input("Max Age", min_value=0, value=50, key="max_age")
    
    # 4. Brokerage
    st.sidebar.subheader("4. Brokerage")
    brokerage = st.sidebar.selectbox("Brokerage", ["Any", "Yes", "No"], key="brokerage")
    
    # 5. Property ID
    st.sidebar.subheader("5. Property ID")
    property_id = st.sidebar.text_input("Property ID", key="property_id")
    
    # 6. Furnishing
    st.sidebar.subheader("6. Furnishing")
    furnishing = st.sidebar.selectbox("Furnishing", ["Any", "Furnished", "Unfurnished"], key="furnishing")
    
    # 7. Security Deposit
    st.sidebar.subheader("7. Security Deposit")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_deposit = st.number_input("Min Deposit", min_value=0, value=0, key="min_deposit")
    with col2:
        max_deposit = st.number_input("Max Deposit", min_value=0, value=1000000, key="max_deposit")
    
    # 8. Rent Price
    st.sidebar.subheader("8. Rent Price")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_rent = st.number_input("Min Rent", min_value=0, value=0, key="min_rent")
    with col2:
        max_rent = st.number_input("Max Rent", min_value=0, value=100000, key="max_rent")
    
    # 9. Area
    st.sidebar.subheader("9. Area")
    area = st.sidebar.selectbox("Area", ["Any"] + areas, key="area")
    
    # 10. Zone
    st.sidebar.subheader("10. Zone")
    zone = st.sidebar.selectbox("Zone", ["Any"] + zones, key="zone")
    
    # 11. Floor Number
    st.sidebar.subheader("11. Floor Number")
    floor_no = st.sidebar.selectbox("Floor Number", ["Any"] + floor_nos, key="floor_no")
    
    # 12. Total Floors
    st.sidebar.subheader("12. Total Floors")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_total_floors = st.number_input("Min Floors", min_value=0, value=0, key="min_total_floors")
    with col2:
        max_total_floors = st.number_input("Max Floors", min_value=0, value=100, key="max_total_floors")
    
    # 13. Property Type
    st.sidebar.subheader("13. Property Type")
    property_type = st.sidebar.selectbox("Property Type", ["Any"] + property_types, key="property_type")
    
    # 14. Ownership
    st.sidebar.subheader("14. Ownership")
    ownership = st.sidebar.selectbox("Ownership", ["Any"] + ownerships, key="ownership")
    
    # 15. Possession Status
    st.sidebar.subheader("15. Possession Status")
    possession_status = st.sidebar.selectbox("Possession Status", ["Any"] + possession_statuses, key="possession_status")
    
    # 16. Location Hub
    st.sidebar.subheader("16. Location Hub")
    location_hub = st.sidebar.selectbox("Location Hub", ["Any"] + location_hubs, key="location_hub")
    
    # 17. Facilities
    st.sidebar.subheader("17. Facilities")
    selected_facilities = st.sidebar.multiselect("Select Facilities", facilities, key="facilities")
    
    # 18. Lock-in Period
    st.sidebar.subheader("18. Lock-in Period")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_lock_in = st.number_input("Min Period (months)", min_value=0, value=0, key="min_lock_in")
    with col2:
        max_lock_in = st.number_input("Max Period (months)", min_value=0, value=60, key="max_lock_in")
    
    # Apply filters button
    if st.sidebar.button("Apply Filters", type="primary"):
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
        if brokerage != "Any":
            filters["brokerage"] = brokerage.lower()
        
        # Property ID filter
        if property_id:
            filters["property_id"] = property_id
        
        # Furnishing filter
        if furnishing != "Any":
            filters["furnishing"] = furnishing.lower()
        
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
        if area != "Any":
            filters["area"] = area
        
        # Zone filter
        if zone != "Any":
            filters["zone"] = zone
        
        # Floor number filter
        if floor_no != "Any":
            filters["floor_no"] = floor_no
        
        # Total floors filters
        if min_total_floors > 0:
            filters["min_total_floors"] = min_total_floors
        if max_total_floors > 0:
            filters["max_total_floors"] = max_total_floors
        
        # Property type filter
        if property_type != "Any":
            filters["property_type"] = property_type
        
        # Ownership filter
        if ownership != "Any":
            filters["ownership"] = ownership
        
        # Possession status filter
        if possession_status != "Any":
            filters["possession_status"] = possession_status
        
        # Location hub filter
        if location_hub != "Any":
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
    
    # Reset filters button
    if st.sidebar.button("Reset Filters"):
        st.session_state.filters = {}
        st.session_state.filtered_properties = properties_data
        st.rerun()
    
    # Display current filters
    if st.session_state.filters:
        st.sidebar.subheader("Active Filters")
        for filter_type, value in st.session_state.filters.items():
            if filter_type in ["min_rent", "max_rent", "min_size", "max_size", 
                              "min_carpet_area", "max_carpet_area", 
                              "min_age", "max_age", 
                              "min_security_deposit", "max_security_deposit",
                              "min_total_floors", "max_total_floors",
                              "min_lock_in_period", "max_lock_in_period"]:
                st.sidebar.text(f"{filter_type.replace('_', ' ').title()}: {value}")
            else:
                st.sidebar.text(f"{filter_type.replace('_', ' ').title()}: {value}")
    
    # Main content area
    st.subheader(f"Search Results ({len(st.session_state.filtered_properties)} properties found)")
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["List View", "Analytics"])
    
    with tab1:
        # Display properties in a table
        if st.session_state.filtered_properties:
            # Format properties for display
            formatted_properties = [format_property(p) for p in st.session_state.filtered_properties]
            
            # Create a DataFrame for better display
            df = pd.DataFrame(formatted_properties)
            
            # Display the DataFrame
            st.dataframe(df, use_container_width=True)
            
            # Option to view full details
            with st.expander("View Full Details"):
                for i, prop in enumerate(st.session_state.filtered_properties):
                    st.markdown(f"### Property {i+1}: {prop.get('listing_title', 'N/A')}")
                    
                    # Format property details
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
                    
                    st.markdown(f"""
                    **ID:** {property_id}  
                    **Title:** {title}  
                    **Location:** {city}, {area}, {zone}  
                    **Hub:** {location_hub} | **Type:** {property_type} | **Ownership:** {ownership}  
                    **Size:** {size} sqft | **Carpet Area:** {carpet_area} sqft  
                    **Floor:** {floor_no} of {total_floors}  
                    **Rent:** ₹{rent} | **Security Deposit:** ₹{security_deposit}  
                    **Brokerage:** {brokerage} | **Possession:** {possession_status}  
                    **Age:** {property_age} years | **Negotiable:** {negotiable}  
                    **Lock-in Period:** {lock_in_period} months  
                    **Furnishing:** {furnishing_status}  
                    **Facilities:** {facilities_str}  
                    **Available Floors:** {floors_str}
                    """)
                    st.markdown("---")
        else:
            st.warning("No properties found matching your criteria. Try adjusting your filters.")
    
    with tab2:
        # Display analytics
        if st.session_state.filtered_properties:
            st.subheader("Property Analytics")
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(st.session_state.filtered_properties)
            
            # Rent distribution
            st.subheader("Rent Distribution")
            fig_rent = px.histogram(
                df, 
                x="rent_price", 
                nbins=20,
                title="Distribution of Property Rents",
                labels={"rent_price": "Rent (₹)", "count": "Number of Properties"}
            )
            st.plotly_chart(fig_rent, use_container_width=True)
            
            # Property types
            st.subheader("Property Types")
            type_counts = df["property_type"].value_counts()
            fig_types = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title="Distribution of Property Types"
            )
            st.plotly_chart(fig_types, use_container_width=True)
            
            # Area distribution
            if "area" in df.columns:
                st.subheader("Properties by Area")
                area_counts = df["area"].value_counts()
                fig_area = px.bar(
                    x=area_counts.index,
                    y=area_counts.values,
                    labels={"x": "Area", "y": "Number of Properties"},
                    title="Properties by Area"
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
        else:
            st.warning("No data available for analytics. Please apply filters to see results.")

if __name__ == "__main__":
    main()
