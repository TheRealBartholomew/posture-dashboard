import serial
import json
import requests
import time

SERIAL_PORT = "/dev/cu.usbmodem101"
BAUD_RATE = 9600
API_URL = "http://127.0.0.1:5000/api/posture"
USER_ID = 1

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print(f"[INFO] Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
    except serial.SerialException as e:
        print(f"[ERROR] Could not open serial port {SERIAL_PORT}: {e}")
        return
    
    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                print(f"[WARNING] Bad JSON: {line}")
                continue
            
            payload = {
                "user_id": USER_ID,
                "angle": data.get("angle"),
            }

            if payload["angle"] is None:
                print(f"[WARNING] Missing angle in data: {data}")
                continue

            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                print(f"[OK] Successfully sent data: {payload}")
            else:
                print(f"[ERROR] Failed to send data: {response.status_code} - {response.text}")

            print(f"[INFO] Transmitted data: {payload}")

        except Exception as e:
            print(f"[ERROR] An unexpected error occurred: {e}")
            time.sleep(1)  # Wait before retrying

if __name__ == "__main__":
    main()
