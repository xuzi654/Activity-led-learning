import cv2
import numpy as np
import RPi.GPIO as GPIO
import time
import paho.mqtt.client as mqtt
import ssl

# GPIO setup for actuator (pump relay)
PUMP_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(PUMP_PIN, GPIO.OUT)

# MQTT setup with encryption
MQTT_BROKER = "your_broker_address"
MQTT_PORT = 8883  # TLS port
MQTT_TOPIC = "plant/distress"

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")

client = mqtt.Client()
client.on_connect = on_connect
client.tls_set(ca_certs="ca.crt", certfile="client.crt", keyfile="client.key", tls_version=ssl.PROTOCOL_TLS)
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Camera setup
cap = cv2.VideoCapture(0)

def detect_distress(frame):
    # Simple distress detection: check green channel intensity
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([80, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    green_pixels = cv2.countNonZero(mask)
    total_pixels = frame.shape[0] * frame.shape[1]
    green_ratio = green_pixels / total_pixels
    return green_ratio < 0.3  # Threshold for distress

def spray_fertilizer():
    GPIO.output(PUMP_PIN, GPIO.HIGH)
    time.sleep(5)  # Spray for 5 seconds
    GPIO.output(PUMP_PIN, GPIO.LOW)

try:
    while True:
        ret, frame = cap.read()
        if ret:
            distressed = detect_distress(frame)
            if distressed:
                spray_fertilizer()
                client.publish(MQTT_TOPIC, "Distress detected, fertilizer sprayed")
        time.sleep(10)  # Check every 10 seconds
except KeyboardInterrupt:
    pass
finally:
    cap.release()
    GPIO.cleanup()
    client.disconnect()