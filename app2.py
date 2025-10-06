import streamlit as st
import json
import re
from collections import defaultdict

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
    "property_type": ALL_PROPERTY_TYPES,
    "facilities": ALL_FACILITIES,
    "nearby_amenities": ALL_NEARBY_AMENITIES 
}

# --- Filtering logic ---
def filter_properties(user_input, field, data):
    filtered_properties = []

    # Map search field to the actual key in properties_data
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

    # --- String fields ---
    normalized_user_input = user_input.lower().strip()
    if field in ["brokerage", "furnishing", "maintenance", "recommended_for", "water_supply", "society_type"]:
        filtered_properties = [p for p in data if str(p.get(data_field, "N/A")).lower() == normalized_user_input]

    elif field == "facilities":
        user_facilities = [normalize_facility_name(f) for f in user_input.split(',')]
        filtered_properties = [
            p for p in data 
            if all(
                any(normalize_facility_name(k) == fac and v == 1 
                    for k, v in p.get("Facilities", {}).items())
                for fac in user_facilities
            )
        ]

    elif field == "nearby_amenities":
        user_facilities = [normalize_facility_name(f) for f in user_input.split(',')]
        filtered_properties = [
            p for p in data 
            if all(
                any(normalize_facility_name(k) == fac and v == 1 
                    for k, v in p.get("Nearby_Amenities", {}).items())
                for fac in user_facilities
            )
        ]

    elif field == "room_type":
        filtered_properties = [p for p in data if normalize_room_name(p.get("Room_Details", {}).get("Rooms", "")) == normalized_user_input]

    elif field == "property_type":
        filtered_properties = [p for p in data if normalize_property_type_name(p.get("Room_Details", {}).get("Type", "")) == normalized_user_input]

    elif field == "area":
        filtered_properties = [p for p in data if normalize_area_name(p.get("Area", "N/A")) == normalize_area_name(user_input)]

    elif field == "zone":
        filtered_properties = [p for p in data if normalize_zone_name(p.get("Zone", "N/A")) == normalize_zone_name(user_input)]

    elif field == "id":
        filtered_properties = [p for p in data if str(p.get(data_field)) == user_input.strip()]

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
        f"**ID:** {property_id} | **Rent:** ₹{rent_price} | **Size:** {size} sqft | **Carpet Area:** {carpet_area} sqft\n"
        f"**Rooms:** {rooms} | **Property Type:** {property_type} | **Bedrooms:** {bedrooms} | **Bathrooms:** {bathrooms} | **Balcony:** {balcony}\n"
        f"**Furnishing:** {furnishing_status} | **Security Deposit:** ₹{security_deposit} | **Brokerage:** {brokerage}\n"
        f"**Amenities:** {amenities}\n"
        f"**Facilities:** {facilities}\n"
        f"**Nearby Amenities:** {nearby_amenities}\n"
        f"**Floor:** {floor_no}/{total_floors} | **Maintenance:** {maintenance} | **Recommended For:** {recommended_for}\n"
        f"**Water Supply:** {water_supply} | **Society:** {society_type} | **Road Connectivity:** {road_connectivity} km\n"
        f"**Age:** {age} years | **Area:** {area} | **Zone:** {zone}"
    )

# --- Extract filters from natural language using regex ---
def extract_filters_from_text(text):
    """Extract property search filters from natural language text using regex"""
    filters = {}
    text_lower = text.lower()
    
    # Extract rent/price
    rent_patterns = [
        r'rent\s+(?:below|under|less\s+than)\s+(\d+)',
        r'rent\s+(?:above|over|more\s+than)\s+(\d+)',
        r'rent\s+between\s+(\d+)\s+and\s+(\d+)',
        r'rent\s+of\s+(\d+)',
        r'price\s+(?:below|under|less\s+than)\s+(\d+)',
        r'price\s+(?:above|over|more\s+than)\s+(\d+)',
        r'price\s+between\s+(\d+)\s+and\s+(\d+)',
        r'price\s+of\s+(\d+)',
        r'(?:below|under|less\s+than)\s+(\d+)\s+rent',
        r'(?:above|over|more\s+than)\s+(\d+)\s+rent',
        r'between\s+(\d+)\s+and\s+(\d+)\s+rent',
        r'(\d+)\s+rent'
    ]
    
    for pattern in rent_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if "between" in pattern:
                filters["rent"] = f"between {match.group(1)} and {match.group(2)}"
            elif "below" in pattern or "under" in pattern or "less" in pattern:
                filters["rent"] = f"below {match.group(1)}"
            elif "above" in pattern or "over" in pattern or "more" in pattern:
                filters["rent"] = f"above {match.group(1)}"
            else:
                filters["rent"] = match.group(1)
            break
    
    # Extract bedrooms
    bedroom_patterns = [
        r'(\d+)\s+bedroom',
        r'(\d+)\s+bedrooms',
        r'(\d+)\s+bhk',
        r'(\d+)\s+rk'
    ]
    
    for pattern in bedroom_patterns:
        match = re.search(pattern, text_lower)
        if match:
            filters["bedrooms"] = match.group(1)
            break
    
    # Extract bathrooms
    bathroom_patterns = [
        r'(\d+)\s+bathroom',
        r'(\d+)\s+bathrooms',
        r'(\d+)\s+bath'
    ]
    
    for pattern in bathroom_patterns:
        match = re.search(pattern, text_lower)
        if match:
            filters["bathrooms"] = match.group(1)
            break
    
    # Extract area
    for area in ALL_AREAS:
        if area.lower() in text_lower:
            filters["area"] = area
            break
    
    # Extract property type
    for prop_type in ALL_PROPERTY_TYPES:
        if prop_type.lower() in text_lower:
            filters["property_type"] = prop_type
            break
    
    # Extract room type
    for room_type in ALL_ROOM_TYPES:
        if room_type.lower() in text_lower:
            filters["room_type"] = room_type
            break
    
    # Extract furnishing
    if "furnished" in text_lower:
        if "semi" in text_lower and "furnished" in text_lower:
            filters["furnishing"] = "semi furnished"
        elif "unfurnished" in text_lower:
            filters["furnishing"] = "unfurnished"
        else:
            filters["furnishing"] = "furnished"
    
    # Extract brokerage
    if any(phrase in text_lower for phrase in ["no brokerage", "without brokerage", "zero brokerage", "free brokerage"]):
        filters["brokerage"] = "no"
    elif "with brokerage" in text_lower or "brokerage" in text_lower:
        filters["brokerage"] = "yes"
    
    # Extract facilities
    facilities_found = []
    for facility in ALL_FACILITIES:
        facility_name = facility.replace("_", " ").lower()
        if facility_name in text_lower:
            facilities_found.append(facility)
    
    if facilities_found:
        filters["facilities"] = ", ".join(facilities_found)
    
    # Extract amenities count
    amenities_patterns = [
        r'amenities\s+(?:below|under|less\s+than)\s+(\d+)',
        r'amenities\s+(?:above|over|more\s+than)\s+(\d+)',
        r'amenities\s+between\s+(\d+)\s+and\s+(\d+)',
        r'amenities\s+of\s+(\d+)',
        r'(?:below|under|less\s+than)\s+(\d+)\s+amenities',
        r'(?:above|over|more\s+than)\s+(\d+)\s+amenities',
        r'between\s+(\d+)\s+and\s+(\d+)\s+amenities',
        r'(\d+)\s+amenities'
    ]
    
    for pattern in amenities_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if "between" in pattern:
                filters["amenities"] = f"between {match.group(1)} and {match.group(2)}"
            elif "below" in pattern or "under" in pattern or "less" in pattern:
                filters["amenities"] = f"below {match.group(1)}"
            elif "above" in pattern or "over" in pattern or "more" in pattern:
                filters["amenities"] = f"above {match.group(1)}"
            else:
                filters["amenities"] = match.group(1)
            break
    
    # Extract size
    size_patterns = [
        r'size\s+(?:below|under|less\s+than)\s+(\d+)',
        r'size\s+(?:above|over|more\s+than)\s+(\d+)',
        r'size\s+between\s+(\d+)\s+and\s+(\d+)',
        r'size\s+of\s+(\d+)\s*sqft',
        r'(?:below|under|less\s+than)\s+(\d+)\s*sqft',
        r'(?:above|over|more\s+than)\s+(\d+)\s*sqft',
        r'between\s+(\d+)\s+and\s+(\d+)\s*sqft',
        r'(\d+)\s*sqft'
    ]
    
    for pattern in size_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if "between" in pattern:
                filters["size"] = f"between {match.group(1)} and {match.group(2)}"
            elif "below" in pattern or "under" in pattern or "less" in pattern:
                filters["size"] = f"below {match.group(1)}"
            elif "above" in pattern or "over" in pattern or "more" in pattern:
                filters["size"] = f"above {match.group(1)}"
            else:
                filters["size"] = match.group(1)
            break
    
    # Extract age
    age_patterns = [
        r'age\s+(?:below|under|less\s+than)\s+(\d+)',
        r'age\s+(?:above|over|more\s+than)\s+(\d+)',
        r'age\s+between\s+(\d+)\s+and\s+(\d+)',
        r'age\s+of\s+(\d+)\s*years?',
        r'(?:below|under|less\s+than)\s+(\d+)\s*years?',
        r'(?:above|over|more\s+than)\s+(\d+)\s*years?',
        r'between\s+(\d+)\s+and\s+(\d+)\s*years?',
        r'(\d+)\s*years?'
    ]
    
    for pattern in age_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if "between" in pattern:
                filters["age"] = f"between {match.group(1)} and {match.group(2)}"
            elif "below" in pattern or "under" in pattern or "less" in pattern:
                filters["age"] = f"below {match.group(1)}"
            elif "above" in pattern or "over" in pattern or "more" in pattern:
                filters["age"] = f"above {match.group(1)}"
            else:
                filters["age"] = match.group(1)
            break
    
    # Extract property ID
    id_match = re.search(r'id\s*[:\s]*(\d+)', text_lower)
    if id_match:
        filters["id"] = id_match.group(1)
    
    return filters

# --- Streamlit App ---
st.set_page_config(page_title="Property Search Chatbot", layout="wide")
st.title("🏠 Property Search Chatbot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Describe the property you're looking for (e.g., '2 BHK in Andheri with rent below 20000')"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Process the query
    try:
        # Check for exit command
        if prompt.lower() == "exit":
            response = "Goodbye!"
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
        
        # Extract filters from natural language
        filters = extract_filters_from_text(prompt)
        
        # If no filters found, ask for clarification
        if not filters:
            response = "I'm sorry, I couldn't understand your search criteria. Please try again with more specific terms like '2 BHK in Andheri with rent below 20000'."
        else:
            # Apply filters
            results = properties_data
            for field, value in filters.items():
                results = filter_properties(value, field, results)
            
            # Format response
            if not results:
                response = "❌ No properties found matching your search."
            else:
                response = f"✅ Found {len(results)} properties matching your search.\n\n"
                
                # Group results by property type
                grouped_results = defaultdict(list)
                for prop in results:
                    property_type = prop.get("Room_Details", {}).get("Type", "Other/Unspecified Type")
                    grouped_results[property_type].append(prop)
                
                # Format each property type group
                for prop_type, props in grouped_results.items():
                    response += f"--- 🏠 Property Type: {str(prop_type).title()} ({len(props)} results) ---\n\n"
                    for prop in props:
                        response += format_property(prop) + "\n\n----------------------------------------\n\n"
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
    except Exception as e:
        response = f"❌ Error processing your request: {str(e)}"
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Rerun to display the new messages
    st.rerun()

# Display help information
with st.expander("💡 Search Examples & Tips"):
    st.markdown("""
    **Natural Language Search Examples:**
    - "2 BHK in Andheri with rent below 20000"
    - "3 bedroom flat in Mumbai with gym and swimming pool"
    - "House with 2 bathrooms, semi furnished, no brokerage"
    - "Property above 1000 sqft in South Mumbai"
    - "1 RK under 15000 rent in Bandra"
    - "Apartments with amenities above 5"
    - "Property ID 12345"
    
    **Supported Search Criteria:**
    - Rent/Price (e.g., "below 20000", "above 15000", "between 10000 and 20000")
    - Bedrooms (e.g., "2 bedrooms", "3 bhk")
    - Bathrooms (e.g., "2 bathrooms", "1 bath")
    - Area/Location (e.g., "in Andheri", "in Bandra")
    - Property Type (e.g., "flat", "house", "apartment")
    - Room Type (e.g., "1 BHK", "2 RK")
    - Furnishing (e.g., "furnished", "semi furnished", "unfurnished")
    - Brokerage (e.g., "no brokerage", "with brokerage")
    - Facilities (e.g., "with gym", "having swimming pool")
    - Amenities Count (e.g., "amenities above 5")
    - Size (e.g., "size above 1000", "size between 800 and 1200")
    - Age (e.g., "age below 5 years")
    - Property ID (e.g., "ID 12345")
    
    **Commands:**
    - `exit` - Exit the chatbot
    """)
