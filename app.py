from flask import Flask, request, jsonify
import os
import threading
import requests
import psycopg2
from datetime import datetime

app = Flask(__name__)

# Get PostgreSQL connection URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

def init_db():
    """Initialize the PostgreSQL database."""
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
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
    """Handles Slack commands and responds immediately."""
    try:
        data = request.form
        command = data.get("command")
        user_id = data.get("user_id")
        user_name = data.get("user_name")
        response_url = data.get("response_url")

        if not all([command, user_id, user_name, response_url]):
            return jsonify({"text": "❌ Missing data in request"}), 400

        print(f"🔄 Received: {command} from {user_name}")

        # Start background thread
        threading.Thread(
            target=process_command,
            args=(command, user_id, user_name, response_url),
            daemon=True
        ).start()

        return jsonify({"text": f"✅ {command} received, processing..."}), 200
    except Exception as e:
        print(f"❌ Error in /slack/command: {e}")
        return jsonify({"error": "Internal server error"}), 500

def process_command(command, user_id, user_name, response_url):
    """Process commands in the background."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Connect to PostgreSQL
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cursor = conn.cursor()

        # Log the command
        cursor.execute(
            "INSERT INTO logs (user_id, user_name, command, timestamp) VALUES (%s, %s, %s, %s)",
            (user_id, user_name, command, timestamp)
        )
        conn.commit()

        # Handle commands
        if command == "/checkin":
            message = f"✅ {user_name}, you have successfully checked in at {timestamp}."

        elif command == "/checkout":
            # Check if the user has checked in today
            cursor.execute(
                "SELECT command FROM logs WHERE user_id = %s AND command = '/checkin' AND timestamp::date = %s::date",
                (user_id, timestamp)
            )
            if cursor.fetchone():
                message = f"✅ {user_name}, you have successfully checked out at {timestamp}."
            else:
                message = f"❌ {user_name}, you must check in before checking out."

        elif command == "/breakstart":
            # Check if the user has checked in today
            cursor.execute(
                "SELECT command FROM logs WHERE user_id = %s AND command = '/checkin' AND timestamp::date = %s::date",
                (user_id, timestamp)
            )
            if cursor.fetchone():
                message = f"✅ {user_name}, your break has started at {timestamp}."
            else:
                message = f"❌ {user_name}, you must check in before starting a break."

        elif command == "/breakend":
            # Check if the user has started a break today
            cursor.execute(
                "SELECT command FROM logs WHERE user_id = %s AND command = '/breakstart' AND timestamp::date = %s::date",
                (user_id, timestamp)
            )
            if cursor.fetchone():
                message = f"✅ {user_name}, your break has ended at {timestamp}."
            else:
                message = f"❌ {user_name}, you must start a break before ending it."

        elif command == "/mylog":
            # Fetch today's logs for the user
            cursor.execute(
                "SELECT command, timestamp FROM logs WHERE user_id = %s AND timestamp::date = %s::date ORDER BY timestamp",
                (user_id, timestamp)
            )
            logs = cursor.fetchall()
            if logs:
                message = "📜 Today's log:\n" + "\n".join([f"{cmd} at {time}" for cmd, time in logs])
            else:
                message = "No logs found for today."

        elif command == "/mylogs":
            # Fetch all logs for the user
            cursor.execute(
                "SELECT command, timestamp FROM logs WHERE user_id = %s ORDER BY timestamp DESC",
                (user_id,)
            )
            logs = cursor.fetchall()
            if logs:
                message = "📜 Your logs:\n" + "\n".join([f"{cmd} at {time}" for cmd, time in logs])
            else:
                message = "No logs found for your account."

        elif command == "/alllogs":
            # Fetch all logs (admin only)
            cursor.execute("SELECT user_name, command, timestamp FROM logs ORDER BY timestamp DESC")
            logs = cursor.fetchall()
            if logs:
                message = "📜 All logs:\n" + "\n".join([f"{user} - {cmd} at {time}" for user, cmd, time in logs])
            else:
                message = "Database empty."

        else:
            message = "❌ Unrecognized command."

        # Send response to Slack
        requests.post(response_url, json={"text": message})

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error processing {command}: {e}")
        requests.post(response_url, json={"text": f"❌ Error: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    
