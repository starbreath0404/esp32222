# MicroPython 燒入教學：完全零基礎版

這份教學先讓兩塊 ESP32-S3 成功執行 MicroPython，再測試 ESP-NOW。不要一開始就接全部感測器。

## 0. 先認識三個資料夾

以下命令中的「專案資料夾」就是你解壓縮本專案的位置，不限定磁碟代號。換電腦時請先閱讀 `在其他電腦執行_零基礎版.md`。

本機範例位置：

```text
D:\專題
```

重要位置：

```text
D:\專題\micropython\common       共用程式
D:\專題\micropython\left_glove  左手程式
D:\專題\micropython\right_glove 右手程式
D:\專題\micropython\desktop     電腦錄製工具
```

每台電腦都必須在專案資料夾內建立自己的 Python 環境：

```text
.venv
```

第一次使用時雙擊 `01_安裝環境.cmd`，不要從其他電腦複製 `.venv`。

## 1. 幫板子做記號

拿膠帶貼在兩塊 ESP32-S3 上：

- 一塊寫「左手」。
- 一塊寫「右手」。

一次只插一塊板子，避免不知道自己正在燒哪一塊。

## 2. 下載 MicroPython 韌體

1. 打開官方頁面：<https://micropython.org/download/ESP32_GENERIC_S3/>
2. 找到 **Firmware (Support for Octal-SPIRAM)**。
3. 選最新穩定版本，不要選 daily build。
4. 點 `.bin` 下載。
5. 把下載的檔案移到：

```text
D:\專題\firmware
```

6. 為了後面不打錯，把檔名改成：

```text
ESP32S3_MICROPYTHON.bin
```

N16R8 通常代表 16MB Flash 與 8MB Octal PSRAM，所以要選 Octal-SPIRAM 版本。

## 3. 找到 COM 埠

1. 先拔掉 ESP32。
2. 右鍵 Windows 開始按鈕。
3. 開啟「裝置管理員」。
4. 展開「連接埠（COM 和 LPT）」。
5. 插入左手 ESP32。
6. 看哪一個 COM 新出現，例如 `COM5`。
7. 把它記在紙上：`左手 = COM5`。
8. 拔掉左手、插入右手，再記下右手 COM。

如果沒有新 COM：

- 換一條確定可以傳資料的 USB 線。
- 換另一個 Type-C 插孔。
- 不要使用只有充電功能的線。
- 仍沒有時，可能要安裝板子使用的 USB-UART 驅動。

## 4. 在 VS Code 開啟終端機

1. VS Code 開啟 `D:\專題`。
2. 上方選單點「終端機」。
3. 點「新增終端機」。
4. 下方出現 PowerShell。
5. 確認提示文字中有：

```text
PS D:\專題>
```

如果不是，輸入：

```powershell
Set-Location -LiteralPath 'D:\專題'
```

## 5. 擦除左手板子

先只插左手。把下面的 `COM5` 改成你的左手 COM：

```powershell
& '.\.venv\Scripts\python.exe' -m esptool --chip esp32s3 --port COM5 erase-flash
```

成功時會看到類似：

```text
Chip erase completed successfully
```

如果一直顯示 Connecting：

1. 按住板子的 BOOT 按鈕。
2. 按一下 RESET／EN 按鈕。
3. 放開 RESET／EN。
4. 再放開 BOOT。
5. 重新執行燒錄命令。

## 6. 燒錄左手 MicroPython

```powershell
& '.\.venv\Scripts\python.exe' -m esptool --chip esp32s3 --port COM5 --baud 460800 write-flash 0 '.\firmware\ESP32S3_MICROPYTHON.bin'
```

成功時會看到寫入完成及驗證成功。若 460800 失敗，改慢速：

```powershell
& '.\.venv\Scripts\python.exe' -m esptool --chip esp32s3 --port COM5 write-flash 0 '.\firmware\ESP32S3_MICROPYTHON.bin'
```

## 7. 右手重做一次

1. 拔掉左手。
2. 插入右手。
3. 把命令中的 COM 改成右手 COM。
4. 先 `erase-flash`。
5. 再 `write-flash`。

左右手燒的是同一個 `.bin`，之後上傳的 Python 檔案不同。

## 8. 第一次連線測試

以左手 `COM5` 為例：

```powershell
& '.\.venv\Scripts\python.exe' -m mpremote connect COM5 repl
```

看到 `>>>` 後輸入：

```python
print("hello")
```

按 Enter，應看到：

```text
hello
```

離開 REPL：按住 `Ctrl` 再按 `]`。

## 9. 檢查 ESP-NOW、I2S 與檔案系統

上傳檢查程式：

```powershell
& '.\.venv\Scripts\python.exe' -m mpremote connect COM5 run '.\micropython\tools\hardware_check.py'
```

希望看到：

```text
PASS: espnow
PASS: I2S
PASS: filesystem
```

左右手都要測。若出現 `FAIL: espnow`，先停止，不要繼續上傳手套程式；代表韌體不含 ESP-NOW。

## 10. 取得左右手 MAC

左手：

```powershell
& '.\.venv\Scripts\python.exe' -m mpremote connect COM5 run '.\micropython\tools\show_mac.py'
```

會出現類似：

```text
34:85:18:AA:BB:CC
```

抄下來。右手也執行一次，換成右手 COM。

## 11. 把右手 MAC 填入設定

VS Code 開啟：

```text
D:\專題\micropython\common\config.py
```

找到：

```python
LEFT_HAND_MAC = None
RIGHT_HAND_MAC = None
```

改成實際值：

```python
LEFT_HAND_MAC = "34:85:18:11:22:33"
RIGHT_HAND_MAC = "34:85:18:AA:BB:CC"
```

引號、冒號都要保留。範例 MAC 不可直接照抄。

## 12. 先確認 GPIO

目前預設：

```text
CD74HC4067 S0～S3：GPIO 4, 5, 6, 7
CD74HC4067 SIG：GPIO 1
GY-91 SDA：GPIO 8
GY-91 SCL：GPIO 9
MAX98357A BCLK：GPIO 16
MAX98357A LRC：GPIO 17
MAX98357A DIN：GPIO 18
```

先看板子兩側是否真的有這些 GPIO 標示。若沒有，先不要接線，把實際板子正反面照片提供給我，再修改 `config.py`。

## 13. 建立左右手上傳資料夾

在 VS Code 終端機執行：

```powershell
& '.\.venv\Scripts\python.exe' '.\micropython\tools\build_deploy.py'
```

成功會產生：

```text
D:\專題\micropython\dist\left
D:\專題\micropython\dist\right
```

每次修改 `common`、`left_glove` 或 `right_glove` 後，都要重新執行這一步。

## 14. 用 mpremote 上傳左手

先清掉板上的舊 Python 檔，再複製新檔。不要在右手 COM 上執行左手命令。

```powershell
& '.\.venv\Scripts\python.exe' -m mpremote connect COM5 fs cp -r '.\micropython\dist\left\.' :
```

完成後按一下左手 RESET／EN。若感測器尚未接好，出現 `LEFT_FATAL` 是正常的，因為程式找不到 MPU9250 或校正資料。

## 15. 上傳右手

拔掉左手、插入右手，將 `COM6` 改成你的右手 COM：

```powershell
& '.\.venv\Scripts\python.exe' -m mpremote connect COM6 fs cp -r '.\micropython\dist\right\.' :
```

按一下右手 RESET／EN。感測器沒接好時可能顯示 `fatal`，目前先確認檔案能上傳即可。

## 16. 使用 VS Code RT-Thread MicroPython 擴充套件

如果擴充套件已安裝：

1. 按 `Ctrl+Shift+P`。
2. 輸入 `MicroPython`。
3. 選擇連接裝置或設定序列埠的命令。
4. 選左手 COM 時，只同步 `micropython/dist/left`。
5. 選右手 COM 時，只同步 `micropython/dist/right`。

擴充套件各版本的按鈕名稱可能不同，因此 `mpremote` 指令是保底方法。兩種方法擇一，不要同時占用同一個 COM 埠。

## 17. 開啟電腦錄製工具

右手完整啟動後，先關閉所有 REPL 與序列監控，再執行：

```powershell
& '.\.venv\Scripts\python.exe' '.\micropython\desktop\app.py'
```

操作順序：

1. 選右手 COM。
2. 按「連線」。
3. 按「查詢狀態」。
4. 按「開始錄製」。
5. 做手勢。
6. 按「停止錄製」。
7. 輸入意思，例如「你好」。
8. 按「產生中文語音」或選擇 WAV。
9. 按「儲存標記」。
10. 同一個意思至少錄三次，系統才會計算辨識門檻。

## 18. 很重要的限制

- 沒接真實感測器以前，左右手主程式不會正常工作。
- 每個手勢至少錄 3 次，建議 5～10 次。
- 不要讓 VS Code REPL、mpremote REPL 和錄製工具同時連同一個 COM。
- Flex 與 CD74HC4067 必須使用 3.3V 訊號。
- GY-91 要遠離喇叭磁鐵。
- 修改 GPIO 或 MAC 後，要重新執行 `build_deploy.py` 並重新上傳。

## 19. 出錯時要提供什麼

不要只說「不能用」。請提供：

1. 卡在哪一個步驟編號。
2. 左手或右手。
3. 使用的 COM 編號。
4. 終端機完整錯誤文字。
5. 板子與接線清楚照片。

有這五項，才能快速判斷是韌體、COM、GPIO、接線或程式問題。
