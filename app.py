import streamlit as st
import json
import re
from collections import defaultdict
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
import requests
import time

# Set page configuration
st.set_page_config(
    page_title="Property Search Assistant - Nagpur",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load properties from JSON file ---
@st.cache_data
def load_properties():
    try:
        with open("property_data.json", "r") as f:
            properties = json.load(f)
            # Filter properties to only include those in Nagpur
            nagpur_properties = [p for p in properties if p.get("City", "").lower() == "nagpur" or p.get("Area", "").lower().find("nagpur") != -1]
            return nagpur_properties
    except FileNotFoundError:
        st.error("Error: 'property_data.json' not found. Please ensure the file exists.")
        return []
    except json.JSONDecodeError:
        st.error("Error: Could not decode 'property_data.json'. Please check its format.")
        return []

properties_data = load_properties()

# --- Geocoding function to get coordinates from area name ---
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

# --- Helper functions for normalization ---
def normalize_area_name(area_name):
    return str(area_name).replace(" ", "").lower().strip()

def normalize_zone_name(zone_name):
    return str(zone_name).replace(" ", "").lower().strip()

def normalize_facility_name(facility_name):
    return str(facility_name).replace(" ", "_").lower().strip()

def normalize_amenity_name(name):
    return str(name).replace(" ", "_").lower().strip()

def normalize_room_name(room_name):
    return str(room_name).replace(" ", "").lower().strip()

def normalize_property_type_name(prop_type):
    return str(prop_type).lower().strip()

def get_numeric_value(value):
    """Extract integer from strings like '800 sqft', '10 years', etc.
       Returns None if no number is found."""
    if not value:
        return None
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None

# --- Dynamically get all unique values from the dataset ---
ALL_AREAS = sorted(
    list(set(normalize_area_name(p.get("Area", "N/A")) for p in properties_data))
)

ALL_ZONES = sorted(
    list(set(normalize_zone_name(p.get("Zone", "N/A")) for p in properties_data))
)

ALL_FACILITIES = []
for p in properties_data:
    if "Facilities" in p and isinstance(p["Facilities"], dict):
        ALL_FACILITIES = sorted(list(p["Facilities"].keys()))
        break

ALL_NEARBY_AMENITIES = []
for p in properties_data:
    if "Nearby_Amenities" in p and isinstance(p["Nearby_Amenities"], dict):
        ALL_NEARBY_AMENITIES = sorted(list(p["Nearby_Amenities"].keys()))
        break

ALL_ROOM_TYPES = sorted(
    list(set(normalize_room_name(p.get("Room_Details", {}).get("Rooms", "N/A"))
             for p in properties_data if p.get("Room_Details", {}).get("Rooms")))
)

ALL_PROPERTY_TYPES = sorted(
    list(set(normalize_property_type_name(p.get("Room_Details", {}).get("Type", "N/A"))
             for p in properties_data if p.get("Room_Details", {}).get("Type")))
)

# --- Comparison Function ---
def compare_properties_side_by_side(data, property_ids):
    """
    Compare multiple properties side by side in table format.
    """
    selected = [p for p in data if str(p.get("property_id", "")).lower() in property_ids]

    if not selected:
        st.warning("⚠️ No properties found for the given IDs.")
        return

    # Collect all possible comparison keys
    comparison_keys = set()
    for p in selected:
        comparison_keys.update(p.keys())
        if isinstance(p.get("Facilities"), dict):
            comparison_keys.update([f"Facility: {k}" for k in p["Facilities"].keys()])
        if isinstance(p.get("Nearby_Amenities"), dict):
            comparison_keys.update([f"Amenity: {k}" for k in p["Nearby_Amenities"].keys()])
        # Also include nested Room_Details keys
        if isinstance(p.get("Room_Details"), dict):
            comparison_keys.update([f"Room Details: {k}" for k in p["Room_Details"].keys()])

    # Always show Property ID and Rent Price first for property comparison
    display_order = ["property_id", "Rent_Price"]
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
                value = "✅" if p.get("Facilities", {}).get(fname) == 1 else "❌"
            elif key.startswith("Amenity: "):
                aname = key.split(": ", 1)[1]
                value = "✅" if p.get("Nearby_Amenities", {}).get(aname) == 1 else "❌"
            elif key.startswith("Room Details: "):
                rdname = key.split(": ", 1)[1]
                value = p.get("Room_Details", {}).get(rdname, "N/A")
            else:
                value = p.get(key, "N/A")

            # Format some values
            if key in ["Rent_Price", "Security_Deposite"]:
                value = f"₹{value}" if value != "N/A" else value
            elif key in ["Size_In_Sqft", "Carpet_Area_Sqft"]:
                value = f"{value} sqft" if value != "N/A" else value
            elif key == "Brokerage":
                value = "Yes" if value == "yes" else "No"

            row.append(value)
        rows.append(row)

    headers = ["Attribute"] + [f"ID {p.get('property_id', 'N/A')}" for p in selected]
    
    # Create a DataFrame for better display
    df = pd.DataFrame(rows, columns=headers)
    st.dataframe(df.style.set_properties(**{'text-align': 'left'}), use_container_width=True)

# --- Filtering logic ---
def filter_properties(user_input, field, data):
    filtered_properties = []
    data_field_map = {
        "size": "Size_In_Sqft", "carpet": "Carpet_Area_Sqft", "age": "Property_Age", "brokerage": "Brokerage",
        "furnishing": "Furnishing_Status", "amenities": "Number_Of_Amenities", "security": "Security_Deposite", "rent": "Rent_Price",
        "area": "Area", "zone": "Zone", "bedrooms": "Bedrooms", "bathrooms": "Bathrooms", "balcony": "Balcony",
        "floor_no": "Floor_No", "total_floors": "Total_floors_In_Building", "maintenance": "Maintenance_Charge",
        "recommended_for": "Recommended_For", "water_supply": "Water_Supply_Type", "society_type": "Society_Type",
        "road_connectivity": "Road_Connectivity", "facilities": "Facilities", "nearby_amenities": "Nearby_Amenities",
        "room_type": "Room_Details", "property_type": "Room_Details", "id": "Property_ID"
    }
    data_field = data_field_map.get(field)
    if not data_field:
        return []

    normalized_user_input = user_input.lower().strip()
    if field in ["brokerage", "furnishing", "maintenance", "recommended_for", "water_supply", "society_type"]:
        filtered_properties = [p for p in data if str(p.get(data_field, "N/A")).lower() == normalized_user_input]
    
    elif field == "facilities":
        user_facilities = [normalize_facility_name(f) for f in user_input.split(',')]
        filtered_properties = [p for p in data if all(
            normalize_facility_name(k) in user_facilities and v == 1
            for k, v in p.get("Facilities", {}).items() if k
        )]

    elif field == "nearby_amenities":
        user_amenities = [normalize_amenity_name(f) for f in user_input.split(',')]
        filtered_properties = [p for p in data if all(
            normalize_amenity_name(k) in user_amenities and v == 1
            for k, v in p.get("Nearby_Amenities", {}).items() if k
        )]

    elif field == "room_type":
        filtered_properties = [p for p in data if normalize_room_name(p.get("Room_Details", {}).get("Rooms", "")) == normalized_user_input]

    elif field == "property_type":
        filtered_properties = [p for p in data if normalize_property_type_name(p.get("Room_Details", {}).get("Type", "")) == normalized_user_input]

    elif field == "area":
        filtered_properties = [p for p in data if normalize_area_name(p.get("Area", "N/A")) == normalize_area_name(user_input)]

    elif field == "zone":
        filtered_properties = [p for p in data if normalize_zone_name(p.get("Zone", "N/A")) == normalize_zone_name(user_input)]
        
    elif field == "id":
        property_ids = [pid.strip().lower() for pid in user_input.split(",")]
        filtered_properties = [p for p in data if str(p.get("Property_ID", "")).lower() in property_ids]
    
    else:
        try:
            val = get_numeric_value(user_input)
            
            if user_input.startswith("below"):
                filtered_properties = [
                    p for p in data
                    if get_numeric_value(p.get(data_field)) is not None
                    and get_numeric_value(p.get(data_field)) < val
                ]
            elif user_input.startswith("above"):
                filtered_properties = [
                    p for p in data
                    if get_numeric_value(p.get(data_field)) is not None
                    and get_numeric_value(p.get(data_field)) > val
                ]
            elif user_input.startswith("between"):
                nums = re.findall(r"\d+", user_input)
                if len(nums) == 2:
                    low, high = int(nums[0]), int(nums[1])
                    filtered_properties = [
                        p for p in data
                        if get_numeric_value(p.get(data_field)) is not None
                        and low <= get_numeric_value(p.get(data_field)) <= high
                    ]
            else:
                filtered_properties = [
                    p for p in data
                    if get_numeric_value(p.get(data_field)) == val
                ]
        except Exception:
            return []

    return filtered_properties

# --- Format results ---
def format_property(prop):
    property_id = prop.get('property_id', 'N/A')
    rent_price = prop.get('Rent_Price', 'N/A')
    size = prop.get('Size_In_Sqft', 'Unknown')
    carpet_area = prop.get('Carpet_Area_Sqft', 'Unknown')
    security_deposit = prop.get('Security_Deposite', 'N/A')
    brokerage = prop.get('Brokerage', 'N/A')
    furnishing_status = prop.get('Furnishing_Status', 'N/A')
    amenities = prop.get('Number_Of_Amenities',0)
    age = prop.get('Property_Age', 'Unknown')
    area = prop.get('Area', 'N/A')
    zone = prop.get('Zone', 'N/A')
    bedrooms = prop.get('Bedrooms', 'N/A')
    bathrooms = prop.get('Bathrooms', 'N/A')
    balcony = prop.get('Balcony', 'N/A')
    floor_no = prop.get('Floor_No', 'N/A')
    total_floors = prop.get('Total_floors_In_Building', 'N/A')
    maintenance = prop.get('Maintenance_Charge', 'N/A')
    recommended_for = prop.get('Recommended_For', 'N/A')
    water_supply = prop.get('Water_Supply_Type', 'N/A')
    society_type = prop.get('Society_Type', 'N/A')
    road_connectivity = prop.get('Road_Connectivity', 'N/A')
    facilities_list = [k.replace("_", " ").title() for k, v in prop.get("Facilities", {}).items() if v == 1]
    facilities = ', '.join(facilities_list) if facilities_list else 'None'
    nearby_amenities_list = [k.replace("_", " ").title() for k, v in prop.get("Nearby_Amenities", {}).items() if v == 1]
    nearby_amenities = ', '.join(nearby_amenities_list) if nearby_amenities_list else 'None'
    rooms = prop.get("Room_Details", {}).get("Rooms", "N/A")
    property_type = prop.get("Room_Details", {}).get("Type", "N/A")

    return (
        f"**ID:** {property_id} | **Rent:** ₹{rent_price} | **Size:** {size} sqft | **Carpet Area:** {carpet_area} sqft\n\n"
        f"**Rooms:** {rooms} | **Property Type:** {property_type} | **Bedrooms:** {bedrooms} | **Bathrooms:** {bathrooms} | **Balcony:** {balcony}\n\n"
        f"**Furnishing:** {furnishing_status} | **Security Deposit:** ₹{security_deposit} | **Brokerage:** {brokerage}\n\n"
        f"**Amenities:** {amenities}\n\n"
        f"**Facilities:** {facilities}\n\n"
        f"**Nearby Amenities:** {nearby_amenities}\n\n"
        f"**Floor:** {floor_no}/{total_floors} | **Maintenance:** {maintenance} | **Recommended For:** {recommended_for}\n\n"
        f"**Water Supply:** {water_supply} | **Society:** {society_type} | **Road Connectivity:** {road_connectivity} km\n\n"
        f"**Age:** {age} years | **Area:** {area} | **Zone:** {zone}"
    )

# --- Create property map ---
def create_property_map(properties):
    """
    Create a Folium map with property markers for Nagpur.
    """
    # Default to Nagpur coordinates if no properties or location data
    default_lat, default_lon = 21.1458, 79.0882  # Nagpur coordinates
    
    # Create a map centered around Nagpur
    m = folium.Map(location=[default_lat, default_lon], zoom_start=12)
    
    # Add tile layer with Google Maps style
    folium.TileLayer('OpenStreetMap').add_to(m)
    
    # Add property markers
    for prop in properties:
        property_id = prop.get('property_id', 'N/A')
        rent_price = prop.get('Rent_Price', 'N/A')
        area = prop.get('Area', 'N/A')
        size = prop.get('Size_In_Sqft', 'Unknown')
        property_type = prop.get("Room_Details", {}).get("Type", "N/A")
        
        # Get coordinates for the property
        if "Latitude" in prop and "Longitude" in prop:
            lat, lon = prop["Latitude"], prop["Longitude"]
        else:
            # Try to geocode the area name within Nagpur
            coords = geocode_area(area)
            if coords:
                lat, lon = coords
            else:
                # Skip if we can't get coordinates
                continue
        
        # Create popup text
        popup_text = f"""
        <b>ID:</b> {property_id}<br>
        <b>Rent:</b> ₹{rent_price}<br>
        <b>Area:</b> {area}<br>
        <b>Size:</b> {size} sqft<br>
        <b>Type:</b> {property_type}
        """
        
        # Add marker to the map
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=250),
            tooltip=f"ID: {property_id} | Rent: ₹{rent_price}",
            icon=folium.Icon(color='blue', icon='home')
        ).add_to(m)
    
    return m

# --- Main App ---
def main():
    # Header
    st.title("🏠 Property Search Assistant - Nagpur")
    st.markdown("Find your perfect property in Nagpur with our advanced search and comparison tools")
    
    # Initialize session state for filters
    if 'filters' not in st.session_state:
        st.session_state.filters = {}
    
    # Sidebar for filters
    st.sidebar.header("🔍 Search Filters")
    
    # Add Nagpur city badge
    st.sidebar.markdown("### 🔍 Search in Nagpur City")
    st.sidebar.info("All search results are limited to properties within Nagpur city limits.")
    
    # Search mode selection
    search_mode = st.sidebar.radio(
        "Select Search Mode",
        ["Simple Search", "Advanced Search", "Compare Properties"]
    )
    
    # Category options for dropdowns
    CATEGORY_OPTIONS = {
        "brokerage": sorted(list(set(str(p.get("Brokerage", "N/A")).lower() for p in properties_data))),
        "furnishing": sorted(list(set(str(p.get("Furnishing_Status", "N/A")).lower() for p in properties_data))),
        "maintenance": sorted(list(set(str(p.get("Maintenance_Charge", "N/A")).lower() for p in properties_data))),
        "recommended_for": sorted(list(set(str(p.get("Recommended_For", "N/A")).lower() for p in properties_data))),
        "water_supply": sorted(list(set(str(p.get("Water_Supply_Type", "N/A")).lower() for p in properties_data))),
        "society_type": sorted(list(set(str(p.get("Society_Type", "N/A")).lower() for p in properties_data))),
        "area": ALL_AREAS,
        "zone": ALL_ZONES,
        "room_type": ALL_ROOM_TYPES,
        "property_type": ALL_PROPERTY_TYPES
    }
    
    # Search map
    search_map = {
        "1": "size", "2": "carpet", "3": "age", "4": "brokerage", "5": "id", "6": "amenities", "7": "furnishing",
        "8": "security", "9": "rent", "10": "area", "11": "zone", "12": "bedrooms", "13": "bathrooms",
        "14": "balcony", "15": "floor_no", "16": "total_floors", "17": "maintenance", "18": "recommended_for",
        "19": "water_supply", "20": "society_type", "21": "road_connectivity", "22": "facilities", "23": "nearby_amenities",
        "24": "room_type", "25": "property_type", "26": "compare"
    }
    
    # Simple Search Mode
    if search_mode == "Simple Search":
        st.sidebar.subheader("Quick Search")
        
        # Quick search options
        quick_search = st.sidebar.selectbox(
            "Select search criteria",
            ["Rent Price", "Area", "Property Type", "Bedrooms"]
        )
        
        if quick_search == "Rent Price":
            rent_option = st.sidebar.radio(
                "Rent preference",
                ["Below budget", "Above budget", "Exact amount", "Range"]
            )
            
            if rent_option == "Below budget":
                max_rent = st.sidebar.number_input("Maximum rent (₹)", min_value=1000, value=20000, step=1000)
                st.session_state.filters["rent"] = f"below {max_rent}"
            elif rent_option == "Above budget":
                min_rent = st.sidebar.number_input("Minimum rent (₹)", min_value=1000, value=10000, step=1000)
                st.session_state.filters["rent"] = f"above {min_rent}"
            elif rent_option == "Exact amount":
                exact_rent = st.sidebar.number_input("Exact rent (₹)", min_value=1000, value=15000, step=1000)
                st.session_state.filters["rent"] = str(exact_rent)
            else:  # Range
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    min_rent = st.number_input("Min rent (₹)", min_value=1000, value=10000, step=1000)
                with col2:
                    max_rent = st.number_input("Max rent (₹)", min_value=1000, value=25000, step=1000)
                st.session_state.filters["rent"] = f"between {min_rent} and {max_rent}"
                
        elif quick_search == "Area":
            area = st.sidebar.selectbox("Select area in Nagpur", ALL_AREAS)
            st.session_state.filters["area"] = area
            
        elif quick_search == "Property Type":
            prop_type = st.sidebar.selectbox("Select property type", ALL_PROPERTY_TYPES)
            st.session_state.filters["property_type"] = prop_type
            
        elif quick_search == "Bedrooms":
            bedrooms = st.sidebar.slider("Number of bedrooms", 1, 5, 2)
            st.session_state.filters["bedrooms"] = str(bedrooms)
    
    # Advanced Search Mode
    elif search_mode == "Advanced Search":
        st.sidebar.subheader("Advanced Filters")
        
        # Allow user to select multiple filters
        selected_filters = st.sidebar.multiselect(
            "Select filters to apply",
            list(search_map.values())[:-1],  # Exclude "compare"
            default=["rent", "area"]
        )
        
        # Generate input fields for selected filters
        for field in selected_filters:
            if field in CATEGORY_OPTIONS and CATEGORY_OPTIONS[field]:
                # For categorical fields, use selectbox
                options = CATEGORY_OPTIONS[field]
                selected_option = st.sidebar.selectbox(
                    f"Select {field.replace('_', ' ').title()}",
                    options=options
                )
                st.session_state.filters[field] = selected_option
            elif field == "facilities":
                # For facilities, use multiselect
                selected_facilities = st.sidebar.multiselect(
                    "Select facilities",
                    options=ALL_FACILITIES
                )
                st.session_state.filters[field] = ', '.join(selected_facilities)
            elif field == "nearby_amenities":
                # For nearby amenities, use multiselect
                selected_amenities = st.sidebar.multiselect(
                    "Select nearby amenities",
                    options=ALL_NEARBY_AMENITIES
                )
                st.session_state.filters[field] = ', '.join(selected_amenities)
            else:
                # For numeric fields, provide text input with instructions
                help_text = ""
                if field in ["size", "carpet", "age", "security", "rent", "amenities", "bedrooms", "bathrooms", "balcony", "floor_no", "total_floors", "maintenance"]:
                    help_text = "You can use: 'below 1000', 'above 500', 'between 500 and 1000', or exact number"
                
                user_input = st.sidebar.text_input(
                    f"Enter {field.replace('_', ' ').title()}",
                    help=help_text
                )
                if user_input:
                    st.session_state.filters[field] = user_input
    
    # Compare Properties Mode
    else:  # Compare Properties
        st.sidebar.subheader("Property Comparison")
        property_ids = st.sidebar.text_input(
            "Enter property IDs to compare (comma separated)",
            help="Example: 101, 102, 105"
        )
        if property_ids:
            st.session_state.filters["compare"] = property_ids
    
    # Apply filters button
    if st.sidebar.button("Apply Filters", type="primary"):
        st.session_state.apply_filters = True
    else:
        st.session_state.apply_filters = False
    
    # Reset filters button
    if st.sidebar.button("Reset Filters"):
        st.session_state.filters = {}
        st.session_state.apply_filters = False
        st.experimental_rerun()
    
    # Main content area
    if st.session_state.apply_filters:
        # Handle comparison mode
        if search_mode == "Compare Properties" and "compare" in st.session_state.filters:
            property_ids = [pid.strip().lower() for pid in st.session_state.filters["compare"].split(",")]
            if len(property_ids) < 2:
                st.warning("⚠️ Please enter at least two Property IDs to compare.")
            else:
                st.header("Property Comparison")
                compare_properties_side_by_side(properties_data, property_ids)
        else:
            # Apply all selected filters
            results = properties_data
            for field, value in st.session_state.filters.items():
                if field != "compare":
                    results = filter_properties(value, field, results)
            
            if not results:
                st.warning("❌ No properties found matching your criteria in Nagpur.")
            else:
                st.success(f"✅ Found {len(results)} properties matching your criteria in Nagpur.")
                
                # Create tabs for different views
                tab1, tab2, tab3 = st.tabs(["List View", "Map View", "Analytics"])
                
                with tab1:
                    # Group by property type
                    grouped_results = defaultdict(list)
                    for prop in results:
                        property_type = prop.get("Room_Details", {}).get("Type", "Other/Unspecified Type")
                        grouped_results[property_type].append(prop)
                    
                    # Display results grouped by property type
                    for prop_type, props in grouped_results.items():
                        st.subheader(f"🏠 Property Type: {str(prop_type).title()} ({len(props)} results)")
                        
                        # Create columns for better layout
                        cols = st.columns(2)
                        for i, prop in enumerate(props):
                            with cols[i % 2]:
                                with st.expander(f"ID: {prop.get('property_id', 'N/A')} | Rent: ₹{prop.get('Rent_Price', 'N/A')}"):
                                    st.markdown(format_property(prop))
                
                with tab2:
                    st.subheader("Property Locations in Nagpur")
                    
                    # Create and display the map
                    try:
                        property_map = create_property_map(results)
                        folium_static(property_map, width=700, height=500)
                        
                        # Add map controls explanation
                        st.markdown("""
                        **Map Controls:**
                        - Click on markers to see property details
                        - Zoom in/out using the + and - buttons or mouse wheel
                        - Drag to move around the map
                        """)
                    except Exception as e:
                        st.error(f"Error displaying map: {str(e)}")
                        st.info("Please check if you have a stable internet connection for map loading.")
                
                with tab3:
                    st.subheader("Property Analytics for Nagpur")
                    
                    # Create analytics visualizations
                    if results:
                        # Convert to DataFrame for easier analysis
                        df = pd.DataFrame(results)
                        
                        # Rent distribution
                        st.subheader("Rent Distribution in Nagpur")
                        fig_rent = px.histogram(
                            df, 
                            x="Rent_Price", 
                            nbins=20,
                            title="Distribution of Property Rents in Nagpur",
                            labels={"Rent_Price": "Rent (₹)", "count": "Number of Properties"}
                        )
                        st.plotly_chart(fig_rent, use_container_width=True)
                        
                        # Property types
                        st.subheader("Property Types in Nagpur")
                        prop_types = [prop.get("Room_Details", {}).get("Type", "Unknown") for prop in results]
                        type_counts = pd.Series(prop_types).value_counts()
                        
                        fig_types = px.pie(
                            values=type_counts.values,
                            names=type_counts.index,
                            title="Distribution of Property Types in Nagpur"
                        )
                        st.plotly_chart(fig_types, use_container_width=True)
                        
                        # Area distribution
                        if "Area" in df.columns:
                            st.subheader("Properties by Area in Nagpur")
                            area_counts = df["Area"].value_counts()
                            
                            fig_area = px.bar(
                                x=area_counts.index,
                                y=area_counts.values,
                                labels={"x": "Area", "y": "Number of Properties"},
                                title="Properties by Area in Nagpur"
                            )
                            st.plotly_chart(fig_area, use_container_width=True)
    else:
        # Display welcome message and sample properties
        st.header("Welcome to Property Search Assistant - Nagpur")
        st.markdown("""
        Use the filters in the sidebar to find properties that match your criteria in Nagpur. 
        You can search by various attributes like rent, area, property type, and more.
        
        **Features:**
        - Simple and advanced search modes
        - Property comparison tool
        - Visual analytics
        - Interactive map view
        - Detailed property information
        """)
        
        # Display some sample properties
        st.subheader("Featured Properties in Nagpur")
        sample_properties = properties_data[:4] if len(properties_data) >= 4 else properties_data
        
        cols = st.columns(2)
        for i, prop in enumerate(sample_properties):
            with cols[i % 2]:
                with st.expander(f"ID: {prop.get('property_id', 'N/A')} | Rent: ₹{prop.get('Rent_Price', 'N/A')}"):
                    st.markdown(format_property(prop))

if __name__ == "__main__":
    main()
