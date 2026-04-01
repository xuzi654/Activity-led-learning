import paho.mqtt.client as mqtt
import time
import random

client = mqtt.Client()

client.connect("test.mosquitto.org", 1883, 60) 

print("传感器已启动，开始发送数据...")

try:
    while True:
        # 强制大部分数据都在 30 以下，用来触发“开启水泵”的截图
        humidity = random.randint(10, 35)
        
        # 2. 统一暗号：改成和 automation_v3.py 一模一样的频道
        client.publish("home/sensor/humi", str(humidity))
        
        print(f"发送数据: 湿度 {humidity}%")
        
        time.sleep(2) # 每 2 秒发一次
except KeyboardInterrupt:
    print("\n传感器停止工作。")
    client.disconnect()