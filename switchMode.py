import sys
import json
import paho.mqtt.client as mqtt

# === MQTT 參數設定 ===
BROKER = "192.168.1.10"  # 替換為你的 MQTT Broker 地址
PORT = 1883  # MQTT 端口
TOPIC = "silabs/aoa/config/ble-pd-0CAE5F9301A8"

def main():
    if len(sys.argv) != 2:
        print("用法: python switchMode.py <json檔案名稱>")
        sys.exit(1)
    json_file = sys.argv[1]
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"讀取 JSON 檔案失敗: {e}")
        sys.exit(1)

    client = mqtt.Client()
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        payload = json.dumps(data)
        client.publish(TOPIC, payload)
        print(f"已發佈 {json_file} 內容到 {TOPIC}")
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        print(f"MQTT 發佈失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
