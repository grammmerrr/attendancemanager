from flask import Flask, request, jsonify
import psycopg2
import threading
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env

DATABASE_URL = os.getenv("DATABASE_URL")

app = Flask(__name__)

# ✅ PostgreSQL Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")  # Ensure this is set in Render's environment variables

def connect_db():
    """Connect to PostgreSQL database."""
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    """Initialize the database with required tables."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            command TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return "✅ Slack Attendance Manager is Running!"

@app.route("/slack/command", methods=["POST"])
def slack_command():
    """Handles Slack commands and prevents timeout using an instant response."""
    try:
        data = request.form
        command = data.get("command")
        user_id = data.get("user_id")
        user_name = data.get("user_name")
        response_url = data.get("response_url")  # Slack response URL for async updates

        if not all([command, user_id, user_name, response_url]):
            return jsonify({"text": "❌ Missing required data."}), 400

        print(f"🔄 Received: {command} from {user_name} (ID: {user_id})")

        # ✅ Respond instantly to Slack
        response = {"text": f"✅ {command} received for {user_name}, processing..."}
        threading.Thread(target=process_command, args=(command, user_id, user_name, response_url), daemon=True).start()

        return jsonify(response), 200
    except Exception as e:
        print(f"❌ Error in /slack/command: {e}")
        return jsonify({"text": "❌ Internal server error"}), 500

def process_command(command, user_id, user_name, response_url):
    """Processes Slack commands in the background and logs them to PostgreSQL."""
    try:
        print(f"🔄 Processing: {command} for {user_name}")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs (user_id, user_name, command, timestamp) VALUES (%s, %s, %s, %s)",
            (user_id, user_name, command, timestamp)
        )
        conn.commit()
        conn.close()

        print(f"✅ Saved: {user_name} - {command} at {timestamp}")

        if command == "/mylog":
            fetch_user_log(user_id, response_url)

        elif command == "/mylogs":
            fetch_user_logs(user_id, response_url)

        elif command == "/alllogs":
            fetch_all_logs(response_url)

        elif command in ["/checkin", "/checkout", "/breakstart", "/breakend"]:
            message = f"✅ {user_name}, {command.replace('/', '').capitalize()} recorded at {timestamp}."
            requests.post(response_url, json={"text": message})

    except Exception as e:
        print(f"❌ Error processing {command}: {e}")
        requests.post(response_url, json={"text": f"❌ Error processing command: {str(e)}"})

def fetch_user_log(user_id, response_url):
    """Fetch today's attendance log for the user."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT command, timestamp FROM logs WHERE user_id = %s AND DATE(timestamp) = CURRENT_DATE ORDER BY timestamp DESC",
            (user_id,)
        )
        logs = cursor.fetchall()
        conn.close()

        if logs:
            log_messages = [f"{cmd} at {time}" for cmd, time in logs]
            message = "📜 Your log for today:\n" + "\n".join(log_messages)
        else:
            message = "📜 No logs found for today."

        requests.post(response_url, json={"text": message})
    except Exception as e:
        requests.post(response_url, json={"text": f"❌ Error fetching logs: {str(e)}"})

def fetch_user_logs(user_id, response_url):
    """Fetch full attendance history for the user."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT command, timestamp FROM logs WHERE user_id = %s ORDER BY timestamp DESC",
            (user_id,)
        )
        logs = cursor.fetchall()
        conn.close()

        if logs:
            log_messages = [f"{cmd} at {time}" for cmd, time in logs]
            message = "📜 Your attendance history:\n" + "\n".join(log_messages)
        else:
            message = "📜 No logs found."

        requests.post(response_url, json={"text": message})
    except Exception as e:
        requests.post(response_url, json={"text": f"❌ Error fetching logs: {str(e)}"})

def fetch_all_logs(response_url):
    """Fetch all logs (Admin only)."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_name, command, timestamp FROM logs ORDER BY timestamp DESC")
        logs = cursor.fetchall()
        conn.close()

        if logs:
            log_messages = [f"{user} - {cmd} at {time}" for user, cmd, time in logs]
            message = "📜 All logs:\n" + "\n".join(log_messages)
        else:
            message = "📜 No logs found in the database."

        requests.post(response_url, json={"text": message})
    except Exception as e:
        requests.post(response_url, json={"text": f"❌ Error fetching all logs: {str(e)}"})

if __name__ == "__main__":
    print("🚀 Starting Flask Server...")
    app.run(host="0.0.0.0", port=5000)
 
