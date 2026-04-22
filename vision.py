#!/usr/bin/env python3
"""
Huragan Vision — Motion Detection & Object Recognition System
- RTSP camera connection with auto-reconnect
- Motion detection with OpenCV
- YOLOv8 object detection (every N frames for RPi performance)
- 15-second H.264 video clips on motion trigger (via ffmpeg)
- Snapshot gallery
- Video gallery with playback
- Telegram notifications with video
- Web dashboard on port 8083
"""

import cv2
import numpy as np
import os
import time
import json
import threading
import subprocess
import sys
import tempfile
import shutil
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from collections import Counter
from ultralytics import YOLO

# ===== Config =====
CAMERA_LOCAL_IP = "192.168.1.201"
CAMERA_TAILSCALE_IP = "100.69.151.75"
CAMERA_RTSP_PORT = 8554
CAMERA_WEB_PORT = 8889
DASHBOARD_PORT = 8083
MIN_CONTOUR_AREA = 500
MOTION_THRESHOLD = 25
MIN_MOTION_FRAMES = 5
COOLDOWN_SECONDS = 10
CLIP_DURATION = 15
CLIP_FPS = 20
SAVE_DIR = "/home/server/public/motion"
SNAPSHOT_DIR = f"{SAVE_DIR}/snapshots"
CLIP_DIR = f"{SAVE_DIR}/clips"

# ===== YOLO Config =====
YOLO_ENABLED = True
YOLO_INTERVAL = 5       # run detection every N frames
YOLO_CONF = 0.4         # confidence threshold

# ===== Notification Config =====
TELEGRAM_BOT_TOKEN = "7999393924:AAFmq2ErCf5TqJ4XuV0h0hwYPEFmb6Y0P0M"
TELEGRAM_CHAT_ID = "126469825"
NOTIFY_TELEGRAM = True
NOTIFY_EMAIL = False

for d in [SAVE_DIR, SNAPSHOT_DIR, CLIP_DIR]:
    Path(d).mkdir(parents=True, exist_ok=True)


# ===== Load YOLO model =====
yolo_model = None
if YOLO_ENABLED:
    try:
        yolo_model = YOLO("yolov8n.pt")
        print(f"[YOLO] Loaded yolov8n - {len(yolo_model.names)} classes")
    except Exception as e:
        print(f"[YOLO] Failed to load: {e}")
        yolo_model = None


# ===== Telegram Notifier =====
class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    def _build_multipart(self, fields, files):
        boundary = '----HuraganBoundary' + datetime.now().strftime("%Y%m%d%H%M%S")
        body = b''
        for key, value in fields.items():
            body += f'--{boundary}\r\n'.encode()
            body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
            body += f'{value}\r\n'.encode()
        for key, filepath in files.items():
            filename = os.path.basename(filepath)
            content_type = 'video/mp4' if filepath.endswith('.mp4') else 'image/jpeg'
            body += f'--{boundary}\r\n'.encode()
            body += f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode()
            body += f'Content-Type: {content_type}\r\n\r\n'.encode()
            with open(filepath, 'rb') as f:
                body += f.read()
            body += b'\r\n'
        body += f'--{boundary}--\r\n'.encode()
        return body, boundary

    def send_video(self, text, video_path, snapshot_path=None):
        if not self.token or not self.chat_id:
            return False
        try:
            if video_path and os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                print(f"[TELEGRAM] Sending video: {os.path.basename(video_path)} ({os.path.getsize(video_path)} bytes)")
                body, boundary = self._build_multipart(
                    {'chat_id': self.chat_id, 'caption': text},
                    {'video': video_path}
                )
                req = urllib.request.Request(
                    f"{self.base_url}/sendVideo",
                    data=body,
                    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
                )
                resp = urllib.request.urlopen(req, timeout=120)
                result = json.loads(resp.read().decode())
                if result.get('ok'):
                    print("[TELEGRAM] Video sent!")
                    return True
                else:
                    print(f"[TELEGRAM] Video failed: {result.get('description')}")
                    if snapshot_path and os.path.exists(snapshot_path):
                        return self.send_photo(text, snapshot_path)
            elif snapshot_path and os.path.exists(snapshot_path):
                return self.send_photo(text, snapshot_path)
            return self.send_text(text)
        except Exception as e:
            print(f"[TELEGRAM] Error: {e}")
            return self.send_text(text)

    def send_photo(self, text, photo_path):
        try:
            body, boundary = self._build_multipart(
                {'chat_id': self.chat_id, 'caption': text},
                {'photo': photo_path}
            )
            req = urllib.request.Request(
                f"{self.base_url}/sendPhoto",
                data=body,
                headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
            )
            urllib.request.urlopen(req, timeout=60)
            print("[TELEGRAM] Photo sent!")
            return True
        except Exception as e:
            print(f"[TELEGRAM] Photo error: {e}")
            return False

    def send_text(self, text):
        try:
            url = f"{self.base_url}/sendMessage"
            data = urllib.parse.urlencode({'chat_id': self.chat_id, 'text': text}).encode()
            urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=10)
            print("[TELEGRAM] Text sent")
            return True
        except Exception as e:
            print(f"[TELEGRAM] Text error: {e}")
            return False


notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)


# ===== MJPEG Stream Buffer =====
class StreamBuffer:
    def __init__(self):
        self._frame = None
        self._lock = threading.Lock()

    def set(self, frame_bytes):
        with self._lock:
            self._frame = frame_bytes

    def get(self):
        with self._lock:
            return self._frame


stream_buf = StreamBuffer()


# ===== Motion Detector =====
class MotionDetector:
    def __init__(self):
        self.prev_gray = None
        self.motion_count = 0
        self.last_alert_time = 0
        self.is_recording = False
        self.record_frames = []
        self.record_trigger_time = None
        self.events = []
        self.fps = 0
        self._frame_count = 0
        self._fps_time = time.time()
        self._fps_count = 0
        self.motion_level = 0
        self.sensitivity = 50
        self.enabled = True
        self.snapshots = []
        self.clips = []
        self.frame_buffer = []
        self.buffer_size = CLIP_FPS * (CLIP_DURATION + 1)
        self.camera_connected = False
        self.last_snapshot_path = None
        # YOLO detection
        self.yolo_frame_count = 0
        self.detected_objects = []
        self.detection_labels = []

    def process_frame(self, frame):
        self.camera_connected = True

        # Always buffer frames for pre-motion recording
        self.frame_buffer.append(frame.copy())
        if len(self.frame_buffer) > self.buffer_size:
            self.frame_buffer.pop(0)

        # ===== YOLO Object Detection =====
        if YOLO_ENABLED and yolo_model is not None:
            self.yolo_frame_count += 1
            if self.yolo_frame_count >= YOLO_INTERVAL:
                self.yolo_frame_count = 0
                try:
                    results = yolo_model(frame, conf=YOLO_CONF, verbose=False)
                    self.detected_objects = []
                    for r in results:
                        for box in r.boxes:
                            cls_id = int(box.cls[0])
                            conf = float(box.conf[0])
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            label = yolo_model.names.get(cls_id, str(cls_id))
                            self.detected_objects.append({
                                "class": label,
                                "conf": round(conf, 2),
                                "box": [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]
                            })
                            # Draw bounding box
                            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 165, 0), 2)
                            cv2.putText(frame, f"{label} {conf:.0%}", (int(x1), int(y1) - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
                    # Build summary
                    counts = Counter(o["class"] for o in self.detected_objects)
                    self.detection_labels = [{"class": c, "count": n} for c, n in counts.most_common(10)]
                except Exception as e:
                    print(f"[YOLO] Error: {e}")

        if not self.enabled:
            self._draw_hud(frame)
            return False, frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            self._draw_hud(frame)
            return False, frame

        threshold = int(MOTION_THRESHOLD * (1 + (100 - self.sensitivity) / 50))
        min_area = int(MIN_CONTOUR_AREA * (1 + (100 - self.sensitivity) / 50))

        diff = cv2.absdiff(self.prev_gray, gray)
        _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion_detected = False
        total_motion_area = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            motion_detected = True
            total_motion_area += area
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"MOTION {area:.0f}px", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        frame_area = frame.shape[0] * frame.shape[1]
        self.motion_level = min(100, int(total_motion_area / frame_area * 500)) if frame_area > 0 else 0

        if motion_detected:
            self.motion_count += 1
        else:
            self.motion_count = max(0, self.motion_count - 1)

        now = time.time()
        significant_motion = (self.motion_count >= MIN_MOTION_FRAMES and
                              now - self.last_alert_time > COOLDOWN_SECONDS)

        if significant_motion:
            self.last_alert_time = now
            self._save_snapshot(frame)
            self._start_recording()
            self._log_event("motion_detected", self.motion_level)

        # Handle ongoing recording
        if self.is_recording:
            self.record_frames.append(frame.copy())
            elapsed = now - self.record_trigger_time
            if elapsed >= CLIP_DURATION:
                self._stop_recording()

        self._draw_hud(frame)
        self.prev_gray = gray
        return significant_motion, frame

    def _draw_hud(self, frame):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 50), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.putText(frame, "HURAGAN VISION", (15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 106, 0), 2)

        if self.is_recording and self.record_trigger_time:
            remaining = max(0, CLIP_DURATION - (time.time() - self.record_trigger_time))
            cv2.circle(frame, (w - 30, 25), 8, (0, 0, 255), -1)
            cv2.putText(frame, f"REC {remaining:.0f}s", (w - 130, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            cv2.circle(frame, (w - 30, 25), 8, (0, 200, 0), -1)

        # YOLO objects count in HUD
        if self.detection_labels:
            obj_text = " | ".join(f"{d['class']}({d['count']})" for d in self.detection_labels[:5])
            cv2.putText(frame, obj_text, (15, h - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 165, 0), 1)

        bar_w, bar_h = 150, 12
        bar_x, bar_y = w - bar_w - 15, h - 25
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)
        fill = int(bar_w * self.motion_level / 100)
        color = (0, 255, 0) if self.motion_level < 30 else (0, 165, 255) if self.motion_level < 70 else (0, 0, 255)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill, bar_y + bar_h), color, -1)
        cv2.putText(frame, f"Motion: {self.motion_level}%", (bar_x, bar_y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        self._frame_count += 1
        now = time.time()
        if now - self._fps_time >= 1.0:
            self.fps = self._frame_count - self._fps_count
            self._fps_count = self._frame_count
            self._fps_time = now
        cv2.putText(frame, f"FPS: {self.fps}", (15, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        cv2.putText(frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (w - 200, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

    def _save_snapshot(self, frame):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"motion_{ts}.jpg"
        path = os.path.join(SNAPSHOT_DIR, filename)
        cv2.imwrite(path, frame)
        self.last_snapshot_path = path
        self.snapshots.append({"file": filename, "time": datetime.now().isoformat()})
        self.snapshots = self.snapshots[-50:]
        print(f"[SNAPSHOT] {path}")

    def _start_recording(self):
        if self.is_recording:
            return
        self.is_recording = True
        self.record_trigger_time = time.time()
        pre_frames = self.frame_buffer[-CLIP_FPS:]
        self.record_frames = list(pre_frames)
        self._log_event("recording_started", self.motion_level)
        print("[REC] Started 15-sec clip recording")

    def _stop_recording(self):
        if not self.record_frames:
            self.is_recording = False
            self.record_trigger_time = None
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"motion_{ts}.mp4"
        output_path = os.path.join(CLIP_DIR, filename)

        tmpdir = tempfile.mkdtemp(prefix="vision_")
        try:
            for i, f in enumerate(self.record_frames):
                cv2.imwrite(os.path.join(tmpdir, f"frame_{i:06d}.jpg"), f,
                            [cv2.IMWRITE_JPEG_QUALITY, 90])

            result = subprocess.run([
                'ffmpeg', '-y', '-framerate', str(CLIP_FPS),
                '-i', os.path.join(tmpdir, 'frame_%06d.jpg'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-preset', 'fast', '-movflags', '+faststart',
                output_path
            ], capture_output=True, timeout=30)

            if result.returncode != 0:
                result2 = subprocess.run([
                    'ffmpeg', '-y', '-framerate', str(CLIP_FPS),
                    '-i', os.path.join(tmpdir, 'frame_%06d.jpg'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    output_path
                ], capture_output=True, timeout=30)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                actual_duration = len(self.record_frames) / CLIP_FPS
                self.clips.append({
                    "file": filename,
                    "duration": round(actual_duration, 1),
                    "time": datetime.now().isoformat(),
                    "motion_level": self.motion_level
                })
                self.clips = self.clips[-30:]
                self._log_event("recording_stopped", 0, duration=round(actual_duration, 1))
                print(f"[REC] Saved: {output_path} ({actual_duration:.1f}s)")

                # Send Telegram notification with video clip
                if NOTIFY_TELEGRAM:
                    snap = self.last_snapshot_path if self.last_snapshot_path and os.path.exists(self.last_snapshot_path) else None
                    ts_text = datetime.now().strftime("%H:%M:%S")
                    # Build object description for Telegram
                    obj_summary = ""
                    obj_detail = ""
                    if self.detection_labels:
                        obj_summary = ", ".join(f'{d["class"]}({d["count"]})' for d in self.detection_labels[:5])
                        obj_detail = "\n".join(f'  • {o["class"]} ({o["conf"]*100:.0f}%)' for o in self.detected_objects[:8])
                    text = f'⚡ Рух виявлено!\nРівень: {self.motion_level}%\nЧас: {ts_text}'
                    if obj_summary:
                        text += f'\n\n🔍 Об\'єкти: {obj_summary}\n{obj_detail}'
                    threading.Thread(
                        target=notifier.send_video,
                        args=(text, output_path, snap),
                        daemon=True
                    ).start()
            else:
                print("[REC] Failed to create clip")
                self._log_event("recording_failed", 0)

        except subprocess.TimeoutExpired:
            print("[REC] ffmpeg timed out")
            self._log_event("recording_failed", 0)
        except Exception as e:
            print(f"[REC] Error: {e}")
            self._log_event("recording_failed", 0)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        self.is_recording = False
        self.record_frames = []
        self.record_trigger_time = None

    def _log_event(self, event_type, motion_level=0, duration=0):
        self.events.append({
            "type": event_type,
            "time": datetime.now().isoformat(),
            "motion_level": motion_level,
            "duration": duration
        })
        self.events = self.events[-100:]

    def manual_record(self, frame):
        if self.is_recording:
            return "already_recording"
        self._start_recording()
        return "recording"

    def get_status(self):
        recording_elapsed = 0
        if self.is_recording and self.record_trigger_time:
            recording_elapsed = time.time() - self.record_trigger_time
        return {
            "status": "recording" if self.is_recording else ("monitoring" if self.enabled else "paused"),
            "fps": self.fps,
            "motion_level": self.motion_level,
            "motion_frames": self.motion_count,
            "events_count": len(self.events),
            "snapshots_count": len(self.snapshots),
            "clips_count": len(self.clips),
            "sensitivity": self.sensitivity,
            "enabled": self.enabled,
            "is_recording": self.is_recording,
            "recording_elapsed": round(recording_elapsed, 1),
            "recording_remaining": round(max(0, CLIP_DURATION - recording_elapsed), 1),
            "clip_duration": CLIP_DURATION,
            "camera_connected": self.camera_connected,
            "yolo_enabled": YOLO_ENABLED and yolo_model is not None,
            "detected_objects": self.detected_objects,
            "detection_labels": self.detection_labels,
            "events": self.events[-30:],
            "snapshots": self.snapshots[-10:],
            "clips": self.clips[-10:]
        }


detector = MotionDetector()


# ===== HTTP Server =====
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/dashboard'):
            self._send_html_file()
        elif self.path == '/stream':
            self._serve_mjpeg()
        elif self.path == '/api/status':
            self._send_json(detector.get_status())
        elif self.path.startswith('/motion/snapshots/'):
            self._serve_static(SNAPSHOT_DIR, self.path.split('/')[-1])
        elif self.path.startswith('/motion/clips/'):
            self._serve_video(CLIP_DIR, self.path.split('/')[-1])
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/toggle':
            detector.enabled = not detector.enabled
            self._send_json(detector.get_status())
        elif self.path == '/api/sensitivity':
            body = self._read_json()
            detector.sensitivity = max(0, min(100, body.get('value', 50)))
            self._send_json(detector.get_status())
        elif self.path == '/api/snapshot':
            frame_data = stream_buf.get()
            if frame_data:
                arr = np.frombuffer(frame_data, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"manual_{ts}.jpg"
                    cv2.imwrite(os.path.join(SNAPSHOT_DIR, filename), frame)
                    detector.snapshots.append({"file": filename, "time": datetime.now().isoformat()})
                    detector.snapshots = detector.snapshots[-50:]
            self._send_json(detector.get_status())
        elif self.path == '/api/record':
            frame_data = stream_buf.get()
            if frame_data:
                arr = np.frombuffer(frame_data, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    result = detector.manual_record(frame)
                    self._send_json({"result": result})
                else:
                    self._send_json({"result": "no_frame"})
            else:
                self._send_json({"result": "no_frame"})
        elif self.path == '/api/delete/clip':
            body = self._read_json()
            filename = body.get('file', '')
            path = os.path.join(CLIP_DIR, filename)
            if os.path.exists(path):
                os.remove(path)
                detector.clips = [c for c in detector.clips if c['file'] != filename]
            self._send_json(detector.get_status())
        elif self.path == '/api/delete/snapshot':
            body = self._read_json()
            filename = body.get('file', '')
            path = os.path.join(SNAPSHOT_DIR, filename)
            if os.path.exists(path):
                os.remove(path)
                detector.snapshots = [s for s in detector.snapshots if s['file'] != filename]
            self._send_json(detector.get_status())
        else:
            self.send_response(404)
            self.end_headers()

    def _read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        if length > 0:
            return json.loads(self.rfile.read(length))
        return {}

    def _send_html_file(self):
        try:
            with open(DASHBOARD_HTML_PATH, "r") as f:
                html = f.read()
        except Exception:
            html = "<h1>Dashboard not found</h1>"
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _serve_mjpeg(self):
        self.send_response(200)
        self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        try:
            while True:
                frame = stream_buf.get()
                if frame:
                    self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n')
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
                time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _serve_static(self, directory, filename):
        path = os.path.join(directory, filename)
        if not os.path.exists(path):
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        if filename.endswith('.jpg'):
            self.send_header('Content-type', 'image/jpeg')
        elif filename.endswith('.mp4'):
            self.send_header('Content-type', 'video/mp4')
        self.send_header('Content-Length', str(os.path.getsize(path)))
        self.end_headers()
        try:
            with open(path, 'rb') as f:
                self.wfile.write(f.read())
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _serve_video(self, directory, filename):
        path = os.path.join(directory, filename)
        if not os.path.exists(path):
            self.send_response(404)
            self.end_headers()
            return
        file_size = os.path.getsize(path)
        range_header = self.headers.get('Range')
        try:
            if range_header:
                parts = range_header.replace('bytes=', '').split('-')
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else file_size - 1
                end = min(end, file_size - 1)
                length = end - start + 1
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                self.send_header('Content-Length', str(length))
                self.send_header('Content-type', 'video/mp4')
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()
                with open(path, 'rb') as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
            else:
                self.send_response(200)
                self.send_header('Content-type', 'video/mp4')
                self.send_header('Content-Length', str(file_size))
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()
                with open(path, 'rb') as f:
                    self.wfile.write(f.read())
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def log_message(self, format, *args):
        pass



# ===== Dashboard HTML (loaded from file) =====
DASHBOARD_HTML_PATH = "/home/server/public/dashboard.html"



# ===== Camera Capture =====
def capture_loop():
    print("[CAM] Starting capture loop...")
    urls = [
        f"rtsp://{CAMERA_TAILSCALE_IP}:{CAMERA_RTSP_PORT}/cam",
        f"rtsp://{CAMERA_LOCAL_IP}:{CAMERA_RTSP_PORT}/cam",
    ]

    cap = None
    for url in urls:
        print(f"[CAM] Trying: {url}")
        try:
            test_cap = cv2.VideoCapture(url)
            if test_cap.isOpened():
                ret, frame = test_cap.read()
                if ret and frame is not None:
                    cap = test_cap
                    print(f"[CAM] Connected via: {url}")
                    break
                test_cap.release()
        except Exception as e:
            print(f"[CAM] Error: {e}")

    if cap is None or not cap.isOpened():
        print("[CAM] All connections failed. Retrying in 10s...")
        time.sleep(10)
        capture_loop()
        return

    print("[CAM] Streaming!")
    fail_count = 0

    while True:
        try:
            ret, frame = cap.read()
            if not ret or frame is None:
                fail_count += 1
                if fail_count > 30:
                    print("[CAM] Too many failures. Reconnecting...")
                    cap.release()
                    time.sleep(3)
                    cap = cv2.VideoCapture(urls[0])
                    fail_count = 0
                time.sleep(0.1)
                continue

            fail_count = 0
            alert, annotated = detector.process_frame(frame)

            _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            stream_buf.set(buf.tobytes())

        except Exception as e:
            print(f"[CAM] Error: {e}")
            time.sleep(1)


# ===== Main =====
def main():
    print("=" * 50)
    print("HURAGAN VISION - Motion & Object Detection")
    print("=" * 50)
    print(f"Dashboard: http://0.0.0.0:{DASHBOARD_PORT}")
    print(f"Clip duration: {CLIP_DURATION}s on motion trigger")
    print(f"YOLO detection: {'ON' if yolo_model else 'OFF'} (every {YOLO_INTERVAL} frames)")
    print(f"Telegram notifications: {'ON' if NOTIFY_TELEGRAM else 'OFF'}")
    print("=" * 50)

    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        print(f"[FFMPEG] Available")
    except Exception:
        print("[FFMPEG] WARNING: ffmpeg not found!")

    server = ThreadedHTTPServer(('0.0.0.0', DASHBOARD_PORT), Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[HTTP] Dashboard on port {DASHBOARD_PORT}")

    try:
        capture_loop()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping...")
        server.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()