import json
import re
from collections import defaultdict

# --- Load properties from JSON file ---
try:
    with open("property_data.json", "r") as f:
        properties_data = json.load(f)
except FileNotFoundError:
    print("Error: 'property_data.json' not found. Please ensure the file exists.")
    properties_data = []
except json.JSONDecodeError:
    print("Error: Could not decode 'property_data.json'. Please check its format.")
    properties_data = []

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

# --- Define multi-select fields ---
MULTI_SELECT_FIELDS = {"facilities", "nearby_amenities"}

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
        f"ID: {property_id} | Rent: ₹{rent_price} | Size: {size} sqft | Carpet Area: {carpet_area} sqft\n"
        f"Rooms: {rooms} | Property Type: {property_type} | Bedrooms: {bedrooms} | Bathrooms: {bathrooms} | Balcony: {balcony}\n"
        f"Furnishing: {furnishing_status} | Security Deposit: ₹{security_deposit} | Brokerage: {brokerage}\n"
        f"Amenities: {amenities}\n"
        f"Facilities: {facilities}\n"
        f"Nearby Amenities: {nearby_amenities}\n"
        f"Floor: {floor_no}/{total_floors} | Maintenance: {maintenance} | Recommended For: {recommended_for}\n"
        f"Water Supply: {water_supply} | Society: {society_type} | Road Connectivity: {road_connectivity} km\n"
        f"Age: {age} years | Area: {area} | Zone: {zone}\n"
        f"----------------------------------------"
    )

# --- Chatbot ---
def chatbot_response():
    print("Welcome to Property Search Chatbot!")
    print("\nSearch Options:")
    print(
        "1. Size (sqft)\n2. Carpet Area (sqft)\n3. Age of Property\n4. Brokerage (yes/no)\n5. Property ID (exact match)\n"
        "6. Amenities\n7. Furnishing Status\n8. Security Deposit\n9. Rent Price\n10. Area\n11. Zone\n"
        "12. Bedrooms\n13. Bathrooms\n14. Balcony\n15. Floor Number\n16. Total Floors\n17. Maintenance Charge\n"
        "18. Recommended For\n19. Water Supply Type\n20. Society Type\n21. Road Connectivity\n22. Facilities\n"
        "23. Nearby Amenities\n24. Room Type (e.g., 1 BHK)\n25. Property Type (e.g., Flat)\n"
    )
    print("💡 You can combine multiple search fields using '+'.")
    print("Example: 1+2+3 (Size + Carpet Area + Age of Property)")
    print("Type 'exit' to quit.")

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

    search_map = {
        "1": "size", "2": "carpet", "3": "age", "4": "brokerage", "5": "id", "6": "amenities", "7": "furnishing",
        "8": "security", "9": "rent", "10": "area", "11": "zone", "12": "bedrooms", "13": "bathrooms",
        "14": "balcony", "15": "floor_no", "16": "total_floors", "17": "maintenance", "18": "recommended_for",
        "19": "water_supply", "20": "society_type", "21": "road_connectivity", "22": "facilities", "23": "nearby_amenities",
        "24": "room_type", "25": "property_type"
    }
    
    while True:
        field_numbers = input("\nEnter the number(s) of search fields to combine (e.g., 9+10) or 'exit': ").strip().lower()
        if field_numbers == "exit":
            print("Goodbye!")
            break

        selected_fields = []
        is_valid_input = True
        for num in field_numbers.split('+'):
            num = num.strip()
            if num in search_map:
                selected_fields.append(search_map[num])
            else:
                print(f"❌ Invalid field number: '{num}'. Please use a valid number from the list.")
                is_valid_input = False
                break
        
        if not is_valid_input:
            continue

        combined_filters = {}
        for field in selected_fields:
            if field in CATEGORY_OPTIONS and CATEGORY_OPTIONS[field]:
                options = CATEGORY_OPTIONS[field]
                print(f"\nAvailable options for {field.title()}:")
                for idx, option in enumerate(options, start=1):
                    print(f"{idx}. {option}")
                
                if field in MULTI_SELECT_FIELDS:
                    choice = input(f"Enter {field} value(s) (choose number(s) separated by commas or type value(s) separated by commas): ").strip().lower()
                    parts = [part.strip() for part in choice.split(',')]
                    
                    # Check if all parts are digits
                    if all(part.isdigit() for part in parts):
                        selected_indices = [int(part) for part in parts]
                        selected_options = []
                        for idx in selected_indices:
                            if 1 <= idx <= len(options):
                                selected_options.append(options[idx-1])
                            else:
                                print(f"⚠️ Option {idx} is invalid, skipping.")
                        user_input = ','.join(selected_options)
                    else:
                        user_input = choice
                else:
                    choice = input(f"Enter {field} value (choose number or type value): ").strip().lower()
                    if choice.isdigit():
                        choice_idx = int(choice) - 1
                        if 0 <= choice_idx < len(options):
                            user_input = options[choice_idx]
                        else:
                            print("❌ Invalid choice, defaulting to your raw input.")
                            user_input = choice
                    else:
                        user_input = choice
            else:
                user_input = input(f"Enter {field} value: ").strip()
            
            combined_filters[field] = user_input

        # Special case for 'id'
        if "id" in combined_filters:
            prop_id = combined_filters["id"]
            prop = next((p for p in properties_data if str(p.get("property_id")) == prop_id), None)
            if prop:
                print("\n✅ Property Found:")
                print(format_property(prop))
            else:
                print("❌ Property not found.")
            continue
        
        results = properties_data
        for field, value in combined_filters.items():
            results = filter_properties(value, field, results)
        
        if not results:
            print("❌ No properties found matching your combined search.")
        else:
            print(f"\n✅ Found {len(results)} properties matching your combined query.")
            grouped_results = defaultdict(list)
            for prop in results:
                property_type = prop.get("Room_Details", {}).get("Type", "Other/Unspecified Type")
                grouped_results[property_type].append(prop)
            
            for prop_type, props in grouped_results.items():
                print(f"\n--- 🏠 Property Type: {str(prop_type).title()} ({len(props)} results) ---")
                for prop in props:
                    print(format_property(prop))

if __name__ == "__main__":
    chatbot_response()
