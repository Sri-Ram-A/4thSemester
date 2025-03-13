from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/ride-request')
def ride_request():
    return render_template('ride-request.html')

@app.route('/ride-details')
def ride_details():
    return render_template('ride-details.html')

@app.route('/otp')
def otp():
    return render_template('otp.html')

if __name__ == '__main__':
    app.run(debug=True,port=3000)