from flask import Flask, render_template, request, jsonify, send_file
import qrcode
import secrets
import os
import csv
from datetime import datetime
from PIL import Image
import threading
import time

app = Flask(__name__)

LIVE_BASE_URL = "https://qr-attendance-system-yqfz.onrender.com"

QR_FOLDER = "static"
QR_IMAGE_PATH = os.path.join(QR_FOLDER, "qr.png")
STUDENT_FILE = "students.csv"

current_mode = {"type": "attendance", "token": ""}


def generate_qr(token):
    full_url = f"{LIVE_BASE_URL}/scan_form?token={token}"
    img = qrcode.make(full_url)
    img.save(QR_IMAGE_PATH)


def update_qr_loop():
    while True:
        if current_mode["type"] == "attendance":
            token = secrets.token_hex(4)
            current_mode["token"] = token
            generate_qr(token)
        time.sleep(2)  # Change every 2 seconds


def load_students():
    students = {}
    if os.path.exists(STUDENT_FILE):
        with open(STUDENT_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                students[row['roll']] = row['name']
    return students


def save_student(name, roll):
    exists = os.path.exists(STUDENT_FILE)
    with open(STUDENT_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'roll'])
        if not exists:
            writer.writeheader()
        writer.writerow({'name': name, 'roll': roll})


def log_attendance(name, roll):
    with open('attendance_log.csv', mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([name, roll, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])


@app.route('/')
def home():
    current_mode["type"] = "attendance"
    return render_template('index.html')


@app.route('/qr_image')
def qr_image():
    return send_file(QR_IMAGE_PATH, mimetype='image/png')


@app.route('/current_qr_token')
def current_qr_token():
    return jsonify({"token": current_mode["token"]})


@app.route('/generate_register_qr')
def generate_register_qr():
    token = secrets.token_hex(4)
    current_mode["type"] = "register"
    current_mode["token"] = token
    generate_qr(token)
    return render_template('index.html')


@app.route('/scan_form')
def scan_form():
    token = request.args.get('token')
    if token != current_mode['token']:
        return "Invalid or expired QR code."
    if current_mode['type'] == "register":
        return render_template('register.html', token=token)
    elif current_mode['type'] == "attendance":
        return render_template('scan.html', token=token)
    return "Unknown operation."


@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    roll = request.form['roll']
    token = request.form['token']
    if token != current_mode['token']:
        return "Invalid registration token."
    students = load_students()
    if roll not in students:
        save_student(name, roll)
        return "Registration successful."
    return "Student already exists."


@app.route('/scan', methods=['POST'])
def scan():
    token = request.form['token']
    roll = request.form['roll']
    students = load_students()
    if token != current_mode['token']:
        return jsonify({"success": False, "msg": "Invalid or expired QR token."})
    name = students.get(roll)
    if name:
        log_attendance(name, roll)
        return jsonify({"success": True, "name": name, "roll": roll})
    return jsonify({"success": False, "msg": "Roll number not found."})


if __name__ == '__main__':
    if not os.path.exists(QR_FOLDER):
        os.makedirs(QR_FOLDER)

    # Start QR auto-update in background
    threading.Thread(target=update_qr_loop, daemon=True).start()

    app.run(debug=True)
