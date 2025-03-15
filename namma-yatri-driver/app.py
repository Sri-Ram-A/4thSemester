from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import requests
# driver.py (Flask app on port 5001)
app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html', hide_nav=True)

@app.route('/offline')
def offline():
    return render_template('offline.html')

@app.route('/silent')
def silent():
    return render_template('silent.html')

@app.route('/online')
def online():
    return render_template('online.html')

@app.route('/earnings')
def earnings():
    return render_template('earnings.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')
@app.route('/bookingPreferences')
def bookingPreferences():
    return render_template('bookingPreferences.html')
@app.route('/leaderboard')
def learboard():
    return render_template('leaderboard.html')
@app.route('/hello')
def hello():
    return render_template('hello.html')

# driver.py

@app.route('/receive_request', methods=['POST'])
def receive_request():
    data = request.json
    print("Driver received ride request:", data)
    # Send message to Driver Web UI using SocketIO
    socketio.emit('new_ride_request', data)
    return "Driver received"

@socketio.on('accept_request')
def handle_accept_request(data):
    print("Driver accepting ride:", data)
    # Notify rider server
    requests.post('http://localhost:5000/driver_response', json=data)

if __name__ == '__main__':
    socketio.run(app, port=5001)
