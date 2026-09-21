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
        self.root.geometry("760x560")
        self.serial = None
        self.reader_thread = None
        self.running = False
        self.last_gesture_id = None
        self.audio_path = None

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

        actions = ttk.Frame(root, padding=(12, 6))
        actions.pack(fill="x")
        ttk.Button(actions, text="查詢狀態", command=lambda: self.send({"command": "status"})).pack(side="left")
        ttk.Button(actions, text="列出手勢", command=lambda: self.send({"command": "list"})).pack(side="left", padx=8)

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
        self.write_log("ESP32 > " + text)
        try:
            event = json.loads(text)
        except ValueError:
            return
        if event.get("event") == "saved":
            self.last_gesture_id = event["gesture_id"]
            if self.audio_path:
                threading.Thread(target=self.upload_audio, daemon=True).start()

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
