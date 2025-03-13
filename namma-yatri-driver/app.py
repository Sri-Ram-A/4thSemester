from flask import Flask, render_template

app = Flask(__name__)

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
if __name__ == '__main__':
    app.run(debug=True)