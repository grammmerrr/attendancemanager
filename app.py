from flask import Flask, request, jsonify
import sqlite3
import threading
import os
from datetime import datetime

app = Flask(__name__)

# ✅ Database setup
DB_FILE = "attendance.db"

def init_db():
    
    try:
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
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")

init_db()

@app.route("/")
def home():
    return "Slack Attendance Bot is Running! 🚀"

@app.route("/slack/command", methods=["POST"])
def slack_command():
    
    data = request.form
    command = data.get("command")
    user_id = data.get("user_id")
    user_name = data.get("user_name")

    if not command or not user_id or not user_name:
        return jsonify({"text": "❌ Missing data in request"}), 400

    print(f"🔄 Received: {command} from {user_name} (ID: {user_id})")  # ✅ Debug log

    # ✅ Respond immediately to Slack
    response = {"text": f"✅ {command} received for {user_name}, processing..."}
    threading.Thread(target=process_command, args=(command, user_id, user_name)).start()

    return jsonify(response), 200

def process_command(command, user_id, user_name):
    
    try:
        print(f"🔄 Processing: {command} for {user_name}")  # ✅ Debug log
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (user_id, user_name, command, timestamp) VALUES (?, ?, ?, ?)",
                       (user_id, user_name, command, timestamp))
        conn.commit()
        conn.close()

        print(f"✅ Saved: {user_name} - {command} at {timestamp}")  # ✅ Debug log
    except Exception as e:
        print(f"❌ Error processing {command}: {e}")  # ✅ Catch errors

@app.route("/logs", methods=["GET"])
def view_logs():
   
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id parameter"}), 400

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        logs = cursor.fetchall()
        conn.close()

        return jsonify({"logs": logs})
    except Exception as e:
        print(f"❌ Error fetching logs: {e}")
        return jsonify({"error": "Failed to fetch logs"}), 500

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
        return jsonify({"error": "Failed to fetch logs"}), 500

if __name__ == "__main__":
    print("🚀 Starting Flask Server...")
    app.run(host="0.0.0.0", port=5000)

    