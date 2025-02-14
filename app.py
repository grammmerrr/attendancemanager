from flask import Flask, request, jsonify
import sqlite3
import threading
import os
from datetime import datetime

app = Flask(__name__)

# ✅ Database File
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
    
    data = request.form
    command = data.get("command")
    user_id = data.get("user_id")
    user_name = data.get("user_name")

    # ✅ Immediately respond to Slack to prevent timeout
    response = {"text": f"Processing {command} for {user_name}..."}
    threading.Thread(target=process_command, args=(command, user_id, user_name)).start()

    return jsonify(response), 200

def process_command(command, user_id, user_name):
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (user_id, user_name, command, timestamp) VALUES (?, ?, ?, ?)",
                   (user_id, user_name, command, timestamp))
    conn.commit()
    conn.close()
    print(f"✅ Saved: {user_name} - {command} at {timestamp}")

@app.route("/mylogs", methods=["POST"])
def my_logs():
   
    user_id = request.form.get("user_id")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT command, timestamp FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
    logs = cursor.fetchall()
    conn.close()

    if not logs:
        return jsonify({"text": "No logs found!"})

    logs_text = "
".join([f"{log[1]} - {log[0]}" for log in logs])
    return jsonify({"text": f"Your last 10 logs:
{logs_text}"}), 200

@app.route("/alllogs", methods=["POST"])
def all_logs():
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_name, command, timestamp FROM logs ORDER BY timestamp DESC LIMIT 20")
    logs = cursor.fetchall()
    conn.close()

    if not logs:
        return jsonify({"text": "No logs found!"})

    logs_text = "
".join([f"{log[2]} - {log[0]}: {log[1]}" for log in logs])
    return jsonify({"text": f"All logs:
{logs_text}"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
