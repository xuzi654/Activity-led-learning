import paho.mqtt.client as mqtt
import requests
import json
import time
from datetime import datetime
import csv

# ================= 核心配置区 =================
# MQTT Broker 配置
BROKER = "test.mosquitto.org" 
PORT = 1883

# 主题配置
TOPIC_HUMIDITY = "home/sensor/humi" 
TOPIC_CMD = "home/control/water_pump" 

#  API 配置 
SENIVERSE_API_KEY = "----"
LOCATION = "hainan" 

# 日志文件配置
LOG_FILE = "smart_irrigation_log.csv"

# ================= 状态变量初始化 =================
dry_count = 0
wet_count = 0
irrigating = False # 记录当前是否正在灌溉

# ================= 辅助函数 =================

def log_to_csv(action, humidity, rain_status, state):
    """将每次的决策记录持久化到 CSV 文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, mode='x', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Action", "Humidity(%)", "Will Rain", "Pump State"])
    except FileExistsError:
        pass 
        
    with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, action, humidity, rain_status, state])

def check_will_rain():
    """接入心知天气 API 获取今日天气预报"""
    try:
        url = f"https://api.seniverse.com/v3/weather/daily.json?key={SENIVERSE_API_KEY}&location={LOCATION}&language=zh-Hans&unit=c&start=0&days=1"
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return False
            
        data = response.json()
        today_weather = data['results'][0]['daily'][0]
        text_day = today_weather['text_day']
        text_night = today_weather['text_night']
        
        print(f"☁️ 心知预报: [{LOCATION}] 今日白天[{text_day}]，夜间[{text_night}]")
        
        return "雨" in text_day or "雨" in text_night
            
    except Exception as e:
        print(f"⚠️ 天气 API 调用失败: {e}")
        return False

# ================= 核心 MQTT 消息处理 =================

def on_connect(client, userdata, flags, rc):
    print(f"✅ 智能大脑已连接到 Broker (状态码: {rc})")
    client.subscribe(TOPIC_HUMIDITY)
    print(f"📡 正在监听土壤湿度数据: {TOPIC_HUMIDITY}")

def on_message(client, userdata, msg):
    global dry_count, wet_count, irrigating
    
    try:
        current_humidity = float(msg.payload.decode())
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 💧 收到实地土壤湿度: {current_humidity}%")
        
        # 1. 计数防抖
        if current_humidity < 40:
            dry_count += 1
            wet_count = 0
        elif current_humidity > 60:
            wet_count += 1
            dry_count = 0
        else:
            dry_count = 0
            wet_count = 0
            
        # 2. 启动决策 (直接开)
        if dry_count >= 3 and not irrigating:
            print("🚨 连续3次确认干燥，检查天气...")
            
            will_rain = check_will_rain()
            
            if will_rain and current_humidity > 20.0:
                print("🛑 决策拦截：今日有雨，暂不开启水泵。")
                log_to_csv("Hold", current_humidity, "Yes", "OFF")
                dry_count = 0 
            else:
                print("🟢 决策执行：启动水泵！发送指令: START")
                client.publish(TOPIC_CMD, "START")
                irrigating = True
                dry_count = 0
                log_to_csv("START", current_humidity, "No/Emergency", "ON")
                
        # 3. 停止决策 (直接关)
        elif wet_count >= 3 and irrigating:
            print("✅ 连续3次确认湿度达标，准备关闭灌溉...")
            print("🔴 决策执行：停止水泵！发送指令: STOP")
            
            client.publish(TOPIC_CMD, "STOP")
            irrigating = False
            wet_count = 0
            log_to_csv("STOP", current_humidity, "N/A", "OFF")
            
    except ValueError:
        pass 

# ================= 启动程序 =================

if __name__ == "__main__":
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    print("🧠 智能农业大脑 V3 (精简开关版) 正在启动...")
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except Exception as e:
        print(f"❌ 运行错误: {e}")