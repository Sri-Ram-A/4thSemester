import eventlet
# from cost import get_price
eventlet.monkey_patch()
from flask import Flask, render_template, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from flask_cors import CORS  # Import CORS

from junctions import gcfa

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for all routes and origins
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')  # Configure SocketIO with CORS


# MongoDB connection setup
uri = "mongodb+srv://sriramaai23:sriramaai23@namma-yatri-cluster.o9bxu.mongodb.net/?retryWrites=true&w=majority&appName=namma-yatri-cluster"
client = MongoClient(uri, server_api=ServerApi('1'))
# Global variable to store current ride information
active_rides = {}

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
        destination = request.form.get('destination')
        print("Pickup:", pickup)
        print("Destination:", destination)

    return render_template('rider/confirm_location.html', pickup=pickup, destination=destination, rider_id=rider_id, pickup_coordinates = gcfa(pickup), drop_coords = gcfa(destination))

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
                            "rate": driver.get("rate", "100"),  # Default rate if not provided
                            "rating": "4.83",  # You could calculate this from ratings collection
                        }
    
    return render_template("rider/ride_confirmed.html", driver=driver_data)

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
    return render_template("driver/leaderboard.html")

@app.route("/driver/hello")
def hello():
    return render_template("driver/hello.html")

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
                'rate': driver.get('rate', '100')  # Include the rate in the response
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

@app.route('/confirm_location', methods=['POST'])
def confirm():
    pickup = request.form['pickup']
    destination = request.form['destination']
    return render_template('rider/confirm_location.html', pickup_location=pickup, destination_location=destination)

# ---------- MAIN ----------
if __name__ == '__main__':
    app.secret_key='sriramaai23'
    socketio.run(app, port=5000, debug=True)

