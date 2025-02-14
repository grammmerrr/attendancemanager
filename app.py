from flask import Flask, request, jsonify
import sqlite3
import threading
import requests
from datetime import datetime

app = Flask(__name__)

# Database setup
DB_FILE = "attendance.db"

def init_db():
    """Initialize the database if it does not exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            user_name TEXT,
            command TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return "Slack Attendance Bot is Running! 🚀"

@app.route("/slack/command", methods=["POST"])
def slack_command():
    """Handles Slack commands and immediately responds to prevent timeouts."""
    try:
        data = request.form
        command = data.get("command")
        user_id = data.get("user_id")
        user_name = data.get("user_name")
        response_url = data.get("response_url")  # Get the response URL for delayed responses

        if not command or not user_id or not user_name or not response_url:
            return jsonify({"text": "❌ Missing data in request"}), 400

        print(f"🔄 Received: {command} from {user_name} (ID: {user_id})")  # Debug log

        # Respond immediately to Slack
        response = {"text": f"✅ {command} received for {user_name}, processing..."}
        threading.Thread(
            target=process_command,
            args=(command, user_id, user_name, response_url),
            daemon=True
        ).start()

        return jsonify(response), 200
    except Exception as e:
        print(f"❌ Error in /slack/command: {e}")
        return jsonify({"error": "Internal server error"}), 500

def process_command(command, user_id, user_name, response_url):
    """Background task to process commands and log them."""
    try:
        print(f"🔄 Processing: {command} for {user_name}")  # Debug log
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Log the command to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs (user_id, user_name, command, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, user_name, command, timestamp)
        )
        conn.commit()
        conn.close()

        print(f"✅ Saved: {user_name} - {command} at {timestamp}")  # Debug log

        # Handle specific commands
        if command == "/mylogs":
            # Fetch logs for the user
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT command, timestamp FROM logs WHERE user_id = ? ORDER BY timestamp DESC",
                (user_id,)
            )
            logs = cursor.fetchall()
            conn.close()

            # Format the logs into a message
            if logs:
                log_messages = [f"{cmd} at {time}" for cmd, time in logs]
                message = "📜 Your logs:\n" + "\n".join(log_messages)
            else:
                message = "No logs found for your account."

            # Send the formatted logs to Slack using the response_url
            requests.post(response_url, json={"text": message})

        elif command == "/alllogs":
            # Fetch all logs from the database
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT user_name, command, timestamp FROM logs ORDER BY timestamp DESC")
            logs = cursor.fetchall()
            conn.close()

            # Format the logs into a message
            if logs:
                log_messages = [f"{user} - {cmd} at {time}" for user, cmd, time in logs]
                message = "📜 All logs:\n" + "\n".join(log_messages)
            else:
                message = "No logs found in the database."

            # Send the formatted logs to Slack using the response_url
            requests.post(response_url, json={"text": message})

        elif command == "/checkin":
            # Handle check-in logic (e.g., mark attendance)
            message = f"✅ {user_name}, you have successfully checked in at {timestamp}."
            requests.post(response_url, json={"text": message})

    except Exception as e:
        print(f"❌ Error processing {command}: {e}")  # Catch errors
        error_message = f"❌ Error processing command: {str(e)}"
        requests.post(response_url, json={"text": error_message})

if __name__ == "__main__":
    print("🚀 Starting Flask Server...")
    app.run(host="0.0.0.0", port=5000)

    
