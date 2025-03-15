import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import requests

app = Flask(__name__)
socketio = SocketIO(app)

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

@app.route("/rider/confirm-location")
def confirm_location():
    return render_template("rider/confirm_location.html")

@app.route("/rider/ride-confirmed")
def ride_confirmed():
    return render_template("rider/ride_confirmed.html")

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

@socketio.on('register_rider')
def handle_register_rider(data):
    print("Rider registered:", data)
    join_room('riders')  # Add to riders room

@socketio.on('rider/send_request')
def handle_send_request(data):
    print("Rider sent ride request:", data)
    # Notify all drivers
    socketio.emit('new_ride_request', data, room='drivers')

@socketio.on('driver/accept_request')
def handle_accept_request(data):
    print("Driver accepted the ride:", data)
    # Forward to rider side (if you know rider SID or use a room)
    socketio.emit('driver_response', data, room='riders')

@socketio.on('driver_response')
def handle_driver_response(data):
    print("Driver response acknowledged by server:", data)
    socketio.emit('show_driver_response', data, room='riders')

# ---------- MAIN ----------
if __name__ == '__main__':
    socketio.run(app, port=5000, debug=True)
