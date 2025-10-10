import streamlit as st
import json
import re
from collections import defaultdict
import pandas as pd
import plotly.express as px

# Set page configuration
st.set_page_config(
    page_title="Property Search Assistant",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load properties from JSON file ---
@st.cache_data
def load_properties():
    try:
        with open("property_data.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Error: 'property_data.json' not found. Please ensure the file exists.")
        return []
    except json.JSONDecodeError:
        st.error("Error: Could not decode 'property_data.json'. Please check its format.")
        return []

properties_data = load_properties()

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
    """Extract integer from strings like '800 sqft', '10 years', etc."""
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

ALL_FACILITIES = sorted(
    {k for p in properties_data for k in p.get("Facilities", {}).keys()}
)

ALL_NEARBY_AMENITIES = sorted(
    {k for p in properties_data for k in p.get("Nearby_Amenities", {}).keys()}
)

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
    selected = [p for p in data if str(p.get("Property_ID", "")).lower() in property_ids]

    if not selected:
        st.warning("⚠️ No properties found for the given IDs.")
        return

    comparison_keys = set()
    for p in selected:
        comparison_keys.update(p.keys())
        if isinstance(p.get("Facilities"), dict):
            comparison_keys.update([f"Facility: {k}" for k in p["Facilities"].keys()])
        if isinstance(p.get("Nearby_Amenities"), dict):
            comparison_keys.update([f"Amenity: {k}" for k in p["Nearby_Amenities"].keys()])
        if isinstance(p.get("Room_Details"), dict):
            comparison_keys.update([f"Room Details: {k}" for k in p["Room_Details"].keys()])

    display_order = ["Property_ID", "Rent_Price"]
    remaining_keys = sorted(k for k in comparison_keys if k not in display_order)
    comparison_keys = display_order + remaining_keys

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

            if key in ["Rent_Price", "Security_Deposite"]:
                value = f"₹{value}" if value != "N/A" else value
            elif key in ["Size_In_Sqft", "Carpet_Area_Sqft"]:
                value = f"{value} sqft" if value != "N/A" else value
            elif key == "Brokerage":
                value = "Yes" if str(value).lower() == "yes" else "No"

            row.append(value)
        rows.append(row)

    headers = ["Attribute"] + [f"ID {p.get('Property_ID', 'N/A')}" for p in selected]
    df = pd.DataFrame(rows, columns=headers)
    st.dataframe(df.style.set_properties(**{'text-align': 'left'}), use_container_width=True)

# --- Filtering logic ---
def filter_properties(user_input, field, data):
    filtered_properties = []
    data_field_map = {
        "size": "Size_In_Sqft", "carpet": "Carpet_Area_Sqft", "age": "Property_Age",
        "brokerage": "Brokerage", "furnishing": "Furnishing_Status", "amenities": "Number_Of_Amenities",
        "security": "Security_Deposite", "rent": "Rent_Price", "area": "Area", "zone": "Zone",
        "bedrooms": "Bedrooms", "bathrooms": "Bathrooms", "balcony": "Balcony", "floor_no": "Floor_No",
        "total_floors": "Total_floors_In_Building", "maintenance": "Maintenance_Charge",
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
            for k, v in p.get("Facilities", {}).items()
        )]

    elif field == "nearby_amenities":
        user_amenities = [normalize_amenity_name(f) for f in user_input.split(',')]
        filtered_properties = [p for p in data if all(
            normalize_amenity_name(k) in user_amenities and v == 1
            for k, v in p.get("Nearby_Amenities", {}).items()
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
                filtered_properties = [p for p in data if get_numeric_value(p.get(data_field)) and get_numeric_value(p.get(data_field)) < val]
            elif user_input.startswith("above"):
                filtered_properties = [p for p in data if get_numeric_value(p.get(data_field)) and get_numeric_value(p.get(data_field)) > val]
            elif user_input.startswith("between"):
                nums = re.findall(r"\d+", user_input)
                if len(nums) == 2:
                    low, high = int(nums[0]), int(nums[1])
                    filtered_properties = [p for p in data if get_numeric_value(p.get(data_field)) and low <= get_numeric_value(p.get(data_field)) <= high]
            else:
                filtered_properties = [p for p in data if get_numeric_value(p.get(data_field)) == val]
        except Exception:
            return []

    return filtered_properties

# --- Format results ---
def format_property(prop):
    property_id = prop.get('Property_ID', 'N/A')
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

# --- Main App ---
def main():
    st.title("🏠 Property Search Assistant")
    st.markdown("Find your perfect property with our advanced search and comparison tools")
    
    if 'filters' not in st.session_state:
        st.session_state.filters = {}
    
    st.sidebar.header("🔍 Search Filters")
    search_mode = st.sidebar.radio("Select Search Mode", ["Simple Search", "Advanced Search", "Compare Properties"])
    
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

    # Simple Search
    if search_mode == "Simple Search":
        st.sidebar.subheader("Quick Search")
        quick_search = st.sidebar.selectbox("Select search criteria", ["Rent Price", "Area", "Property Type", "Bedrooms"])
        if quick_search == "Rent Price":
            rent_option = st.sidebar.radio("Rent preference", ["Below budget", "Above budget", "Exact amount", "Range"])
            if rent_option == "Below budget":
                max_rent = st.sidebar.number_input("Maximum rent (₹)", min_value=1000, value=20000, step=1000)
                st.session_state.filters["rent"] = f"below {max_rent}"
            elif rent_option == "Above budget":
                min_rent = st.sidebar.number_input("Minimum rent (₹)", min_value=1000, value=10000, step=1000)
                st.session_state.filters["rent"] = f"above {min_rent}"
            elif rent_option == "Exact amount":
                exact_rent = st.sidebar.number_input("Exact rent (₹)", min_value=1000, value=15000, step=1000)
                st.session_state.filters["rent"] = str(exact_rent)
            else:
                col1, col2 = st.sidebar.columns(2)
                with col1: min_rent = st.number_input("Min rent (₹)", min_value=1000, value=10000, step=1000)
                with col2: max_rent = st.number_input("Max rent (₹)", min_value=1000, value=25000, step=1000)
                st.session_state.filters["rent"] = f"between {min_rent} and {max_rent}"
        elif quick_search == "Area":
            area = st.sidebar.selectbox("Select area", ALL_AREAS)
            st.session_state.filters["area"] = area
        elif quick_search == "Property Type":
            prop_type = st.sidebar.selectbox("Select property type", ALL_PROPERTY_TYPES)
            st.session_state.filters["property_type"] = prop_type
        elif quick_search == "Bedrooms":
            bedrooms = st.sidebar.slider("Number of bedrooms", 1, 5, 2)
            st.session_state.filters["bedrooms"] = str(bedrooms)

    # Advanced Search
    elif search_mode == "Advanced Search":
        st.sidebar.subheader("Advanced Filters")
        selected_filters = st.sidebar.multiselect("Select filters to apply", list(CATEGORY_OPTIONS.keys()), default=["rent", "area"])
        for field in selected_filters:
            if field in CATEGORY_OPTIONS and CATEGORY_OPTIONS[field]:
                options = CATEGORY_OPTIONS[field]
                selected_option = st.sidebar.selectbox(f"Select {field.replace('_',' ').title()}", options=options)
                st.session_state.filters[field] = selected_option
            elif field == "facilities":
                selected_facilities = st.sidebar.multiselect("Select facilities", options=ALL_FACILITIES)
                st.session_state.filters[field] = ', '.join(selected_facilities)
            elif field == "nearby_amenities":
                selected_amenities = st.sidebar.multiselect("Select nearby amenities", options=ALL_NEARBY_AMENITIES)
                st.session_state.filters[field] = ', '.join(selected_amenities)
            else:
                user_input = st.sidebar.text_input(f"Enter {field.replace('_',' ').title()} (e.g. below 1000, between 1000 and 2000)")
                if user_input:
                    st.session_state.filters[field] = user_input

    # Compare Mode
    else:
        st.sidebar.subheader("Property Comparison")
        property_ids = st.sidebar.text_input("Enter property IDs to compare (comma separated)", help="Example: 101, 102, 105")
        if property_ids:
            st.session_state.filters["compare"] = property_ids

    if st.sidebar.button("Apply Filters", type="primary"):
        st.session_state.apply_filters = True
    else:
        st.session_state.apply
