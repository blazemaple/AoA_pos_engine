import paho.mqtt.client as mqtt
import json
import csv
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# === 旋轉函式 ===
def rotate_vector(vector, x_deg, y_deg, z_deg):
    x_rad, y_rad, z_rad = np.radians([x_deg, y_deg, z_deg])
    Rx = np.array([[1, 0, 0], [0, np.cos(x_rad), -np.sin(x_rad)], [0, np.sin(x_rad), np.cos(x_rad)]])
    Ry = np.array([[np.cos(y_rad), 0, np.sin(y_rad)], [0, 1, 0], [-np.sin(y_rad), 0, np.cos(y_rad)]])
    Rz = np.array([[np.cos(z_rad), -np.sin(z_rad), 0], [np.sin(z_rad), np.cos(z_rad), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx @ vector

# === AoA + 位置計算 ===
def compute_position_from_az_el_height(azimuth_deg, elevation_deg, base_position, orientation_xyz, tag_height):
    az_rad, el_rad = np.radians([azimuth_deg, elevation_deg])
    direction = np.array([np.cos(el_rad)*np.cos(az_rad), np.cos(el_rad)*np.sin(az_rad), np.sin(el_rad)])
    world_vector = rotate_vector(direction, *orientation_xyz)
    height_diff = tag_height - base_position[2]
    if abs(world_vector[2]) < 1e-6:
        return None
    scale = height_diff / world_vector[2]
    tag_position = np.array(base_position) + scale * world_vector
    horizontal_distance = np.linalg.norm((tag_position - base_position)[:2])
    return tag_position, horizontal_distance

def angle_diff_deg(a1, a2):
    """計算循環角度的差異（處理 -180°~180°）"""
    delta = (a2 - a1 + 180) % 360 - 180
    return abs(delta)

def handle_azimuth_filter(tag_id, azimuth):
    global last_azimuths, azimuth_ready

    # 如果是第一筆：先記下但不判斷跳動
    if tag_id not in last_azimuths:
        last_azimuths[tag_id] = azimuth
        azimuth_ready[tag_id] = False
        print(f"✅ {tag_id} 第一筆 azimuth 接收：{azimuth:.2f}°（暫不檢查跳動）")
        return False  # 不濾掉

    # 如果是第二筆起才判斷跳動
    delta = angle_diff_deg(last_azimuths[tag_id], azimuth)
    if not azimuth_ready[tag_id]:
        if delta < MAX_AZIMUTH_JUMP:
            azimuth_ready[tag_id] = True
            last_azimuths[tag_id] = azimuth
            print(f"✅ {tag_id} azimuth 穩定：Δ={delta:.1f}°，正式開始檢查")
            return False
        else:
            print(f"⚠️ {tag_id} 初始 azimuth 跳動過大（Δ={delta:.1f}°），忽略此筆")
            return True  # 濾掉這筆，但不更新 last_azimuth
    else:
        if delta > MAX_AZIMUTH_JUMP:
            print(f"⚠️ {tag_id} azimuth 突變（Δ={delta:.1f}°），忽略此筆")
            return True
        last_azimuths[tag_id] = azimuth
        return False

# === 基地台參數 ===
BASE_POSITION = [0.0, 0.0, 1.4]     # 基地台位置 (X, Y, Z) 公尺
TAG_HEIGHT = 0.0                    # 標籤高度 (Z) 相對於基地台的高度   
ORIENTATION = (90.0, 0.0, 180.0)    # 基地台朝向 (X, Y, Z) 旋轉角度 

# === 繪圖初始化 ===
plt.ion()
fig, ax = plt.subplots()
ax.set_title("Tag 2D Position (Live)")
ax.set_xlabel("X (meters)")
ax.set_ylabel("Y (meters)")
ax.grid(True)
ax.set_aspect('equal')
# 固定視窗範圍
ax.set_xlim(-8, 10)
ax.set_ylim(-3, 15)
# 固定每格 1 單位
ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
# 畫出基地台
ax.plot(BASE_POSITION[0], BASE_POSITION[1], 'bo', label='Base Station')
ax.text(BASE_POSITION[0]+0.2, BASE_POSITION[1]+0.2, "Base", color='blue')

# 初始化軌跡線物件
# 軌跡線（藍線）
line, = ax.plot([], [], 'b-', label='Path')   # 軌跡線 blue
# 當前點（紅點）
point, = ax.plot([], [], 'ro', label='Current Tag')  # 最新紅點
ax.legend()
positions = []

# === 檔案與濾波參數 ===
CSV_FILE = "aoa_mqtt_log.csv"
MAX_STDEV = 10.0  # elevation or azimuth 標準差容忍度
last_azimuths = {}
azimuth_ready = {}  # 是否已經確認該 tag 的 azimuth 是穩定的
MAX_AZIMUTH_JUMP = 30  # azimuth 跳動容忍度

# === MQTT 參數設定 ===
BROKER = "192.168.1.10"  # 替換為你的 MQTT Broker 地址
PORT = 1883  # MQTT 端口
TOPIC = "silabs/aoa/angle/ble-pd-0CAE5F9301A8/+"    # ble-pd-1C34F16339B6

# === MQTT 連線成功時 ===
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe(TOPIC)

# === MQTT 接收資料時 ===
def on_message(client, userdata, msg):
    global last_azimuth
    global positions
    try:
        tag_id = msg.topic.split("/")[-1]
        data = json.loads(msg.payload.decode('utf-8'))
        az = data.get("azimuth")
        el = data.get("elevation")
        az_std = data.get("azimuth_stdev", 0)
        el_std = data.get("elevation_stdev", 0)

        # 多 tag 判斷 azimuth 跳動
        if handle_azimuth_filter(tag_id, az):
            return  # 若為異常值就直接丟掉

        result = compute_position_from_az_el_height(az, el, BASE_POSITION, ORIENTATION, TAG_HEIGHT)
        if result is None:
            print("Direction too flat, skipped.")
            return

        tag_pos, distance_xy = result
        print(f"{msg.topic.split('/')[-1]} Tag @ X={tag_pos[0]:.2f}, Y={tag_pos[1]:.2f}, Z={tag_pos[2]:.2f} | Dist XY = {distance_xy:.2f}m")

        # === 繪圖資料更新 ===
        tag_positions = {topic: pos for topic, pos in positions}  # 使用字典儲存每個TAG的最新位置
        tag_positions[msg.topic] = tag_pos[:2]  # 更新當前TAG的位置
        positions = list(tag_positions.items())  # 將字典轉回列表

        # 清除舊的文字標籤
        for text in ax.texts:
            text.remove()

        # 更新所有點
        xs, ys = [], []
        for topic, (x, y) in positions:
            xs.append(x)
            ys.append(y)
            ax.text(x + 0.2, y + 0.2, topic.split('/')[-1], color='red', fontsize=8)  # 顯示每個點的Topic名稱
        point.set_data(xs, ys)  # 更新所有點的位置
        plt.draw()
        plt.pause(0.01)

        # === 寫入 CSV ===
        # write_header = not os.path.exists(CSV_FILE)
        # with open(CSV_FILE, mode='a', newline='') as file:
        #     writer = csv.writer(file)
        #     if write_header:
        #         writer.writerow(["azimuth", "elevation", "x", "y", "z", "horizontal_distance"])
        #         writer.writerow([
        #             round(az, 2),
        #             round(el, 2),
        #             round(tag_pos[0], 2),
        #             round(tag_pos[1], 2),
        #             round(tag_pos[2], 2),
        #             round(distance_xy, 2)
        #         ])

    except Exception as e:
        print("Error:", e)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\nProgram interrupted. Exiting...")
    client.disconnect()
