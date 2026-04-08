import requests
import json

# ================= 配置 =================
SENIVERSE_API_KEY = "----"  # 请填入你的心知天气 API 密钥
LOCATION = "hainan"  # 地区配置

def check_will_rain():
    """检测今日是否会下雨"""
    try:
        url = f"https://api.seniverse.com/v3/weather/daily.json?key={SENIVERSE_API_KEY}&location={LOCATION}&language=zh-Hans&unit=c&start=0&days=1"
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            print("❌ API 请求失败")
            return False
            
        data = response.json()
        today_weather = data['results'][0]['daily'][0]
        text_day = today_weather['text_day']
        text_night = today_weather['text_night']
        
        print(f"☁️ 心知预报: [{LOCATION}] 今日白天[{text_day}]，夜间[{text_night}]")
        
        will_rain = "雨" in text_day or "雨" in text_night
        print(f"🌧️ 今日是否会下雨: {'是' if will_rain else '否'}")
        return will_rain
            
    except Exception as e:
        print(f"⚠️ 天气 API 调用失败: {e}")
        return False

if __name__ == "__main__":
    print("🌦️ 雨水检测程序启动...")
    check_will_rain()</content>
<parameter name="filePath">c:\Users\20786\Desktop\rain_detector.py