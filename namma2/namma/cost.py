import requests
import folium
from geopy.geocoders import Nominatim

# Your TomTom API Key
API_KEY = "MexiPby9cseRStOBWLta27NtzUcGwwFV"

def get_coordinates(location):
    """Convert place names to latitude & longitude."""
    geolocator = Nominatim(user_agent="geoapi")
    location_data = geolocator.geocode(location)
    if location_data:
        return location_data.latitude, location_data.longitude
    else:
        print(f"Could not find coordinates for {location}.")
        exit()

def get_route(source, destination):
    """Fetch shortest route & distance using TomTom Routing API."""
    URL = f"https://api.tomtom.com/routing/1/calculateRoute/{source[0]},{source[1]}:{destination[0]},{destination[1]}/json?key={API_KEY}"
    
    response = requests.get(URL)
    if response.status_code == 200:
        data = response.json()
        route_points = [(p["latitude"], p["longitude"]) for leg in data["routes"][0]["legs"] for p in leg["points"]]
        distance_km = data["routes"][0]["summary"]["lengthInMeters"] / 1000  # Convert meters to km
        return route_points, distance_km
    else:
        print("Error fetching route:", response.status_code)
        exit()

def get_traffic_density(lat, lon):
    """Fetch real-time traffic congestion data."""
    TRAFFIC_URL = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={API_KEY}&point={lat},{lon}"
    response = requests.get(TRAFFIC_URL)
    if response.status_code == 200:
        data = response.json()
        free_flow_speed = data["flowSegmentData"]["freeFlowSpeed"]
        current_speed = data["flowSegmentData"]["currentSpeed"]
        density = ((free_flow_speed - current_speed) / free_flow_speed) * 100
        return density
    else:
        return None

def calculate_fare(route_points, distance):
    """Calculate fare based on entire route's traffic conditions."""
    base_fare = 30  # ₹ Base charge
    rate_per_km = 15  # ₹ per km
    
    # Count route segments based on traffic density
    blue = green = orange = red = 0
    
    for lat, lon in route_points[::100]:  
        density = get_traffic_density(lat, lon)
        if density is not None:
            if density < 25:
                blue += 1
            elif density < 50:
                green += 1
            elif density < 75:
                orange += 1
            else:
                red += 1
    
    total_distance = blue + green + orange + red or 1  # Prevent division by zero
    multiplier = (blue * 1 + green * 1.2 + orange * 1.5 + red * 2) / total_distance
    total_fare = base_fare + (distance * rate_per_km * multiplier)
    
    return round(total_fare, 2), round(multiplier, 2)

def generate_html(distance, multiplier, fare):
    """Generate an HTML file to display the fare details."""
    html_content = f"""
    <html>
    <head>
        <title>Fare Estimation</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; }}
            .container {{ margin-top: 50px; }}
            .card {{ display: inline-block; background: #f8f8f8; padding: 20px; border-radius: 10px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1); }}
            h2 {{ color: #333; }}
            p {{ font-size: 18px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h2> Travel Details </h2>
                <p> Distance: {distance:.2f} km</p>
                <p> Traffic Multiplier: {multiplier}x</p>
                <p><strong> Estimated Fare: ₹{fare}</strong></p>
            </div>
        </div>
    </body>
    </html>
    """
    with open("fare.html", "w", encoding="utf-8") as file:
        file.write(html_content)
    print("Fare estimation saved as 'fare.html'. Open it in a browser.")

# Get optimized route & distance
def get_price(source_location, destination_location):
    source_coords = get_coordinates(source_location)
    destination_coords = get_coordinates(destination_location)
    route_points, distance = get_route(source_coords, destination_coords)
    # Calculate fare based on entire route's traffic conditions
    fare, surge_multiplier = calculate_fare(route_points, distance)
    return fare

# pickup='Kengeri'
# destination='KR Puram'
# predicted_fare=get_price(pickup,destination)
# print(predicted_fare)