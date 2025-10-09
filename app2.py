import streamlit as st
import json
import re
from collections import defaultdict
from tabulate import tabulate
import random

# --- Load properties from JSON file ---
@st.cache_data
def load_properties():
    try:
        with open("property_data.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("'property_data.json' not found. Please ensure the file exists.")
        return []
    except json.JSONDecodeError:
        st.error("Could not decode 'property_data.json'. Please check its format.")
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
@st.cache_data
def get_unique_values():
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
    
    return {
        "areas": ALL_AREAS,
        "zones": ALL_ZONES,
        "facilities": ALL_FACILITIES,
        "amenities": ALL_NEARBY_AMENITIES,
        "room_types": ALL_ROOM_TYPES,
        "property_types": ALL_PROPERTY_TYPES
    }

unique_values = get_unique_values()

# --- Comparison Function ---
def compare_properties_side_by_side(data, property_ids):
    selected = [p for p in data if str(p.get("property_id", "")).lower() in property_ids]
    
    if not selected:
        st.warning("No properties found for the given IDs.")
        return None
    
    # Collect all possible comparison keys
    comparison_keys = set()
    for p in selected:
        comparison_keys.update(p.keys())
        if isinstance(p.get("Facilities"), dict):
            comparison_keys.update([f"Facility: {k}" for k in p["Facilities"].keys()])
        if isinstance(p.get("Nearby_Amenities"), dict):
            comparison_keys.update([f"Amenity: {k}" for k in p["Nearby_Amenities"].keys()])
        if isinstance(p.get("Room_Details"), dict):
            comparison_keys.update([f"Room Details: {k}" for k in p["Room_Details"].keys()])
    
    # Always show Property ID and Rent Price first
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
    return tabulate(rows, headers=headers, tablefmt="grid")

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
        f"🏠 **ID:** {property_id} | **Rent:** ₹{rent_price} | **Size:** {size} sqft | **Carpet Area:** {carpet_area} sqft\n"
        f"🛏️ **Rooms:** {rooms} | **Property Type:** {property_type} | **Bedrooms:** {bedrooms} | **Bathrooms:** {bathrooms} | **Balcony:** {balcony}\n"
        f"🪑 **Furnishing:** {furnishing_status} | **Security Deposit:** ₹{security_deposit} | **Brokerage:** {brokerage}\n"
        f"✨ **Amenities:** {amenities}\n"
        f"🏢 **Facilities:** {facilities}\n"
        f"📍 **Nearby Amenities:** {nearby_amenities}\n"
        f"🏢 **Floor:** {floor_no}/{total_floors} | **Maintenance:** {maintenance} | **Recommended For:** {recommended_for}\n"
        f"💧 **Water Supply:** {water_supply} | **Society:** {society_type} | **Road Connectivity:** {road_connectivity} km\n"
        f"📅 **Age:** {age} years | **Area:** {area} | **Zone:** {zone}\n"
        f"----------------------------------------"
    )

# --- Natural Language Processing ---
def extract_search_criteria(query):
    criteria = {}
    query_lower = query.lower()
    
    # Extract rent information
    if any(word in query_lower for word in ["rent", "price", "cost"]):
        if "below" in query_lower or "under" in query_lower or "less than" in query_lower:
            match = re.search(r'(?:below|under|less than)\s*(\d+)', query_lower)
            if match:
                criteria["rent"] = f"below {match.group(1)}"
        elif "above" in query_lower or "over" in query_lower or "more than" in query_lower:
            match = re.search(r'(?:above|over|more than)\s*(\d+)', query_lower)
            if match:
                criteria["rent"] = f"above {match.group(1)}"
        elif "between" in query_lower:
            match = re.search(r'between\s*(\d+)\s*(?:and|to)\s*(\d+)', query_lower)
            if match:
                criteria["rent"] = f"between {match.group(1)} and {match.group(2)}"
        else:
            match = re.search(r'(?:rent|price|cost)\s*(?:of|:|)?\s*(\d+)', query_lower)
            if match:
                criteria["rent"] = match.group(1)
    
    # Extract size information
    if any(word in query_lower for word in ["size", "area", "sqft", "square feet"]):
        if "below" in query_lower or "under" in query_lower or "less than" in query_lower:
            match = re.search(r'(?:below|under|less than)\s*(\d+)', query_lower)
            if match:
                criteria["size"] = f"below {match.group(1)}"
        elif "above" in query_lower or "over" in query_lower or "more than" in query_lower:
            match = re.search(r'(?:above|over|more than)\s*(\d+)', query_lower)
            if match:
                criteria["size"] = f"above {match.group(1)}"
        elif "between" in query_lower:
            match = re.search(r'between\s*(\d+)\s*(?:and|to)\s*(\d+)', query_lower)
            if match:
                criteria["size"] = f"between {match.group(1)} and {match.group(2)}"
        else:
            match = re.search(r'(?:size|area|sqft|square feet)\s*(?:of|:|)?\s*(\d+)', query_lower)
            if match:
                criteria["size"] = match.group(1)
    
    # Extract bedroom information
    if any(word in query_lower for word in ["bedroom", "bhk", "bed"]):
        match = re.search(r'(\d+)\s*(?:bedroom|bhk|bed)', query_lower)
        if match:
            criteria["bedrooms"] = match.group(1)
    
    # Extract area/location information
    if any(word in query_lower for word in ["area", "location", "locality", "in", "at"]):
        for area in unique_values["areas"]:
            if area.lower() in query_lower:
                criteria["area"] = area
                break
    
    # Extract furnishing status
    if any(word in query_lower for word in ["furnishing", "furnished", "unfurnished", "semi-furnished"]):
        if "unfurnished" in query_lower:
            criteria["furnishing"] = "unfurnished"
        elif "semi-furnished" in query_lower:
            criteria["furnishing"] = "semi-furnished"
        elif "furnished" in query_lower:
            criteria["furnishing"] = "furnished"
    
    # Extract property type
    if any(word in query_lower for word in ["flat", "apartment", "house", "villa", "property type"]):
        if "flat" in query_lower or "apartment" in query_lower:
            criteria["property_type"] = "flat"
        elif "house" in query_lower:
            criteria["property_type"] = "house"
        elif "villa" in query_lower:
            criteria["property_type"] = "villa"
    
    # Extract room type
    if "bhk" in query_lower:
        match = re.search(r'(\d+)\s*bhk', query_lower)
        if match:
            criteria["room_type"] = f"{match.group(1)} bhk"
    
    # Extract property IDs for comparison
    if "compare" in query_lower:
        ids = re.findall(r'\b\d+\b', query)
        if len(ids) >= 2:
            criteria["compare"] = ids
    
    return criteria

# --- Streamlit App ---
def main():
    st.set_page_config(
        page_title="Rental Property Finder",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🏠 Rental Property Finder")
    st.markdown("Find your perfect rental property with our friendly AI assistant!")
    
    # Sidebar with examples and help
    st.sidebar.title("🔍 Search Examples")
    st.sidebar.markdown("""
    Try these examples:
    - 2 BHK flats under ₹15000 rent
    - Furnished apartments in Downtown area
    - Houses with 3 bedrooms above 1000 sqft
    - Compare properties 101, 105, and 110
    - Unfurnished apartments with gym and pool
    """)
    
    st.sidebar.title("💡 Tips")
    st.sidebar.markdown("""
    - You can combine multiple criteria in one query
    - Use natural language like you're talking to a person
    - For comparison, mention "compare" followed by property IDs
    - Be specific about location, price range, and amenities
    """)
    
    # Initialize session state
    if 'query' not in st.session_state:
        st.session_state.query = ""
    if 'results' not in st.session_state:
        st.session_state.results = []
    
    # Search input
    st.subheader("What are you looking for?")
    query = st.text_input(
        "Describe your ideal rental property:",
        placeholder="e.g., 2 BHK furnished apartment under ₹20000 in Downtown area",
        key="query_input"
    )
    
    # Search button
    if st.button("🔍 Search Properties", type="primary"):
        if not query:
            st.warning("Please enter a search query.")
        else:
            with st.spinner("Searching for properties..."):
                criteria = extract_search_criteria(query)
                
                if not criteria:
                    st.error("I didn't understand your query. Please try rephrasing it.")
                else:
                    # Handle property comparison
                    if "compare" in criteria:
                        property_ids = criteria["compare"]
                        if len(property_ids) < 2:
                            st.warning("Please provide at least two Property IDs to compare.")
                        else:
                            comparison_table = compare_properties_side_by_side(
                                properties_data, 
                                [pid.lower() for pid in property_ids]
                            )
                            if comparison_table:
                                st.subheader("Property Comparison")
                                st.markdown(comparison_table, unsafe_allow_html=True)
                    else:
                        # Apply filters based on extracted criteria
                        results = properties_data
                        for field, value in criteria.items():
                            results = filter_properties(value, field, results)
                        
                        if not results:
                            st.warning("No properties found matching your criteria. Try adjusting your search.")
                        else:
                            st.session_state.results = results
                            st.success(f"Found {len(results)} properties matching your criteria!")
    
    # Display results
    if st.session_state.results:
        st.subheader("🏠 Search Results")
        
        # Group results by property type
        grouped_results = defaultdict(list)
        for prop in st.session_state.results:
            property_type = prop.get("Room_Details", {}).get("Type", "Other/Unspecified Type")
            grouped_results[property_type].append(prop)
        
        # Display results by property type
        for prop_type, props in grouped_results.items():
            with st.expander(f"🏠 {str(prop_type).title()} ({len(props)} results)", expanded=True):
                for prop in props:
                    st.markdown(format_property(prop))
                    st.markdown("---")
    
    # Clear results button
    if st.session_state.results:
        if st.button("Clear Results"):
            st.session_state.results = []
            st.experimental_rerun()

if __name__ == "__main__":
    main()
