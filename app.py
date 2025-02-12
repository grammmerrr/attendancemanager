import os
import json
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ✅ Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
db = SQLAlchemy(app)

# ✅ Slack Bot Token
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=SLACK_BOT_TOKEN)

# ✅ Attendance Model
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    user_name = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# ✅ Initialize DB
with app.app_context():
    db.create_all()

@app.route('/slack/events', methods=['POST'])
def slack_events():
    """Handles Slack Event Subscriptions and Challenge Verification."""
    data = request.json
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    return jsonify({"status": "OK"}), 200

@app.route('/')
def home():
    return "✅ Flask Slack Bot Running!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
