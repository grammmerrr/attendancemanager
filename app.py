from flask import Flask, request, jsonify
import sqlite3
import threading
import os
from datetime import datetime

app = Flask(__name__)

# ✅ Database setup
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

    # ✅ Instant Slack response to prevent timeout
    response = {"text": f"Processing {command} for {user_name}..."}
    threading.Thread(target=process_command, args=(command, user_id, user_name)).start()
    
    return jsonify(response), 200

def process_command(command, user_id, user_name):
    # ✅ Background task to save command logs
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (user_id, user_name, command, timestamp) VALUES (?, ?, ?, ?)",
                   (user_id, user_name, command, timestamp))
    conn.commit()
    conn.close()
    print(f"✅ Saved: {user_name} - {command} at {timestamp}")

@app.route("/logs", methods=["GET"])
def view_logs():
    # ✅ User can view their own logs
    user_id = request.args.get("user_id")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    logs = cursor.fetchall()
    conn.close()
    
    return jsonify({"logs": logs})

@app.route("/alllogs", methods=["GET"])
def view_all_logs():
    # ✅ Admin can view all logs
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()
    
    return jsonify({"all_logs": logs})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    