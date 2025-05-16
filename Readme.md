# 使用說明

## 介紹

1. `switchMode.py` 是一個用於將本地 JSON 檔案內容發佈（publish）到指定 MQTT broker/topic 的 Python 工具。適合用於切換或下發 AoA（Angle of Arrival）相關設定。
2. `stream_calc_pos.py` 用於即時繪製標籤地圖。

## 需求
- Python 3.x
- paho-mqtt
- numpy
- matplotlib

安裝需求：
```
pip install -r requirements.txt
```

## 參數設定
- MQTT Broker: `192.168.1.10`
- Port: `1883`
- Topic: `silabs/aoa/config/ble-pd-0CAE5F9301A8/+`

## 基地台參數
`stream_calc_pos.py` 的 64 行至 66 行
```
BASE_POSITION = [0.0, 0.0, 1.4]     # 基地台位置 (X, Y, Z)
ORIENTATION = (90.0, 0.0, 180.0)    # 基地台朝向 (X, Y, Z) 旋轉角度
TAG_HEIGHT = 0.0                    # 標籤高度 (Z) 相對於基地台的高度
```

## 使用方法

1. 準備好要發佈的 JSON 檔案（如 `connless_mode.json` 或 `silabs_mode.json`）。
2. 執行指令：
   ```
   python stream_calc_pos.py
   ```
   ```
   python switchMode.py <json檔案名稱>
   ```
   例如：
   ```
   python switchMode.py connless_mode.json
   ```

## 檔案說明
- `switchMode.py`：主程式，負責讀取 JSON 並發佈到 MQTT。
- `stream_calc_pos.py`：即時接收 MQTT AoA 資料，計算並即時繪製標籤（Tag）於 2D 平面座標，適合用於定位與軌跡追蹤。
- `connless_mode.json`、`silabs_mode.json`：範例設定檔。
- `requirements.txt`：Python 套件需求清單。

## 注意事項
- 請確認 MQTT broker 位址與 topic 設定正確。
- JSON 檔案需為合法格式。

---
如有問題歡迎聯絡開發者。
