import base64
import binascii
import json
from pathlib import Path
import struct
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import wave

import serial
from serial.tools import list_ports

from recording_db import RecordingDatabase


BAUD_RATE = 115200


def convert_wav(source, destination, target_rate=16000):
    """Convert PCM 16-bit WAV to mono 16 kHz with linear interpolation."""
    with wave.open(str(source), "rb") as reader:
        channels = reader.getnchannels()
        width = reader.getsampwidth()
        rate = reader.getframerate()
        frames = reader.readframes(reader.getnframes())
    if width != 2:
        raise ValueError("TTS WAV is not 16-bit PCM")
    samples = list(struct.unpack("<%dh" % (len(frames) // 2), frames))
    if channels == 2:
        samples = [
            (samples[index] + samples[index + 1]) // 2
            for index in range(0, len(samples), 2)
        ]
    elif channels != 1:
        raise ValueError("unsupported WAV channel count")

    if rate != target_rate:
        output_count = max(1, int(len(samples) * target_rate / rate))
        converted = []
        for index in range(output_count):
            position = index * rate / target_rate
            left = min(int(position), len(samples) - 1)
            right = min(left + 1, len(samples) - 1)
            fraction = position - left
            converted.append(int(samples[left] * (1 - fraction) + samples[right] * fraction))
        samples = converted

    with wave.open(str(destination), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(target_rate)
        writer.writeframes(struct.pack("<%dh" % len(samples), *samples))


class GloveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("手勢翻譯手套錄製工具")
        self.root.geometry("860x760")
        self.serial = None
        self.reader_thread = None
        self.running = False
        self.last_gesture_id = None
        self.audio_path = None
        self.database = RecordingDatabase()
        self.recording_frames = []
        self.mode = "single"
        self.flex_calibrated = False

        connection = ttk.Frame(root, padding=12)
        connection.pack(fill="x")
        ttk.Label(connection, text="手套 COM 埠").pack(side="left")
        self.port = ttk.Combobox(connection, width=18, state="readonly")
        self.port.pack(side="left", padx=8)
        ttk.Button(connection, text="重新整理", command=self.refresh_ports).pack(side="left")
        self.connect_button = ttk.Button(connection, text="連線", command=self.toggle_connection)
        self.connect_button.pack(side="left", padx=8)

        form = ttk.LabelFrame(root, text="錄製與標記", padding=12)
        form.pack(fill="x", padx=12, pady=4)
        ttk.Label(form, text="手勢意思").grid(row=0, column=0, sticky="w")
        self.label = ttk.Entry(form, width=40)
        self.label.grid(row=0, column=1, columnspan=3, sticky="ew", padx=8)
        ttk.Button(form, text="開始錄製", command=lambda: self.send({"command": "start_record", "max_ms": 3000})).grid(row=1, column=0, pady=10)
        ttk.Button(form, text="停止錄製", command=lambda: self.send({"command": "stop_record"})).grid(row=1, column=1)
        ttk.Button(form, text="取消", command=lambda: self.send({"command": "cancel"})).grid(row=1, column=2)
        ttk.Button(form, text="儲存標記", command=self.save_label).grid(row=1, column=3)
        ttk.Button(form, text="產生中文語音", command=self.generate_tts).grid(row=2, column=0)
        ttk.Button(form, text="選擇 WAV", command=self.choose_wav).grid(row=2, column=1)
        self.audio_label = ttk.Label(form, text="尚未選擇語音")
        self.audio_label.grid(row=2, column=2, columnspan=2, sticky="w", padx=8)
        form.columnconfigure(1, weight=1)

        sensors = ttk.LabelFrame(root, text="即時感測器讀值（唯讀）", padding=10)
        sensors.pack(fill="x", padx=12, pady=4)
        finger_names = ("拇指", "食指", "中指", "無名指", "小指")
        self.flex_values = []
        self.flex_bars = []
        for row, name in enumerate(finger_names):
            ttk.Label(sensors, text=name, width=7).grid(row=row, column=0, sticky="w")
            value = tk.StringVar(value="--")
            self.flex_values.append(value)
            ttk.Label(sensors, textvariable=value, width=12).grid(row=row, column=1)
            bar = ttk.Progressbar(sensors, maximum=65535, mode="determinate")
            bar.grid(row=row, column=2, sticky="ew", padx=(6, 12))
            self.flex_bars.append(bar)
        self.flex_unit = tk.StringVar(value="未校正：ADC 原始值")
        ttk.Label(sensors, textvariable=self.flex_unit).grid(
            row=0, column=3, rowspan=2, sticky="nw"
        )
        self.imu_values = {}
        imu_names = (
            ("Ax", "Ay", "Az"),
            ("Gx", "Gy", "Gz"),
            ("Mx", "My", "Mz"),
        )
        for group, names in enumerate(imu_names):
            frame = ttk.Frame(sensors)
            frame.grid(row=group + 2, column=3, sticky="w")
            for column, name in enumerate(names):
                value = tk.StringVar(value="--")
                self.imu_values[name] = value
                ttk.Label(frame, text=name + ":").grid(row=0, column=column * 2)
                ttk.Label(frame, textvariable=value, width=9).grid(
                    row=0, column=column * 2 + 1
                )
        sensors.columnconfigure(2, weight=1)

        actions = ttk.Frame(root, padding=(12, 6))
        actions.pack(fill="x")
        ttk.Button(actions, text="查詢狀態", command=lambda: self.send({"command": "status"})).pack(side="left")
        ttk.Button(actions, text="列出手勢", command=lambda: self.send({"command": "list"})).pack(side="left", padx=8)
        ttk.Button(actions, text="查看電腦紀錄", command=self.show_recordings).pack(side="left")
        ttk.Button(actions, text="匯出全部 CSV", command=self.export_all_csv).pack(side="left", padx=8)

        ttk.Label(root, text="訊息紀錄").pack(anchor="w", padx=12)
        self.log = tk.Text(root, height=20, state="disabled")
        self.log.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self.refresh_ports()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def refresh_ports(self):
        ports = [item.device for item in list_ports.comports()]
        self.port["values"] = ports
        if ports and not self.port.get():
            self.port.set(ports[0])

    def toggle_connection(self):
        if self.serial:
            self.disconnect()
            return
        if not self.port.get():
            messagebox.showerror("錯誤", "找不到 COM 埠")
            return
        try:
            self.serial = serial.Serial(self.port.get(), BAUD_RATE, timeout=0.2)
        except Exception as error:
            messagebox.showerror("連線失敗", str(error))
            return
        self.running = True
        self.reader_thread = threading.Thread(target=self.read_loop, daemon=True)
        self.reader_thread.start()
        self.connect_button.config(text="中斷")
        self.write_log("已連線 " + self.port.get())

    def disconnect(self):
        self.running = False
        if self.serial:
            try:
                self.serial.close()
            except Exception:
                pass
        self.serial = None
        self.connect_button.config(text="連線")
        self.write_log("已中斷")

    def send(self, payload):
        if not self.serial:
            messagebox.showwarning("尚未連線", "請先連接手套的 COM 埠")
            return
        data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        self.serial.write(data)

    def read_loop(self):
        while self.running and self.serial:
            try:
                line = self.serial.readline()
                if not line:
                    continue
                text = line.decode("utf-8", errors="replace").strip()
                self.root.after(0, self.handle_line, text)
            except Exception as error:
                self.root.after(0, self.write_log, "讀取錯誤: " + str(error))
                break

    def handle_line(self, text):
        try:
            event = json.loads(text)
        except ValueError:
            self.write_log("ESP32 > " + text)
            return
        event_name = event.get("event")
        if event_name == "sensor":
            self.update_sensor_display(event)
            return
        if event_name == "record_frame":
            values = event.get("values", [])
            if len(values) == 14:
                self.recording_frames.append(values)
                self.update_frame_display(values)
            return

        self.write_log("ESP32 > " + text)
        if event_name == "ready":
            self.mode = event.get("mode", self.mode)
        elif event_name == "status":
            self.mode = event.get("mode", self.mode)
        elif event_name == "recording":
            self.recording_frames = []
        elif event_name == "saved":
            self.last_gesture_id = event["gesture_id"]
            label = self.label.get().strip()
            if self.recording_frames:
                try:
                    row_id = self.database.add(
                        label,
                        self.last_gesture_id,
                        event.get("mode", self.mode),
                        self.recording_frames,
                        50,
                    )
                    self.write_log(
                        "已備份到電腦資料庫：紀錄 #%d（%d 筆）"
                        % (row_id, len(self.recording_frames))
                    )
                except Exception as error:
                    self.write_log("電腦資料庫備份失敗: " + str(error))
            if self.audio_path:
                threading.Thread(target=self.upload_audio, daemon=True).start()

    def update_sensor_display(self, event):
        self.flex_calibrated = bool(event.get("calibrated"))
        values = event.get("flex", [])
        if len(values) == 5:
            maximum = 100 if self.flex_calibrated else 65535
            self.flex_unit.set(
                "已校正：彎曲百分比（%）"
                if self.flex_calibrated
                else "未校正：ADC 原始值"
            )
            for index, value in enumerate(values):
                self.flex_bars[index].configure(maximum=maximum)
                self.flex_bars[index]["value"] = value
                self.flex_values[index].set(
                    "%.1f %%" % value if self.flex_calibrated else str(int(value))
                )
        for prefix, key in (("A", "accel"), ("G", "gyro"), ("M", "mag")):
            vector = event.get(key, [])
            if len(vector) == 3:
                for axis, value in zip(("x", "y", "z"), vector):
                    self.imu_values[prefix + axis].set("%.3f" % value)

    def update_frame_display(self, values):
        event = {
            "calibrated": self.flex_calibrated,
            "flex": values[:5],
            "accel": values[5:8],
            "gyro": values[8:11],
            "mag": values[11:14],
        }
        self.update_sensor_display(event)

    def show_recordings(self):
        window = tk.Toplevel(self.root)
        window.title("電腦錄製紀錄")
        window.geometry("850x430")
        columns = ("id", "time", "label", "gesture", "mode", "frames")
        tree = ttk.Treeview(window, columns=columns, show="headings", selectmode="extended")
        titles = {
            "id": "編號",
            "time": "時間",
            "label": "意思",
            "gesture": "手勢 ID",
            "mode": "模式",
            "frames": "樣本數",
        }
        widths = {"id": 60, "time": 210, "label": 170, "gesture": 80, "mode": 80, "frames": 80}
        for column in columns:
            tree.heading(column, text=titles[column])
            tree.column(column, width=widths[column], anchor="center")
        for row in self.database.list_recordings():
            tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["id"],
                    row["created_at"],
                    row["label"],
                    row["gesture_id"],
                    row["mode"],
                    row["frame_count"],
                ),
            )
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(
            window,
            text="匯出選取項目 CSV",
            command=lambda: self.export_selected_csv(tree),
        ).pack(pady=(0, 10))

    def export_selected_csv(self, tree):
        selected = [int(value) for value in tree.selection()]
        if not selected:
            messagebox.showwarning("未選取", "請先選擇至少一筆電腦紀錄")
            return
        self.export_csv(selected)

    def export_all_csv(self):
        self.export_csv(None)

    def export_csv(self, recording_ids):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 檔案", "*.csv")],
            initialfile="gesture_recordings.csv",
        )
        if not path:
            return
        try:
            count = self.database.export_csv(path, recording_ids)
            messagebox.showinfo("匯出完成", "已匯出 %d 筆感測樣本" % count)
        except Exception as error:
            messagebox.showerror("匯出失敗", str(error))

    def save_label(self):
        label = self.label.get().strip()
        if not label:
            messagebox.showwarning("缺少標記", "請輸入這個手勢代表的意思")
            return
        self.send({"command": "save", "label": label})

    def choose_wav(self):
        path = filedialog.askopenfilename(filetypes=[("WAV 音訊", "*.wav")])
        if path:
            self.audio_path = Path(path)
            self.audio_label.config(text=self.audio_path.name)

    def generate_tts(self):
        label = self.label.get().strip()
        if not label:
            messagebox.showwarning("缺少文字", "先輸入手勢意思")
            return
        try:
            import pyttsx3
            folder = Path(tempfile.gettempdir()) / "gesture_glove_tts"
            folder.mkdir(exist_ok=True)
            raw_path = folder / "raw.wav"
            output_path = folder / "speech_16k.wav"
            for old_path in (raw_path, output_path):
                if old_path.exists():
                    old_path.unlink()
            engine = pyttsx3.init()
            engine.save_to_file(label, str(raw_path))
            engine.runAndWait()
            for _ in range(20):
                if raw_path.exists() and raw_path.stat().st_size > 44:
                    break
                time.sleep(0.1)
            convert_wav(raw_path, output_path)
            self.audio_path = output_path
            self.audio_label.config(text=output_path.name)
            self.write_log("語音已產生: " + str(output_path))
        except Exception as error:
            messagebox.showerror("語音產生失敗", str(error))

    def upload_audio(self):
        path = self.audio_path
        gesture_id = self.last_gesture_id
        if not path or gesture_id is None or not self.serial:
            return
        data = path.read_bytes()
        self.send({
            "command": "audio_begin",
            "gesture_id": gesture_id,
            "size": len(data),
            "crc32": binascii.crc32(data) & 0xFFFFFFFF,
        })
        time.sleep(0.2)
        for offset in range(0, len(data), 384):
            chunk = base64.b64encode(data[offset:offset + 384]).decode("ascii")
            self.send({"command": "audio_chunk", "data": chunk})
            time.sleep(0.01)
        self.send({"command": "audio_end"})

    def write_log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def close(self):
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    GloveApp(root)
    root.mainloop()
