from flask import Flask, request, jsonify
import sqlite3
import threading
import requests  # Add this import for sending data to response_url
from datetime import datetime

app = Flask(__name__)

DB_FILE = "attendance.db"

def init_db():
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
    try:
        data = request.form
        command = data.get("command")
        user_id = data.get("user_id")
        user_name = data.get("user_name")
        response_url = data.get("response_url")  # Get the response URL

        if not command or not user_id or not user_name or not response_url:
            return jsonify({"text": "❌ Missing data in request"}), 400

        print(f"🔄 Received: {command} from {user_name}")

        # Pass response_url to the background thread
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
    try:
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
                message = "📜 Your logs"
" + "
".join(log_messages)"
            else:
                message = "No logs found for your account."

            # Send the formatted logs to Slack using the response_url
            requests.post(response_url, json={"text": message})

        # Add handling for other commands if needed
        # elif command == "/othercommand":
        #     ...

    except Exception as e:
        error_message = f"❌ Error processing command: {str(e)}"
        print(error_message)
        requests.post(response_url, json={"text": error_message})

@app.route("/logs", methods=["GET"])
def view_logs():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        logs = cursor.fetchall()
        conn.close()
        return jsonify({"logs": logs})
    except Exception as e:
        print(f"❌ Error fetching logs: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route("/alllogs", methods=["GET"])
def view_all_logs():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC")
        logs = cursor.fetchall()
        conn.close()
        return jsonify({"all_logs": logs})
    except Exception as e:
        print(f"❌ Error fetching all logs: {e}")
        return jsonify({"error": "Database error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

    