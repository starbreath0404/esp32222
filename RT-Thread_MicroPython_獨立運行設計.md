# 雙手手勢翻譯手套：MicroPython 獨立運行設計

## 1. 名稱釐清

本專題使用 VS Code 的「RT-Thread MicroPython」擴充套件連接開發板、開啟 REPL 並同步 `.py` 檔案。這個名稱不代表 ESP32-S3 會執行 RT-Thread 作業系統。

兩塊 ESP32-S3-N16R8 實際燒錄標準 ESP32-S3 MicroPython 韌體。該韌體建立於 ESP-IDF／FreeRTOS，因此報告應寫成：

> 使用 MicroPython 開發 ESP32-S3 雙手手勢翻譯系統，並以 VS Code 的 RT-Thread MicroPython 擴充套件進行程式同步與除錯。

## 2. 燒錄後先驗證

左右手燒錄相同的 ESP32-S3 N16R8 MicroPython 韌體，再同步不同的 Python 專案。韌體必須支援 16MB Flash、8MB PSRAM、`espnow`、`machine.I2S` 及裝置檔案系統。

兩塊板都先在 REPL 執行：

```python
import gc, os, sys
import network, espnow
from machine import ADC, I2C, I2S, Pin

print(sys.implementation)
print(os.uname())
print("free heap:", gc.mem_free())

sta = network.WLAN(network.STA_IF)
sta.active(True)
radio = espnow.ESPNow()
radio.active(True)

print("ESP-NOW OK")
print("max packet:", getattr(espnow, "MAX_DATA_LEN", 250))
print("I2S:", I2S)
```

只有左右手都能正常 `import espnow`，才繼續開發雙手通訊。不同韌體包含的模組可能不同，不能只看韌體名稱推定功能。

## 3. 整體架構

```text
左手 ESP32-S3
  ├─ 5× Flex + CD74HC4067
  ├─ GY-91／MPU9250
  ├─ 產生 14 維資料
  └─ ESP-NOW 傳送
              ↓
右手 ESP32-S3
  ├─ 5× Flex + CD74HC4067
  ├─ GY-91／MPU9250
  ├─ 同步成 28 維時間序列
  ├─ 電腦控制錄製與標記
  ├─ Flash 儲存範本與 WAV
  ├─ DTW 手勢辨識
  └─ I2S → MAX98357A → 喇叭
```

左手只負責採集與傳送；右手負責錄製、儲存、辨識及發聲。

## 4. VS Code 專案結構

```text
GestureGlove/
├─ shared/
│  ├─ config.py
│  ├─ packet.py
│  ├─ flex.py
│  └─ mpu9250.py
├─ left_glove/
│  ├─ boot.py
│  ├─ main.py
│  ├─ sensor_reader.py
│  └─ espnow_sender.py
├─ right_glove/
│  ├─ boot.py
│  ├─ main.py
│  ├─ sensor_reader.py
│  ├─ espnow_receiver.py
│  ├─ synchronizer.py
│  ├─ serial_control.py
│  ├─ recorder.py
│  ├─ storage.py
│  ├─ dtw.py
│  ├─ motion_detector.py
│  └─ audio.py
└─ desktop/
   ├─ app.py
   ├─ serial_client.py
   ├─ template_manager.py
   └─ audio_converter.py
```

部署方式：左手 COM 埠同步 `shared + left_glove`；右手 COM 埠同步 `shared + right_glove`。同步後，每塊板根目錄都要有自己的 `boot.py` 和 `main.py`。

## 5. 感測資料與封包

每隻手每幀有 14 個特徵：

```text
Flex0～Flex4,
Ax, Ay, Az,
Gx, Gy, Gz,
Mx, My, Mz
```

左右手同步後為 28 維／幀。建議 50 Hz 取樣，單次手勢最長 3 秒，共 150 幀。

左手封包包含協定版本、序號、時間戳、14 維資料與 CRC。為相容 ESP-NOW V1 的 250-byte 上限，使用 `struct.pack()`，不傳 JSON 浮點文字：

```python
import struct

PACKET_FORMAT = "<BII14fH"

def encode_packet(version, sequence, timestamp_ms, features, crc):
    if len(features) != 14:
        raise ValueError("frame must contain 14 features")
    return struct.pack(PACKET_FORMAT, version, sequence,
                       timestamp_ms, *features, crc)
```

## 6. 不寫死感測數據

所有校正值都由實際量測產生，保存在 `/config/calibration.json`。程式不可使用固定 ADC 數字代表手勢。

Flex Sensor 校正成 0～100：

```python
def normalize_flex(raw, straight, bent):
    span = bent - straight
    if abs(span) < 50:
        raise ValueError("Flex calibration range is too small")
    value = (raw - straight) * 100.0 / span
    return max(0.0, min(100.0, value))
```

MPU9250 另外校正陀螺儀零點、磁力計偏移及比例。喇叭磁鐵會干擾磁力計，所以錄製與實際辨識時，GY-91 和喇叭的位置必須一致。

## 7. ESP-NOW 通訊

```python
import network, espnow

sta = network.WLAN(network.STA_IF)
sta.active(True)
radio = espnow.ESPNow()
radio.active(True)
radio.add_peer(RIGHT_HAND_MAC)
```

配對後將左右手 MAC 保存於 `/config/device.json`，不要散落在多個程式檔內。

右手不要在 ESP-NOW 回呼內執行 DTW、寫 Flash 或播放音訊。回呼只接收封包並放入固定大小緩衝區，主迴圈或 `uasyncio` 工作再處理。官方文件提醒 ESP-NOW、I2S、Timer 等同時大量使用排程器時可能漏掉回呼，因此第一版應避免註冊過多 IRQ 回呼。

## 8. 電腦控制錄製

錄製不使用實體按鈕：

```text
右手 USB 連接電腦
→ 按「開始錄製」
→ 做出手勢
→ 按「停止錄製」
→ 輸入意思
→ 選擇／產生 WAV
→ 儲存至右手 Flash
```

USB 控制採用一行一筆 UTF-8 JSON：

```json
{"command":"status"}
{"command":"start_record","max_ms":3000}
{"command":"stop_record"}
{"command":"save","label":"使用者輸入的文字"}
{"command":"cancel"}
{"command":"list"}
```

ESP32 回覆：

```json
{"event":"ready","protocol":1}
{"event":"recording"}
{"event":"recorded","frames":108,"dropped":0}
{"event":"saved","gesture_id":7}
{"event":"error","code":"LEFT_HAND_TIMEOUT"}
```

WAV 不放進 JSON，改用包含檔案長度與 CRC32 的二進位傳輸。電腦只有收到 `saved` 才顯示成功。

## 9. MicroPython 錄製器

```python
import gc, time

class GestureRecorder:
    IDLE, RECORDING, RECORDED = range(3)

    def __init__(self, sample_rate=50, max_ms=3000):
        self.sample_rate = sample_rate
        self.max_ms = max_ms
        self.state = self.IDLE
        self.frames = []

    def start(self):
        if self.state == self.RECORDING:
            raise RuntimeError("already recording")
        gc.collect()
        self.frames = []
        self.started_at = time.ticks_ms()
        self.next_sample_at = self.started_at
        self.state = self.RECORDING

    def poll(self, read_synced_frame):
        if self.state != self.RECORDING:
            return
        now = time.ticks_ms()
        if time.ticks_diff(now, self.started_at) >= self.max_ms:
            self.stop()
            return
        if time.ticks_diff(now, self.next_sample_at) < 0:
            return

        frame = read_synced_frame()
        if frame is not None:
            if len(frame) != 28:
                raise ValueError("frame must contain 28 features")
            self.frames.append(frame)
        self.next_sample_at = time.ticks_add(
            self.next_sample_at, 1000 // self.sample_rate)

    def stop(self):
        if self.state != self.RECORDING:
            raise RuntimeError("not recording")
        if len(self.frames) < self.sample_rate // 2:
            self.cancel()
            raise ValueError("recording is too short")
        self.state = self.RECORDED

    def cancel(self):
        self.frames = []
        self.state = self.IDLE
        gc.collect()
```

`read_synced_frame` 必須由真實感測資料提供，不能回傳模擬或固定數字。

## 10. Flash 儲存

```text
/config/calibration.json
/config/device.json
/gestures/index.json
/gestures/0001/sample_01.bin
/gestures/0001/sample_02.bin
/gestures/0001/audio.wav
```

範本使用 `float32` 或量化 `int16` 二進位格式，不使用大型 JSON 浮點陣列。檔案包含版本、幀數、特徵數及 CRC；先寫暫存檔，驗證後再重新命名，降低斷電損壞風險。

標籤、門檻與內容均由錄製流程產生，不寫死在 `main.py`。

## 11. ±20 與 DTW

Flex 的 ±20 只適用於校正後的 0～100 彎曲百分比，不能直接套用到 IMU。

1. Flex 正規化至 0～100。
2. IMU 各軸依訓練統計值正規化。
3. DTW 比較不同長度的 28 維時間序列。
4. Flex 關鍵幀相差超過 20 時增加懲罰。
5. 最小距離仍須低於門檻才接受。
6. 未通過門檻時判定未知，不播放語音。

門檻由同標籤的多筆範本估計：

```text
門檻 = 同類範本平均距離 + 2 × 標準差
```

MicroPython DTW 使用兩列滾動矩陣，不建立完整 `150 × 150` Python 二維陣列。先測試 5 個手勢、每個 5 筆範本；若速度不足，再將 DTW 編譯成原生 `.mpy`／C 模組。

## 12. 離線辨識與語音

離線時右手持續保留最近三秒資料。Flex 變化或陀螺儀能量超過動態門檻即開始動作，連續靜止 300 ms 即結束並執行 DTW。播放後進入冷卻狀態，防止重複發聲。

中文 TTS 在電腦端完成，再上傳 WAV。建議格式為單聲道、16-bit PCM、16000 Hz。右手辨識成功後使用 `machine.I2S` 將 WAV 送至 MAX98357A。`machine.I2S` 目前仍屬 Technical Preview，燒錄後必須實測韌體是否提供。

## 13. 獨立運行

```text
開機
→ boot.py 初始化硬體
→ main.py 載入校正、範本與 WAV
→ 左手傳送 14 維資料
→ 右手同步成 28 維
→ 自動擷取動作並執行 DTW
→ 通過門檻：播放對應 WAV
→ 未通過門檻：保持安靜
```

電腦只負責燒錄、同步程式、校正、錄製、標記與上傳 WAV。完成設定後拔除 USB，左右手改由電池供電，仍可獨立辨識與發聲。

## 14. 開發順序

1. 兩塊板燒錄相同 ESP32-S3 N16R8 MicroPython 韌體。
2. 使用 VS Code RT-Thread MicroPython 連接兩個 COM 埠。
3. 確認 PSRAM、`espnow`、`machine.I2S` 與檔案系統。
4. 取得左右手 STA MAC Address。
5. 先完成 ESP-NOW 傳送 `hello`。
6. 改為序號、時間戳與 14 維二進位封包。
7. 完成 GY-91／MPU9250。
8. 完成 CD74HC4067、5 支 Flex 與校正。
9. 完成右手 28 維同步與 USB 輸出。
10. 完成電腦錄製控制與 Flash 儲存。
11. 完成 DTW、未知動作拒絕及冷卻。
12. 完成 WAV 上傳與 MAX98357A 播放。

## 15. 驗收標準

- 兩塊板使用相同版本 MicroPython 並可由 VS Code 連接。
- `import espnow` 與 `machine.I2S` 成功。
- 左手能以 50 Hz 傳資料，右手能檢查掉包。
- 電腦可控制開始、停止、取消、標記與儲存。
- 手勢範本不是原始碼中的固定數值。
- 重新開機後範本與 WAV 仍存在。
- 拔除 USB 後可由電池獨立辨識及發聲。
- 未知動作不會被強制翻譯成已知手勢。
- 感測器或左手離線時停止辨識並回報錯誤。

