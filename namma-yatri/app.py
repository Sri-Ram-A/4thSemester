from flask import Flask, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
import requests
# rider.py (Flask app on port 5000)
app = Flask(__name__)
socketio = SocketIO(app)

# Make sure eventlet is installed and being used

@app.route("/")
def home():
    return render_template("index.html")
@app.route("/intro")
def intro():
    return render_template("intro.html")
@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/confirm-location")
def confirm_location():
    return render_template("confirm_location.html")

@app.route("/ride-confirmed")
def ride_confirmed():
    return render_template("ride_confirmed.html")

if __name__ == "__main__":
    app.run(debug=True)

# rider.py

@socketio.on('send_request')
def handle_send_request(data):
    print("Sending ride request to driver:", data)
    # Forward message to Driver server using HTTP or socket
    requests.post('http://localhost:5001/receive_request', json=data)

@socketio.on('driver_response')
def handle_driver_response(data):
    print("Driver accepted:", data)
    socketio.emit('show_driver_response', data)

if __name__ == '__main__':
    socketio.run(app, port=5000)
