import json
import time
from datetime import datetime

import paho.mqtt.client as mqtt

# ================= 核心配置 =================
BROKER = "test.mosquitto.org"
PORT = 1883

TOPIC_HUMIDITY = "home/sensor/humi"
TOPIC_CAMERA_ROOT = "home/sensor/camera_root"
TOPIC_ALERT = "home/alert/root_waterlogged"
LOG_FILE = "camera_root_assistant_log.csv"

# 根部饱和阈值（可根据实际摄像头分析结果进一步调整）
ROOT_WATERLOGGED_THRESHOLD = 80.0

# ================= 日志与告警 =================

def log_event(event_type: str, details: str) -> None:
    """将监测事件记录到 CSV 日志中。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, mode='x', encoding='utf-8') as f:
            f.write("Timestamp,Event,Details\n")
    except FileExistsError:
        pass

    with open(LOG_FILE, mode='a', encoding='utf-8') as f:
        f.write(f'{timestamp},{event_type},{details}\n')


def send_alert(client: mqtt.Client, reason: str, payload: str) -> None:
    """发送根部水浸告警到 MQTT 主题，并记录日志。"""
    message = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "camera_payload": payload,
    }, ensure_ascii=False)
    client.publish(TOPIC_ALERT, message)
    print(f"🚨 告警已发送: {reason}")
    log_event("ALERT", f"{reason} | payload={payload}")


# ================= 摄像头分析 =================

def parse_camera_payload(raw_payload: bytes) -> dict:
    """解析摄像头发布的根部检测结果。"""
    text = raw_payload.decode(errors='ignore').strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {"raw": text}
    except json.JSONDecodeError:
        return {"raw": text}


def analyze_root_observation(camera_data: dict) -> dict:
    """根据摄像头结果判断根部是否水分过高。"""
    result = {
        "waterlogged": False,
        "reason": None,
        "score": None,
    }

    if "root_moisture" in camera_data:
        try:
            score = float(camera_data["root_moisture"])
            result["score"] = score
            if score >= ROOT_WATERLOGGED_THRESHOLD:
                result["waterlogged"] = True
                result["reason"] = f"根部水分指数 {score} >= {ROOT_WATERLOGGED_THRESHOLD}"
        except (ValueError, TypeError):
            result["reason"] = "root_moisture 数据无法解析"

    elif "status" in camera_data:
        status = str(camera_data["status"]).lower()
        if status in {"waterlogged", "saturated", "overflow", "root saturated"}:
            result["waterlogged"] = True
            result["reason"] = f"根部状态: {camera_data['status']}"

    else:
        result["reason"] = "未检测到可解析的根部水分信息"

    return result


# ================= MQTT 消息回调 =================

def on_connect(client, userdata, flags, rc):
    print(f"✅ 摄像头辅助模块已连接到 Broker (rc={rc})")
    client.subscribe([(TOPIC_HUMIDITY, 0), (TOPIC_CAMERA_ROOT, 0)])
    print(f"📡 订阅主题: {TOPIC_HUMIDITY}, {TOPIC_CAMERA_ROOT}")


def on_message(client, userdata, msg):
    topic = msg.topic
    if topic == TOPIC_HUMIDITY:
        handle_humidity(msg.payload)
    elif topic == TOPIC_CAMERA_ROOT:
        handle_camera_root(msg.payload, client)
    else:
        print(f"⚠️ 未知主题消息: {topic}")


def handle_humidity(payload: bytes) -> None:
    try:
        humidity = float(payload.decode())
        print(f"📥 传感器湿度数据: {humidity}%")
        log_event("HUMIDITY", f"{humidity}")
    except ValueError:
        print("⚠️ 湿度数据解析失败")
        log_event("HUMIDITY_ERROR", payload.decode(errors='ignore'))


def handle_camera_root(payload: bytes, client: mqtt.Client) -> None:
    camera_data = parse_camera_payload(payload)
    analysis = analyze_root_observation(camera_data)

    detail = json.dumps(camera_data, ensure_ascii=False)
    print(f"📷 摄像头根部观测: {detail}")
    if analysis["waterlogged"]:
        send_alert(client, analysis["reason"], detail)
    else:
        status = analysis["reason"] or "未发现根部积水风险"
        print(f"✅ 根部观测正常: {status}")
        log_event("CAMERA_OK", status)


if __name__ == "__main__":
    print("🌲 果树根部摄像头辅助监测程序启动中...")
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except Exception as exc:
        print(f"❌ 连接失败: {exc}")
