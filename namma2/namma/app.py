import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from flask_cors import CORS  # Import CORS
eventlet.monkey_patch()
from junctions import gcfa, get_intermediate_junctions

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for all routes and origins
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')  # Configure SocketIO with CORS


# MongoDB connection setup
uri = "mongodb+srv://sriramaai23:sriramaai23@namma-yatri-cluster.o9bxu.mongodb.net/?retryWrites=true&w=majority&appName=namma-yatri-cluster"
client = MongoClient(uri, server_api=ServerApi('1'))
# Global variable to store current ride information

from dotenv import load_dotenv
load_dotenv()

active_rides = {}
import requests
import os
from geopy.geocoders import Nominatim

# Your TomTom API Key
API_KEY=os.getenv('TOMTOM_API_KEY')

def get_coordinates(location):
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

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
    db = client['namma-yatri-database']  # Replace with your database name
except Exception as e:
    print(e)

# ---------- LOGIN ROUTES ----------
# 🟢 Route for Driver Login
@app.route("/driver/login", methods=["GET", "POST"])
def driver_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        driver = db.drivers.find_one({"email": email})
        
        if driver and check_password_hash(driver["password"], password):
            session["driver"] = email
            flash("Login successful!", "success")
            return render_template('driver/index.html')  # Redirect to driver dashboard
        else:
            flash("Invalid email or password!", "danger")

    return render_template("driver/login.html")

# 🟢 Route for User Login
@app.route("/rider/login", methods=["GET", "POST"])
def rider_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]  
        user = db.riders.find_one({"email": email})
        
        if user and check_password_hash(user["password"], password):
            session["user"] = email
            flash("Login successful!", "success")
            return render_template("rider/index.html")  # Redirect to user dashboard
        else:
            flash("Invalid email or password!", "danger")

    return render_template("rider/login.html")

# 🟢 Driver Registration Route
@app.route("/driver/register", methods=["GET", "POST"])
def driver_register():
    if request.method == "POST":
        name = request.form["name"]
        gender = request.form.get('gender')
        email = request.form["email"]
        unique_id = request.form["unique_id"]
        phone = request.form["phone"]
        alt_phone = request.form["alt_phone"]
        dl_no = request.form["dl_no"]
        vehicle_no = request.form["vehicle_no"]
        city = request.form["city"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        if gender=='male':
            profile=f'https://avatar.iran.liara.run/public/boy?username={name}'
        elif gender=='female':
            profile=f'https://avatar.iran.liara.run/public/girl?username={name}'
        else:
            profile=f'https://avatar.iran.liara.run/username?username={name}'

        # 🛠️ Ensure all fields are filled
        if not (name and email and unique_id and phone and alt_phone and dl_no and vehicle_no and city and password and confirm_password):
            flash("All fields are required!", "danger")
            return render_template("driver/register.html")

        # 🛠️ Check if passwords match
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return render_template("driver/register.html")

        # 🛠️ Check if email already exists
        existing_driver = db.drivers.find_one({"email": email})
        if existing_driver:
            flash("Email already registered!", "danger")
            return render_template("driver/register.html")

        # 🛠️ Securely store password
        hashed_password = generate_password_hash(password)

        # 🛠️ Insert driver data into MongoDB
        driver_data = {
            "name": name,
            "email": email,
            'gender':gender,
            "unique_id": unique_id,
            "phone": phone,
            "alt_phone": alt_phone,
            "dl_no": dl_no,
            "vehicle_no": vehicle_no,
            "city": city,
            "password": hashed_password,
            'profile':profile,
        }
        db.drivers.insert_one(driver_data)

        flash("Driver registered successfully! Please log in.", "success")
        return render_template("driver/login.html")

    return render_template("driver/register.html")

# 🟢 User Registration
@app.route("/rider/register", methods=["GET", "POST"])
def rider_register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # 🛠️ Ensure all fields are filled
        if not username or not email or not password or not confirm_password:
            flash("All fields are required!", "danger")
            return render_template("rider/register.html")

        # 🛠️ Check if passwords match
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return render_template("rider/register.html")

        # 🛠️ Check if username or email already exists
        existing_user = db.riders.find_one({"$or": [{"name": username}, {"email": email}]})
        if existing_user:
            flash("Username or email already taken!", "danger")
            return render_template("rider/register.html")

        # 🛠️ Securely store password
        hashed_password = generate_password_hash(password)

        # 🛠️ Insert new user into MongoDB
        db.riders.insert_one({"name": username, "email": email, "password": hashed_password})

        flash("Registration successful! Please log in.", "success")
        return render_template("rider/login.html") # Redirect to login page

    return render_template("rider/register.html")

@app.route("/")
def beginning():
    return render_template("index.html")

# ---------- RIDER ROUTES ----------
@app.route("/rider")
def rider_home():
    return render_template("rider/index.html")

@app.route("/rider/intro")
def intro():
    return render_template("rider/intro.html")

@app.route("/rider/search")
def search():

    return render_template("rider/search.html")



@app.route("/rider/confirm_location", methods=["GET", "POST"])
def confirm_location():
    rider_id = None
    pickup = ""
    destination = ""
    predicted_fare=0

    # 🟡 Step 1: Get the logged-in rider's email from session
    if "user" in session:
        user_email = session["user"]
        # 🟡 Step 2: Fetch rider record from DB
        rider = db.riders.find_one({"email": user_email})
        if rider:
            rider_id = str(rider.get("_id"))  # Convert ObjectId to string if needed
            print("Rider ID:", rider_id)

    if request.method == 'POST':
        pickup = request.form.get('pickup')
        session["pickup"]= pickup
        destination = request.form.get('destination')
        print("Pickup:", pickup)
        print("Destination:", destination)
        # predicted_fare=get_price(pickup,destination)
        pickup_coordinates = gcfa(pickup)
        drop_coords = gcfa(destination)
        session['coordinates']={"source_coordinates":pickup_coordinates,"destination_coordinates":drop_coords,pickup:session["pickup"]}
        session['destination'] = destination        

    return render_template('rider/confirm_location.html', pickup=pickup, destination=destination, rider_id=rider_id,predicted_fare=predicted_fare, pickup_coordinates = gcfa(pickup), drop_coords = gcfa(destination))

@app.route("/rider/ride_confirmed")
def ride_confirmed():
    rider_id = None
    driver_data = None
    
    # Get the logged-in rider's email from session
    if "user" in session:
        user_email = session["user"]
        rider = db.riders.find_one({"email": user_email})
        if rider:
            rider_id = str(rider.get("_id"))
            
            # Check if there's an active ride for this rider
            if rider_id in active_rides:
                driver_email = active_rides[rider_id].get('driver_email')
                if driver_email:
                    # Fetch driver details from MongoDB
                    driver = db.drivers.find_one({"email": driver_email})
                    if driver:
                        driver_data = {
                            "name": driver.get("name", "Driver"),
                            "vehicle_no": driver.get("vehicle_no", "Unknown"),
                            "phone": driver.get("phone", ""),
                            "profile": driver.get("profile", ""),
                            "rate": driver.get("rate", "python"),  # Default rate if not provided
                            "rating": "4.83",  # You could calculate this from ratings collection
                        }
    if "coordinates" in session:
        source_coordinates=session["coordinates"]["source_coordinates"]
        destination_coordinates=session["coordinates"]["destination_coordinates"]
    
    return render_template("rider/ride_confirmed.html", driver=driver_data, MAPBOX_API=os.getenv('MAPBOX'),source_coordinates=source_coordinates,destination_coordinates=destination_coordinates)

@app.route("/rider/split_ride_confirmed")
def split_ride_confirmed():
    rider_id = None
    driver_data = None
    
    # Get the logged-in rider's email from session
    if "user" in session:
        user_email = session["user"]
        rider = db.riders.find_one({"email": user_email})
       
        if rider:
            rider_id = str(rider.get("_id"))
            
            # Check if there's an active ride for this rider
            if rider_id in active_rides:
                driver_email = active_rides[rider_id].get('driver_email')
                if driver_email:
                    # Fetch driver details from MongoDB
                    driver = db.drivers.find_one({"email": driver_email})
                    if driver:
                        driver_data = {
                            "name": driver.get("name", "Driver"),
                            "vehicle_no": driver.get("vehicle_no", "Unknown"),
                            "phone": driver.get("phone", ""),
                            "profile": driver.get("profile", ""),
                            "rate": driver.get("rate", "python"),  # Default rate if not provided
                            "rating": "4.83",  # You could calculate this from ratings collection
                        }
    

    jns = get_intermediate_junctions(session["pickup"], session["destination"])
    if jns:
        return render_template("rider/split_ride_confirmed.html", jns=jns, driver=driver_data, MAPBOX_API=os.getenv('MAPBOX'), pickup_location=session["pickup"], destination_location = session["destination"],source_coordinates=session["coordinates"]["source_coordinates"],destination_coordinates=session["coordinates"]["destination_coordinates"])
    else:
        return render_template("rider/ride_confirmed.html", driver=driver_data, MAPBOX_API=os.getenv('MAPBOX'),source_coordinates=session["coordinates"]["source_coordinates"],destination_coordinates=session["coordinates"]["destination_coordinates"])


# ---------- DRIVER ROUTES ----------
@app.route("/driver")
def home():
    return render_template("driver/index.html", hide_nav=True)

@app.route("/driver/offline")
def offline():
    return render_template("driver/offline.html")

@app.route("/driver/online")
def online():
    return render_template("driver/online.html")

@app.route("/driver/earnings")
def earnings():
    return render_template("driver/earnings.html")

@app.route("/driver/profile")
def profile():
    return render_template("driver/profile.html")

@app.route("/driver/bookingPreferences")
def booking_preferences():
    return render_template("driver/bookingPreferences.html")

@app.route("/driver/leaderboard")
def leaderboard():
    # Example dynamic data (replace with data from your database)
    drivers = [
        {"name": "RideMaster", "rides": 42, "points": 1245, "change": "+5"},
        {"name": "SpeedDemon", "rides": 38, "points": 1145, "change": "+3"},
        {"name": "NightRider", "rides": 35, "points": 1050, "change": "+1"},
        {"name": "RoadWarrior", "rides": 32, "points": 990, "change": "-2"},
        {"name": "UrbanRider", "rides": 30, "points": 956, "change": "+2"},
        {"name": "CitySlicker", "rides": 28, "points": 910, "change": "0"},
        {"name": "MountainKing", "rides": 27, "points": 876, "change": "+3"},
        {"name": "HighRoller", "rides": 25, "points": 840, "change": "-1"},
        {"name": "EcoRider", "rides": 23, "points": 795, "change": "+4"},
        {"name": "RushHour", "rides": 21, "points": 760, "change": "-2"},
    ]

    # Sort drivers by points in descending order
    drivers_sorted = sorted(drivers, key=lambda x: x["points"], reverse=True)

    return render_template("driver/leaderboard.html", drivers=drivers_sorted)
@app.route("/driver/hello")
def hello():
    return render_template("driver/hello.html")


@app.route('/driver/graphs', methods=['GET', 'POST'])
def graphs():
    import pandas as pd
    dataset_number = request.args.get('dataset', default=1, type=int)
    
    # Load the selected dataset
    actual_df = pd.read_csv(f'dataset/actual_fare_costs{dataset_number}.csv')
    predicted_df = pd.read_csv(f'dataset/predicted_fare_costs{dataset_number}.csv')
    
    # Convert timestamps and get the data
    timestamps = actual_df['timestamp'].tolist()
    actual_fares = actual_df['actual_fare'].tolist()
    predicted_fares = predicted_df['predicted_fare'].tolist()
    
    return render_template('driver/graphs.html',
                         timestamps=timestamps,
                         actual_fares=actual_fares,
                         predicted_fares=predicted_fares,
                         dataset_number=dataset_number)

# ---------- API ENDPOINTS ----------
@app.route('/driver/receive_request', methods=['POST'])
def receive_request():
    data = request.json
    print("Driver received ride request:", data)
    # Broadcast to all drivers in the 'drivers' room
    socketio.emit('new_ride_request', data, room='drivers')
    return "Driver received request", 200

# ---------- SOCKET EVENTS ----------
@socketio.on('connect')
def handle_connect():
    print("Client connected:", request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected:", request.sid)

@socketio.on('register_driver')
def handle_register_driver(data):
    print("Driver registered:", data)
    join_room('drivers')  # Add to drivers room
    
    # Store driver's socket id and email for later use
    driver_id = data.get('driver_id')
    if "driver" in session:
        driver_email = session["driver"]
        # You could store this mapping in a dictionary or database
        print(f"Registered driver {driver_email} with socket ID {request.sid}")


@socketio.on('register_rider')
def handle_register_rider(data):
    print("Rider registered:", data)
    join_room('riders')  # Add to riders room

from bson.objectid import ObjectId  # Important for querying MongoDB by _id

@socketio.on('rider/send_request')
def handle_send_request(data):
    print("Rider sent ride request:", data)

    # Get rider_id from incoming data (should be a string, convert to ObjectId)
    rider_id = data.get("rider_id")
    if not rider_id:
        print("No rider_id provided!")
        return

    try:
        rider = db.riders.find_one({"_id": ObjectId(rider_id)})
        if not rider:
            print("Rider not found!")
            return
        import datetime
        # Prepare all rider details to send to drivers
        ride_request = {
            "rider_id": str(rider["_id"]),
            "name": rider.get("name", ""),
            "email": rider.get("email", ""),
            "phone": rider.get("phone", ""),
            "pickup": data.get("pickup", ""),
            "destination": data.get("destination", "")
            # ,
            # "timestamp": datetime.datetime.now()
        }

        print("Emitting ride request to drivers:", ride_request)

        # Emit to all drivers in 'drivers' room
        socketio.emit('new_ride_request', ride_request, room='drivers')

    except Exception as e:
        print("Error in handle_send_request:", str(e))

@socketio.on('driver/accept_request')
def handle_accept_request(data):
    print("Driver accepted the ride:", data)
    
    driver_id = data.get('driver_id')
    ride_id = data.get('ride_id')
    rider_id = data.get('rider_id')
    
    # Get the logged-in driver's email from session or data
    driver_email = None
    if "driver" in session:
        driver_email = session["driver"]
    else:
        # Try to get driver email from the data if not in session
        driver_email = data.get('driver_email')
    
    if driver_email and rider_id:
        # Fetch driver details from MongoDB
        driver = db.drivers.find_one({"email": driver_email})
        
        if driver:
            # Store driver details in the active_rides dictionary
            active_rides[rider_id] = {
                'driver_email': driver_email,
                'ride_id': ride_id,
                'driver_id': driver_id,
                'status': 'accepted'
            }
            
            # Add driver details to the response
            response_data = {
                'driver_id': driver_id,
                'ride_id': ride_id,
                'status': 'accepted',
                'driver_name': driver.get('name', 'Driver'),
                'driver_phone': driver.get('phone', ''),
                'vehicle_no': driver.get('vehicle_no', ''),
                'driver_profile': driver.get('profile', ''),
                'rider_id': rider_id,
                'rate': driver.get('rate', '200')  # Include the rate in the response
            }
            
            # Forward to rider side
            socketio.emit('driver_response', response_data, room='riders')
        else:
            print("Driver not found in database")
    else:
        print("Missing driver_email or rider_id in accept_request")
        # Still emit the original data if we couldn't enhance it
        socketio.emit('driver_response', data, room='riders')
@socketio.on('driver_response')
def handle_driver_response(data):
    print("Driver response acknowledged by server:", data)
    socketio.emit('show_driver_response', data, room='riders')

@app.route('/confirm_location', methods=['GET','POST'])
def confirm():
    source_coordinates=None
    destination_coordinates=None
    pickup = request.form['pickup']
    destination = request.form['destination']
    if "coordinates" in session:
        source_coordinates=session["coordinates"]["source_coordinates"]
        destination_coordinates=session["coordinates"]["destination_coordinates"]
        print(source_coordinates)
        print(destination_coordinates)

    session["pickup"] = pickup
    session["destination_location"]=destination

    
#     return render_template('rider/confirm_location.html', pickup_location=pickup, destination_location=destination,source_coordinates=source_coordinates,destination_coordinates=destination_coordinates)

# ---------- MAIN ----------
if __name__ == '__main__':
    app.secret_key='sriramaai23'
    socketio.run(app, port=5000, debug=True)

