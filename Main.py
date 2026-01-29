import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# --- CONFIGURATION ---
# Get API KEY from Environment Variable (Best for security) or use default
API_KEY = os.environ.get("GEOAPIFY_KEY", "YOUR_GEOAPIFY_API_KEY")

def get_coordinates(address):
    url = "https://api.geoapify.com/v1/geocode/search"
    params = {"text": address, "apiKey": API_KEY, "limit": 1}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200 and response.json()['features']:
            coords = response.json()['features'][0]['geometry']['coordinates']
            return coords[1], coords[0]  # Returns (lat, lon)
    except Exception as e:
        print(f"Geocoding Error: {e}")
    return None, None

def find_places(lat, lon, categories, radius_meters, limit=5):
    """Generic function to find places using the Places API"""
    url = "https://api.geoapify.com/v2/places"
    params = {
        "categories": categories,
        "filter": f"circle:{lon},{lat},{radius_meters}",
        "bias": f"proximity:{lon},{lat}",
        "limit": limit,
        "apiKey": API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        results = []
        if response.status_code == 200:
            places = response.json().get('features', [])
            for place in places:
                props = place['properties']
                # Clean up name: use 'name' if available, otherwise formatted address
                name = props.get('name', props.get('address_line1', 'Unnamed Location'))
                distance = props.get('distance', 0)
                results.append({"name": name, "distance_meters": distance})
        return results
    except Exception:
        return []

@app.route('/', methods=['GET'])
def home():
    return "Map Analyzer API is Running!"

@app.route('/analyze', methods=['POST'])
def analyze_property():
    data = request.json
    address = data.get('address')
    
    if not address:
        return jsonify({"error": "No address provided"}), 400

    # 1. Get Coordinates
    lat, lon = get_coordinates(address)
    if not lat:
        return jsonify({"error": "Address not found"}), 404

    # 2. Define Categories
    # FIX: Split Transport into 'Rail' (High Value) and 'Bus' (Low Value)
    rail_categories = "public_transport.subway,public_transport.train,public_transport.light_rail,public_transport.monorail"
    
    surroundings = {
        # Schools: Search 3km
        "Schools": find_places(lat, lon, "education.school", 3000, limit=3),
        
        # Groceries: Search 2km
        "Groceries": find_places(lat, lon, "commercial.supermarket,commercial.convenience", 2000, limit=3),
        
        # Healthcare: Search 5km
        "Healthcare": find_places(lat, lon, "healthcare.hospital,healthcare.clinic", 5000, limit=3),
        
        # FIX: Search specifically for TRAINS up to 3km (Investors care about this)
        "TrainStations": find_places(lat, lon, rail_categories, 3000, limit=3),
        
        # Fallback: Nearest Bus Stop (Closer radius)
        "BusStops": find_places(lat, lon, "public_transport.bus", 500, limit=2)
    }

    response_data = {
        "address": address,
        "coordinates": {"lat": lat, "lon": lon},
        "surroundings": surroundings,
        "market_data_placeholders": {
            "demand": "Run Web Search for this area",
            "supply": "Check listings count"
        }
    }

    return jsonify(response_data)

if __name__ == '__main__':
    # CRITICAL FOR DEPLOYMENT: Use the PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)