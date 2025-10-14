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
    page_title="Property Search Hub - Nagpur",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar navigation
st.sidebar.title("🏠 Property Search Hub")
st.sidebar.markdown("Navigate between different property search options:")

app_mode = st.sidebar.radio(
    "Select Application",
    ["Residential Properties", "Commercial Properties", "PG Finder"]
)

# Common functions used by all apps
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on earth."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def geocode_area(area_name):
    """Get latitude and longitude for an area name in Nagpur."""
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={area_name}, Nagpur, India&format=json&limit=1"
        headers = {"User-Agent": "PropertySearchApp/1.0"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        return None
    except Exception as e:
        st.warning(f"Geocoding error for {area_name}: {str(e)}")
        return None

# App 1: Residential Property Search
def run_residential_app():
    st.title("🏠 Residential Property Search - Nagpur")
    st.markdown("Find your perfect home in Nagpur with our advanced search and comparison tools")
    
    # Initialize session state for filters
    if 'residential_filters' not in st.session_state:
        st.session_state.residential_filters = {}
    
    # Initialize session state for user location
    if 'residential_user_location' not in st.session_state:
        st.session_state.residential_user_location = None
    
    # Load properties from JSON file
    @st.cache_data
    def load_properties():
        try:
            with open("property_data.json", "r") as f:
                properties = json.load(f)
                nagpur_properties = [p for p in properties if p.get("City", "").lower() == "nagpur" or p.get("Area", "").lower().find("nagpur") != -1]
                return nagpur_properties
        except FileNotFoundError:
            st.error("Error: 'property_data.json' not found. Please ensure the file exists.")
            return []
        except json.JSONDecodeError:
            st.error("Error: Could not decode 'property_data.json'. Please check its format.")
            return []
    
    properties_data = load_properties()
    
    # Helper functions for normalization
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
        if not value:
            return None
        match = re.search(r"\d+", str(value))
        return int(match.group()) if match else None
    
    # Dynamically get all unique values from the dataset
    ALL_AREAS = sorted(list(set(normalize_area_name(p.get("Area", "N/A")) for p in properties_data)))
    ALL_ZONES = sorted(list(set(normalize_zone_name(p.get("Zone", "N/A")) for p in properties_data)))
    
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
    
    ALL_ROOM_TYPES = sorted(list(set(normalize_room_name(p.get("Room_Details", {}).get("Rooms", "N/A")) for p in properties_data if p.get("Room_Details", {}).get("Rooms"))))
    ALL_PROPERTY_TYPES = sorted(list(set(normalize_property_type_name(p.get("Room_Details", {}).get("Type", "N/A")) for p in properties_data if p.get("Room_Details", {}).get("Type"))))
    
    # Filtering logic
    def filter_properties(user_input, field, data):
        filtered_properties = []
        data_field_map = {
            "size": "Size_In_Sqft", "carpet": "Carpet_Area_Sqft", "age": "Property_Age", "brokerage": "Brokerage",
            "furnishing": "Furnishing_Status", "amenities": "Number_Of_Amenities", "security": "Security_Deposite", "rent": "Rent_Price",
            "area": "Area", "zone": "Zone", "bedrooms": "Bedrooms", "bathrooms": "Bathrooms", "balcony": "Balcony",
            "floor_no": "Floor_No", "total_floors": "Total_floors_In_Building", "maintenance": "Maintenance_Charge",
            "recommended_for": "Recommended_For", "water_supply": "Water_Supply_Type", "society_type": "Society_Type",
            "road_connectivity": "Road_Connectivity", "facilities": "Facilities", "nearby_amenities": "Nearby_Amenities",
            "room_type": "Room_Details", "property_type": "Room_Details", "id": "property_id"
        }
        data_field = data_field_map.get(field)
        if not data_field:
            return []
    
        normalized_user_input = user_input.lower().strip()
        
        # String fields
        if field in ["brokerage", "furnishing", "maintenance", "recommended_for", "water_supply", "society_type"]:
            filtered_properties = [p for p in data if str(p.get(data_field, "N/A")).lower() == normalized_user_input]
        
        # Facilities field
        elif field == "facilities":
            user_facilities = [normalize_facility_name(f.strip()) for f in user_input.split(',') if f.strip()]
            filtered_properties = []
            
            for p in data:
                facilities_dict = p.get("Facilities", {})
                if not isinstance(facilities_dict, dict):
                    continue
                    
                normalized_facilities = {normalize_facility_name(k): v for k, v in facilities_dict.items()}
                
                if all(facility in normalized_facilities and normalized_facilities[facility] == 1 for facility in user_facilities):
                    filtered_properties.append(p)
    
        # Nearby Amenities field
        elif field == "nearby_amenities":
            user_amenities = [normalize_amenity_name(a.strip()) for a in user_input.split(',') if a.strip()]
            filtered_properties = []
            
            for p in data:
                amenities_dict = p.get("Nearby_Amenities", {})
                if not isinstance(amenities_dict, dict):
                    continue
                    
                normalized_amenities = {normalize_amenity_name(k): v for k, v in amenities_dict.items()}
                
                if all(amenity in normalized_amenities and normalized_amenities[amenity] == 1 for amenity in user_amenities):
                    filtered_properties.append(p)
    
        # Room Type field
        elif field == "room_type":
            filtered_properties = [p for p in data if 
                                  normalize_room_name(p.get("Room_Details", {}).get("Rooms", "")) == normalized_user_input]
    
        # Property Type field
        elif field == "property_type":
            filtered_properties = [p for p in data if 
                                  normalize_property_type_name(p.get("Room_Details", {}).get("Type", "")) == normalized_user_input]
    
        # Area field
        elif field == "area":
            filtered_properties = [p for p in data if 
                                  normalize_area_name(p.get("Area", "N/A")) == normalize_area_name(user_input)]
    
        # Zone field
        elif field == "zone":
            filtered_properties = [p for p in data if 
                                  normalize_zone_name(p.get("Zone", "N/A")) == normalize_zone_name(user_input)]
            
        # Property ID field
        elif field == "id":
            property_ids = [pid.strip().lower() for pid in user_input.split(",")]
            filtered_properties = [p for p in data if str(p.get("property_id", "")).lower() in property_ids]
        
        # Numeric fields
        else:
            try:
                val = get_numeric_value(user_input)
                if val is None:
                    return []
                
                if user_input.lower().startswith("below"):
                    filtered_properties = [
                        p for p in data
                        if get_numeric_value(p.get(data_field)) is not None
                        and get_numeric_value(p.get(data_field)) < val
                    ]
                elif user_input.lower().startswith("above"):
                    filtered_properties = [
                        p for p in data
                        if get_numeric_value(p.get(data_field)) is not None
                        and get_numeric_value(p.get(data_field)) > val
                    ]
                elif user_input.lower().startswith("between"):
                    nums = re.findall(r"\d+", user_input)
                    if len(nums) >= 2:
                        low, high = int(nums[0]), int(nums[1])
                        filtered_properties = [
                            p for p in data
                            if get_numeric_value(p.get(data_field)) is not None
                            and low <= get_numeric_value(p.get(data_field)) <= high
                        ]
                else:
                    # Exact match
                    filtered_properties = [
                        p for p in data
                        if get_numeric_value(p.get(data_field)) == val
                    ]
            except Exception as e:
                st.warning(f"Error filtering by {field}: {str(e)}")
                return []
    
        return filtered_properties
    
    # Format results
    def format_property(prop, distance=None):
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
    
        # Add distance information if available
        distance_text = ""
        if distance is not None:
            distance_text = f"**Distance from you:** {distance:.2f} km\n\n"
    
        return (
            f"**ID:** {property_id} | **Rent:** ₹{rent_price} | **Size:** {size} sqft | **Carpet Area:** {carpet_area} sqft\n\n"
            f"{distance_text}"
            f"**Rooms:** {rooms} | **Property Type:** {property_type} | **Bedrooms:** {bedrooms} | **Bathrooms:** {bathrooms} | **Balcony:** {balcony}\n\n"
            f"**Furnishing:** {furnishing_status} | **Security Deposit:** ₹{security_deposit} | **Brokerage:** {brokerage}\n\n"
            f"**Amenities:** {amenities}\n\n"
            f"**Facilities:** {facilities}\n\n"
            f"**Nearby Amenities:** {nearby_amenities}\n\n"
            f"**Floor:** {floor_no}/{total_floors} | **Maintenance:** {maintenance} | **Recommended For:** {recommended_for}\n\n"
            f"**Water Supply:** {water_supply} | **Society:** {society_type} | **Road Connectivity:** {road_connectivity} km\n\n"
            f"**Age:** {age} years | **Area:** {area} | **Zone:** {zone}"
        )
    
    # Create property map
    def create_property_map(properties, user_location=None):
        # Default to Nagpur coordinates if no properties or location data
        default_lat, default_lon = 21.1458, 79.0882  # Nagpur coordinates
        
        # Create a map centered around Nagpur
        m = folium.Map(location=[default_lat, default_lon], zoom_start=12)
        
        # Add tile layer with Google Maps style
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
                # Get property coordinates
                if "Latitude" in prop and "Longitude" in prop:
                    prop_lat, prop_lon = prop["Latitude"], prop["Longitude"]
                else:
                    # Try to geocode the area name within Nagpur
                    coords = geocode_area(prop.get("Area", "N/A"))
                    if coords:
                        prop_lat, prop_lon = coords
                    else:
                        # Skip if we can't get coordinates
                        continue
                
                # Calculate distance
                distance = haversine_distance(user_lat, user_lon, prop_lat, prop_lon)
                distances.append(distance)
                # Store distance in property for later use
                prop["distance_from_user"] = distance
            
            # Calculate average distance
            avg_distance = sum(distances) / len(distances) if distances else 0
        else:
            avg_distance = None
        
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
        
        return m
    
    # Comparison Function
    def compare_properties_side_by_side(data, property_ids):
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
    
    # Main content for residential app
    st.sidebar.subheader("🔍 Search Filters")
    
    # Add Nagpur city badge
    st.sidebar.markdown("### 🔍 Search in Nagpur City")
    st.sidebar.info("All search results are limited to properties within Nagpur city limits.")
    
    # User location section
    st.sidebar.subheader("📍 Your Location")
    location_method = st.sidebar.radio(
        "Select location method",
        ["Enter Manually", "Use Current Location"]
    )
    
    if location_method == "Enter Manually":
        lat = st.sidebar.number_input("Latitude", value=21.1458, format="%.6f")
        lon = st.sidebar.number_input("Longitude", value=79.0882, format="%.6f")
        if st.sidebar.button("Set Location"):
            st.session_state.residential_user_location = (lat, lon)
            st.sidebar.success("Location set successfully!")
    else:
        if st.sidebar.button("Get My Current Location"):
            # This is a placeholder - in a real app, you would use browser geolocation
            # For demo purposes, we'll use a default location in Nagpur
            st.session_state.residential_user_location = (21.1458, 79.0882)
            st.sidebar.success("Using default Nagpur location. In a real app, this would get your current location.")
    
    # Display current user location if set
    if st.session_state.residential_user_location:
        st.sidebar.info(f"Your location: {st.session_state.residential_user_location[0]:.6f}, {st.session_state.residential_user_location[1]:.6f}")
    
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
                st.session_state.residential_filters["rent"] = f"below {max_rent}"
            elif rent_option == "Above budget":
                min_rent = st.sidebar.number_input("Minimum rent (₹)", min_value=1000, value=10000, step=1000)
                st.session_state.residential_filters["rent"] = f"above {min_rent}"
            elif rent_option == "Exact amount":
                exact_rent = st.sidebar.number_input("Exact rent (₹)", min_value=1000, value=15000, step=1000)
                st.session_state.residential_filters["rent"] = str(exact_rent)
            else:  # Range
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    min_rent = st.number_input("Min rent (₹)", min_value=1000, value=10000, step=1000)
                with col2:
                    max_rent = st.number_input("Max rent (₹)", min_value=1000, value=25000, step=1000)
                st.session_state.residential_filters["rent"] = f"between {min_rent} and {max_rent}"
                
        elif quick_search == "Area":
            area = st.sidebar.selectbox("Select area in Nagpur", ALL_AREAS)
            st.session_state.residential_filters["area"] = area
            
        elif quick_search == "Property Type":
            prop_type = st.sidebar.selectbox("Select property type", ALL_PROPERTY_TYPES)
            st.session_state.residential_filters["property_type"] = prop_type
            
        elif quick_search == "Bedrooms":
            bedrooms = st.sidebar.slider("Number of bedrooms", 1, 5, 2)
            st.session_state.residential_filters["bedrooms"] = str(bedrooms)
    
    # Advanced Search Mode
    elif search_mode == "Advanced Search":
        st.sidebar.subheader("Advanced Filters")
        
        # Allow user to select multiple filters
        selected_filters = st.sidebar.multiselect(
            "Select filters to apply",
            list(search_map.values())[:-1],  # Removed proximity_points and amenities_list
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
                st.session_state.residential_filters[field] = selected_option
            elif field == "facilities":
                # For facilities, use multiselect
                selected_facilities = st.sidebar.multiselect(
                    "Select facilities",
                    options=ALL_FACILITIES
                )
                st.session_state.residential_filters[field] = ', '.join(selected_facilities)
            elif field == "nearby_amenities":
                # For nearby amenities, use multiselect
                selected_amenities = st.sidebar.multiselect(
                    "Select nearby amenities",
                    options=ALL_NEARBY_AMENITIES
                )
                st.session_state.residential_filters[field] = ', '.join(selected_amenities)
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
                    st.session_state.residential_filters[field] = user_input
    
    # Compare Properties Mode
    else:  # Compare Properties
        st.sidebar.subheader("Property Comparison")
        property_ids = st.sidebar.text_input(
            "Enter property IDs to compare (comma separated)",
            help="Example: 101, 102, 105"
        )
        if property_ids:
            st.session_state.residential_filters["compare"] = property_ids
    
    # Apply filters button
    if st.sidebar.button("Apply Filters", type="primary"):
        st.session_state.residential_apply_filters = True
    else:
        st.session_state.residential_apply_filters = False
    
    # Reset filters button
    if st.sidebar.button("Reset Filters"):
        st.session_state.residential_filters = {}
        st.session_state.residential_apply_filters = False
        st.rerun()
    
    # Main content area
    if st.session_state.residential_apply_filters:
        # Handle comparison mode
        if search_mode == "Compare Properties" and "compare" in st.session_state.residential_filters:
            property_ids = [pid.strip().lower() for pid in st.session_state.residential_filters["compare"].split(",")]
            if len(property_ids) < 2:
                st.warning("⚠️ Please enter at least two Property IDs to compare.")
            else:
                st.header("Property Comparison")
                compare_properties_side_by_side(properties_data, property_ids)
        else:
            # Apply all selected filters
            results = properties_data
            for field, value in st.session_state.residential_filters.items():
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
                            # Get distance if user location is set
                            distance = prop.get("distance_from_user", None) if st.session_state.residential_user_location else None
                            
                            with cols[i % 2]:
                                with st.expander(f"ID: {prop.get('property_id', 'N/A')} | Rent: ₹{prop.get('Rent_Price', 'N/A')}"):
                                    st.markdown(format_property(prop, distance))
                
                with tab2:
                    st.subheader("Property Locations in Nagpur")
                    
                    # Create and display the map
                    try:
                        property_map = create_property_map(results, st.session_state.residential_user_location)
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
                        
                        # Distance distribution if user location is set
                        if st.session_state.residential_user_location and "distance_from_user" in df.columns:
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
                with st.expander(f"ID: {prop.get('property_id', 'N/A')} | Rent: ₹{prop.get('Rent_Price', 'N/A')}"):
                    st.markdown(format_property(prop))

# App 2: Commercial Property Search
def run_commercial_app():
    st.title("🏢 Commercial Property Search - Nagpur")
    st.markdown("Find your perfect commercial property in Nagpur with our advanced search and comparison tools")
    
    # Initialize session state for filters
    if 'commercial_filters' not in st.session_state:
        st.session_state.commercial_filters = {}
    
    # Initialize session state for user location
    if 'commercial_user_location' not in st.session_state:
        st.session_state.commercial_user_location = None
    
    # Initialize session state for filtered properties
    if 'commercial_filtered_properties' not in st.session_state:
        st.session_state.commercial_filtered_properties = []
    
    # Load properties from JSON file
    @st.cache_data
    def load_properties():
        try:
            with open("commercial_data.json", "r") as f:
                properties = json.load(f)
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
    if properties_data:
        st.session_state.commercial_filtered_properties = properties_data
    
    # Helper for normalization
    def normalize_facility_name(facility_name):
        return str(facility_name).replace(" ", "_").lower().strip()
    
    # Function to format property details
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
    
    # Function to filter properties by multiple criteria
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
    
    # Function to get unique values for a field
    def get_unique_values(data, field):
        """Get unique values for a specific field from the data."""
        values = set()
        for p in data:
            value = p.get(field)
            if value:
                values.add(str(value))
        return sorted(values)
    
    # Function to get all available facilities
    def get_all_facilities(data):
        """Get all facilities that are available in any property."""
        facilities = set()
        for p in data:
            for fac, val in p.get("facilities", {}).items():
                if val == 1:
                    facilities.add(fac.replace('_', ' ').title())
        return sorted(facilities)
    
    # Function to get all available floors
    def get_all_floors(data):
        """Get all floors that are available in any property."""
        floors = set()
        for p in data:
            for floor, val in p.get("floor_availability", {}).items():
                if val == 1:
                    floors.add(floor.replace('_', ' ').title())
        return sorted(floors)
    
    # Function to compare properties side by side
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
    
    # Function to create property map
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
                st.session_state.commercial_user_location = (lat, lon)
                st.success("Location set successfully!")
        else:
            if st.button("Get My Current Location"):
                # This is a placeholder - in a real app, you would use browser geolocation
                # For demo purposes, we'll use a default location in Nagpur
                st.session_state.commercial_user_location = (21.1458, 79.0882)
                st.success("Using default Nagpur location. In a real app, this would get your current location.")
    
    # Display current user location if set
    if st.session_state.commercial_user_location:
        st.info(f"Your location: {st.session_state.commercial_user_location[0]:.6f}, {st.session_state.commercial_user_location[1]:.6f}")
    
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
                    st.session_state.commercial_filters["max_rent"] = max_rent
                elif rent_option == "Above budget":
                    min_rent = st.number_input("Minimum rent (₹)", min_value=1000, value=10000, step=1000)
                    st.session_state.commercial_filters["min_rent"] = min_rent
                elif rent_option == "Exact amount":
                    exact_rent = st.number_input("Exact rent (₹)", min_value=1000, value=15000, step=1000)
                    st.session_state.commercial_filters["min_rent"] = exact_rent
                    st.session_state.commercial_filters["max_rent"] = exact_rent
                else:  # Range
                    col1, col2 = st.columns(2)
                    with col1:
                        min_rent = st.number_input("Min rent (₹)", min_value=1000, value=10000, step=1000)
                    with col2:
                        max_rent = st.number_input("Max rent (₹)", min_value=1000, value=25000, step=1000)
                    st.session_state.commercial_filters["min_rent"] = min_rent
                    st.session_state.commercial_filters["max_rent"] = max_rent
                    
            elif quick_search == "Area":
                area = st.selectbox("Select area in Nagpur", ["Any"] + areas)
                if area != "Any":
                    st.session_state.commercial_filters["area"] = area
                
            elif quick_search == "Property Type":
                prop_type = st.selectbox("Select property type", ["Any"] + property_types)
                if prop_type != "Any":
                    st.session_state.commercial_filters["property_type"] = prop_type
                
            elif quick_search == "Size":
                size_option = st.radio(
                    "Size preference",
                    ["Below size", "Above size", "Exact size", "Range"]
                )
                
                if size_option == "Below size":
                    max_size = st.number_input("Maximum size (sqft)", min_value=100, value=2000, step=100)
                    st.session_state.commercial_filters["max_size"] = max_size
                elif size_option == "Above size":
                    min_size = st.number_input("Minimum size (sqft)", min_value=100, value=1000, step=100)
                    st.session_state.commercial_filters["min_size"] = min_size
                elif size_option == "Exact size":
                    exact_size = st.number_input("Exact size (sqft)", min_value=100, value=1500, step=100)
                    st.session_state.commercial_filters["min_size"] = exact_size
                    st.session_state.commercial_filters["max_size"] = exact_size
                else:  # Range
                    col1, col2 = st.columns(2)
                    with col1:
                        min_size = st.number_input("Min size (sqft)", min_value=100, value=1000, step=100)
                    with col2:
                        max_size = st.number_input("Max size (sqft)", min_value=100, value=2000, step=100)
                    st.session_state.commercial_filters["min_size"] = min_size
                    st.session_state.commercial_filters["max_size"] = max_size
    
    # Advanced Search Mode
    elif search_mode == "Advanced Search":
        with st.expander("Advanced Filter Options", expanded=True):
            # Display current property count
            st.markdown(f"📊 Showing all {len(st.session_state.commercial_filtered_properties)} properties")
            
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
                    st.session_state.commercial_filters = {}
                    st.session_state.commercial_filtered_properties = properties_data
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
                    st.session_state.commercial_filters = filters
                    st.session_state.commercial_filtered_properties = filter_properties(properties_data, filters)
                    st.rerun()
    
    # Compare Properties Mode
    else:  # Compare Properties
        with st.expander("Property Comparison Options", expanded=True):
            property_ids = st.text_input(
                "Enter property IDs to compare (comma separated)",
                help="Example: Property_1, Property_2, Property_3"
            )
            if property_ids:
                st.session_state.commercial_filters["compare"] = property_ids
    
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
                    filters = st.session_state.commercial_filters.copy()
                
                # Apply filters
                st.session_state.commercial_filters = filters
                if search_mode == "Compare Properties" and "compare" in filters:
                    # For comparison mode, we don't filter the properties
                    st.session_state.commercial_filtered_properties = properties_data
                else:
                    st.session_state.commercial_filtered_properties = filter_properties(properties_data, filters)
        with col2:
            if st.button("Reset Filters"):
                st.session_state.commercial_filters = {}
                st.session_state.commercial_filtered_properties = properties_data
                st.rerun()
    
    # Display current filters
    if st.session_state.commercial_filters and search_mode != "Advanced Search":
        st.subheader("Active Filters")
        cols = st.columns(4)
        for i, (filter_type, value) in enumerate(st.session_state.commercial_filters.items()):
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
    if st.session_state.commercial_filters:
        # Handle comparison mode
        if search_mode == "Compare Properties" and "compare" in st.session_state.commercial_filters:
            property_ids = [pid.strip().lower() for pid in st.session_state.commercial_filters["compare"].split(",")]
            if len(property_ids) < 2:
                st.warning("⚠️ Please enter at least two Property IDs to compare.")
            else:
                st.header("Property Comparison")
                compare_properties_side_by_side(properties_data, property_ids)
        else:
            # Display results
            if not st.session_state.commercial_filtered_properties:
                st.warning("❌ No properties found matching your criteria in Nagpur.")
            else:
                st.success(f"✅ Found {len(st.session_state.commercial_filtered_properties)} properties matching your criteria in Nagpur.")
                
                # Create tabs for different views
                tab1, tab2, tab3 = st.tabs(["List View", "Map View", "Analytics"])
                
                with tab1:
                    # Group by property type
                    grouped_results = defaultdict(list)
                    for prop in st.session_state.commercial_filtered_properties:
                        property_type = prop.get("property_type", "Other/Unspecified Type")
                        grouped_results[property_type].append(prop)
                    
                    # Display results grouped by property type
                    for prop_type, props in grouped_results.items():
                        st.subheader(f"🏠 Property Type: {str(prop_type).title()} ({len(props)} results)")
                        
                        # Create columns for better layout
                        cols = st.columns(2)
                        for i, prop in enumerate(props):
                            # Get distance if user location is set
                            distance = prop.get("distance_from_user", None) if st.session_state.commercial_user_location else None
                            
                            with cols[i % 2]:
                                with st.expander(f"ID: {prop.get('property_id', 'N/A')} | Rent: ₹{prop.get('rent_price', 'N/A')}"):
                                    st.markdown(format_property(prop, distance))
                
                with tab2:
                    st.subheader("Property Locations in Nagpur")
                    
                    # Create and display the map
                    try:
                        property_map, avg_distance = create_property_map(st.session_state.commercial_filtered_properties, st.session_state.commercial_user_location)
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
                    if st.session_state.commercial_filtered_properties:
                        # Convert to DataFrame for easier analysis
                        df = pd.DataFrame(st.session_state.commercial_filtered_properties)
                        
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
                        for prop in st.session_state.commercial_filtered_properties:
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
                        if st.session_state.commercial_user_location and "distance_from_user" in df.columns:
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

# App 3: PG Finder
def run_pg_app():
    st.title("🏠 PG Listings Dashboard")
    
    # Load JSON data
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
    
    # Fix Amenities and Common Area columns safely
    if "Amenities" in df:
        df["Amenities"] = df["Amenities"].apply(lambda x: x if isinstance(x, list) else [])
    else:
        df["Amenities"] = [[] for _ in range(len(df))]
    
    if "Common Area" in df:
        df["Common Area"] = df["Common Area"].apply(lambda x: x if isinstance(x, list) else [])
    else:
        df["Common Area"] = [[] for _ in range(len(df))]
    
    # Ensure required columns exist
    required_columns = [
        "Listing Title", "City", "Area", "Zone", "PG Name", "Shearing", 
        "Best Suit For", "Meals Available", "Notice Period", "Lock-in Period",
        "Non-Veg Allowed", "Opposite Gender Allowed", "Visitors Allowed",
        "Drinking Allowed", "Smoking Allowed", "Rent Price", "Security Deposit"
    ]
    
    for col in required_columns:
        if col not in df.columns:
            df[col] = "" if col != "Rent Price" else 0
    
    # Custom CSS
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
    
    # Main Header
    st.markdown('<div class="main-header">🏠 PG Listings Dashboard</div>', unsafe_allow_html=True)
    
    # Sidebar Filters
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
    
    # Apply Filters
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
    
    # Results Header
    st.markdown(f"### 🏠 Found {len(filtered_df)} PG Listings matching your criteria")
    
    # Average Rent
    avg_rent = filtered_df["Rent Price"].mean() if not filtered_df.empty else 0
    st.markdown(f"#### 💰 Average Rent: ₹{avg_rent:.2f}")
    
    # PG Listings
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
    
    # Map View
    st.markdown("### 🗺️ Map View")
    filtered_df.loc[:, "Latitude"] = filtered_df.index.map(lambda x: 21.1458 + random.uniform(-0.01, 0.01))
    filtered_df.loc[:, "Longitude"] = filtered_df.index.map(lambda x: 79.0882 + random.uniform(-0.01, 0.01))
    
    m = folium.Map(location=[21.1458, 79.0882], zoom_start=12)
    
    # Add markers with color coding based on rent
    for idx, row in filtered_df.iterrows():
        # Determine marker color based on rent
        if row['Rent Price'] > avg_rent:
            color = 'red'
            icon_color = 'white'
        else:
            color = 'blue'
            icon_color = 'white'
        
        # Create popup with rent comparison
        popup_html = f"""
        <b>{row['PG Name']}</b><br>
        Shearing: {row['Shearing']}<br>
        Rent: <b>₹{row['Rent Price']}</b><br>
        Average: <b>₹{avg_rent:.2f}</b><br>
        """
        
        if row['Rent Price'] > avg_rent:
            popup_html += "<span style='color:red;'>Above Average</span>"
        else:
            popup_html += "<span style='color:blue;'>Below Average</span>"
        
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=row["Area"],
            icon=folium.Icon(color=color, icon_color=icon_color, icon='home')
        ).add_to(m)
    
    # Add a legend to the map
    legend_html = '''
         <div style="position: fixed; 
                     top: 10px; right: 10px; width: 180px; height: 110px; 
                     border:2px solid grey; z-index:9999; font-size:14px;
                     background-color:white;
                     ">&nbsp; <b>Rent Comparison</b> <br>
                     &nbsp; <i class="fa fa-circle" style="color:red"></i> Above Average Rent <br>
                     &nbsp; <i class="fa fa-circle" style="color:blue"></i> Below Average Rent <br>
                     &nbsp; Average: ₹{:.2f}
         </div>
         '''.format(avg_rent)
    
    m.get_root().html.add_child(Element(legend_html))
    
    folium_static(m, width=700, height=500)
    
    # Analytics Section
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
    
    # Footer
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem; padding: 1rem; color: #64748b; font-size: 0.9rem;">
        PG Finder Dashboard • Data sourced from pg.json • Last updated: 2023
    </div>
    """, unsafe_allow_html=True)

# Main application logic
if app_mode == "Residential Properties":
    run_residential_app()
elif app_mode == "Commercial Properties":
    run_commercial_app()
elif app_mode == "PG Finder":
    run_pg_app()
