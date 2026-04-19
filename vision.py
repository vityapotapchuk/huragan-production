#!/usr/bin/env python3
"""
Huragan Vision — Complete Camera & Motion Detection System
- MJPEG proxy from WebRTC camera
- Motion detection with OpenCV
- Recording & snapshots
- Beautiful web dashboard
"""

import cv2
import numpy as np
import os
import time
import json
import threading
import subprocess
import signal
import sys
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import io

# ===== Config =====
CAMERA_LOCAL_IP = "192.168.1.201"
CAMERA_TAILSCALE_IP = "100.69.151.75"
CAMERA_WEB_PORT = 8889
MJPEG_PORT = 8888          # Local MJPEG stream port
DASHBOARD_PORT = 8081      # Web dashboard
MIN_CONTOUR_AREA = 500
MOTION_THRESHOLD = 25
MIN_MOTION_FRAMES = 5
COOLDOWN_SECONDS = 10
SAVE_DIR = "/home/server/public/motion"
SNAPSHOT_DIR = f"{SAVE_DIR}/snapshots"
CLIP_DIR = f"{SAVE_DIR}/clips"
LOG_FILE = f"{SAVE_DIR}/motion_log.json"

for d in [SAVE_DIR, SNAPSHOT_DIR, CLIP_DIR]:
    Path(d).mkdir(parents=True, exist_ok=True)


# ===== MJPEG Stream Server =====
class StreamServer:
    """Serves MJPEG frames from motion detection to browsers"""
    def __init__(self):
        self.frame = None
        self.lock = threading.Lock()
        self.clients = 0

    def set_frame(self, frame):
        with self.lock:
            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            self.frame = buf.tobytes()

    def get_frame(self):
        with self.lock:
            return self.frame


stream_server = StreamServer()


# ===== Motion Detector =====
class MotionDetector:
    def __init__(self):
        self.prev_gray = None
        self.motion_count = 0
        self.last_alert_time = 0
        self.is_recording = False
        self.video_writer = None
        self.record_start = None
        self.events = []
        self.status = "initializing"
        self.fps = 0
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.last_fps_count = 0
        self.motion_level = 0  # 0-100
        self.roi = None  # Region of interest
        self.sensitivity = 50  # 0-100
        self.enabled = True
        self.snapshots = []
        self.clips = []

    def process_frame(self, frame):
        if not self.enabled:
            return False, frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # Apply ROI if set
        if self.roi:
            x, y, w, h = self.roi
            mask = np.zeros(gray.shape, dtype=np.uint8)
            mask[y:y+h, x:x+w] = 255
            gray = cv2.bitwise_and(gray, gray, mask=mask)

        if self.prev_gray is None:
            self.prev_gray = gray
            return False, frame

        # Adjust threshold based on sensitivity
        threshold = int(MOTION_THRESHOLD * (1 + (100 - self.sensitivity) / 50))

        diff = cv2.absdiff(self.prev_gray, gray)
        thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion_detected = False
        total_motion_area = 0

        min_area = int(MIN_CONTOUR_AREA * (1 + (100 - self.sensitivity) / 50))

        for contour in contours:
            if cv2.contourArea(contour) < min_area:
                continue
            motion_detected = True
            area = cv2.contourArea(contour)
            total_motion_area += area
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"MOTION {area:.0f}px", (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Motion level 0-100
        frame_area = frame.shape[0] * frame.shape[1]
        self.motion_level = min(100, int(total_motion_area / frame_area * 500))

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
            self._log_event("motion_detected", self.motion_level)

        if self.motion_count >= MIN_MOTION_FRAMES and not self.is_recording:
            self._start_recording(frame)
        elif self.motion_count == 0 and self.is_recording:
            self._stop_recording()

        if self.is_recording and self.video_writer:
            self.video_writer.write(frame)

        # HUD overlay
        self._draw_hud(frame)

        self.prev_gray = gray
        return significant_motion, frame

    def _draw_hud(self, frame):
        h, w = frame.shape[:2]
        # Top bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 50), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # Logo
        cv2.putText(frame, "HURAGAN VISION", (15, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 106, 0), 2)

        # Status
        if self.is_recording:
            cv2.circle(frame, (w - 30, 25), 8, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (w - 80, 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            cv2.circle(frame, (w - 30, 25), 8, (0, 200, 0), -1)

        # Motion bar
        bar_w = 150
        bar_h = 12
        bar_x = w - bar_w - 15
        bar_y = h - 25
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)
        fill = int(bar_w * self.motion_level / 100)
        color = (0, 255, 0) if self.motion_level < 30 else (0, 165, 255) if self.motion_level < 70 else (0, 0, 255)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill, bar_y + bar_h), color, -1)
        cv2.putText(frame, f"Motion: {self.motion_level}%", (bar_x, bar_y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # FPS
        self.frame_count += 1
        now = time.time()
        if now - self.last_fps_time >= 1.0:
            self.fps = self.frame_count - self.last_fps_count
            self.last_fps_count = self.frame_count
            self.last_fps_time = now
        cv2.putText(frame, f"FPS: {self.fps}", (15, h - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

        # Timestamp
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, ts, (w - 200, h - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

    def _save_snapshot(self, frame):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{SNAPSHOT_DIR}/motion_{ts}.jpg"
        cv2.imwrite(path, frame)
        self.snapshots.append({"file": f"motion_{ts}.jpg", "time": datetime.now().isoformat()})
        self.snapshots = self.snapshots[-50:]
        print(f"[SNAPSHOT] {path}")

    def _start_recording(self, frame):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h, w = frame.shape[:2]
        path = f"{CLIP_DIR}/motion_{ts}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(path, fourcc, 20.0, (w, h))
        self.is_recording = True
        self.record_start = time.time()
        self._log_event("recording_started", self.motion_level)
        print(f"[REC] Started: {path}")

    def _stop_recording(self):
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        self.is_recording = False
        duration = time.time() - self.record_start if self.record_start else 0
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.clips.append({"file": f"motion_{ts}.mp4", "duration": round(duration, 1), "time": datetime.now().isoformat()})
        self.clips = self.clips[-20:]
        self._log_event("recording_stopped", 0, duration=round(duration, 1))
        print(f"[REC] Stopped. Duration: {duration:.1f}s")

    def _log_event(self, event_type, level=0, duration=0):
        event = {
            "type": event_type,
            "time": datetime.now().isoformat(),
            "motion_level": level,
            "duration": duration
        }
        self.events.append(event)
        self.events = self.events[-200:]
        with open(LOG_FILE, 'w') as f:
            json.dump(self.events, f, indent=2)

    def get_status(self):
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
            "events": self.events[-30:],
            "snapshots": self.snapshots[-10:],
            "clips": self.clips[-10:]
        }


detector = MotionDetector()


# ===== Dashboard HTTP Server =====
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/dashboard':
            self._serve_dashboard()
        elif self.path == '/stream':
            self._serve_mjpeg()
        elif self.path == '/api/status':
            self._serve_json()
        elif self.path.startswith('/motion/snapshots/'):
            self._serve_file(SNAPSHOT_DIR, self.path.split('/')[-1])
        elif self.path.startswith('/motion/clips/'):
            self._serve_file(CLIP_DIR, self.path.split('/')[-1])
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/toggle':
            detector.enabled = not detector.enabled
            self._serve_json()
        elif self.path == '/api/sensitivity':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            detector.sensitivity = max(0, min(100, body.get('value', 50)))
            self._serve_json()
        elif self.path == '/api/snapshot':
            if stream_server.get_frame() is not None:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = f"{SNAPSHOT_DIR}/manual_{ts}.jpg"
                frame_array = np.frombuffer(stream_server.get_frame(), dtype=np.uint8)
                frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                cv2.imwrite(path, frame)
                detector.snapshots.append({"file": f"manual_{ts}.jpg", "time": datetime.now().isoformat()})
                detector.snapshots = detector.snapshots[-50:]
            self._serve_json()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_dashboard(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = DASHBOARD_HTML
        self.wfile.write(html.encode())

    def _serve_mjpeg(self):
        self.send_response(200)
        self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        try:
            while True:
                frame = stream_server.get_frame()
                if frame:
                    self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n')
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
                time.sleep(0.05)
        except:
            pass

    def _serve_json(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(detector.get_status()).encode())

    def _serve_file(self, directory, filename):
        path = os.path.join(directory, filename)
        if os.path.exists(path):
            self.send_response(200)
            if filename.endswith('.jpg'):
                self.send_header('Content-type', 'image/jpeg')
            elif filename.endswith('.mp4'):
                self.send_header('Content-type', 'video/mp4')
            self.end_headers()
            with open(path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Huragan Vision</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#000;color:#fff;font-family:'Inter',system-ui,sans-serif;overflow-x:hidden}
.header{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(0,0,0,0.9);
  backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,106,0,0.2);padding:12px 24px;
  display:flex;align-items:center;justify-content:space-between}
.logo{font-size:1.2rem;font-weight:900;color:#FF6A00;letter-spacing:3px;text-transform:uppercase}
.header-status{display:flex;align-items:center;gap:16px}
.status-dot{width:10px;height:10px;border-radius:50%;display:inline-block}
.status-dot.on{background:#0f0;box-shadow:0 0 10px #0f0}
.status-dot.rec{background:#f00;box-shadow:0 0 10px #f00;animation:pulse 1s infinite}
.status-dot.off{background:#666}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
.status-text{font-size:0.8rem;font-weight:600;text-transform:uppercase;letter-spacing:1px}

.main{padding-top:70px;display:grid;grid-template-columns:1fr 360px;gap:0;height:100vh}

.stream-panel{position:relative;background:#111;display:flex;align-items:center;justify-content:center;overflow:hidden}
.stream-panel img{width:100%;height:100%;object-fit:contain}
.stream-overlay{position:absolute;bottom:0;left:0;right:0;padding:20px;
  background:linear-gradient(transparent,rgba(0,0,0,0.8));display:flex;align-items:flex-end;justify-content:space-between}
.motion-bar{width:200px;height:8px;background:#333;border-radius:4px;overflow:hidden}
.motion-fill{height:100%;border-radius:4px;transition:width 0.3s,background 0.3s}
.no-stream{color:#555;font-size:1.2rem;text-transform:uppercase;letter-spacing:3px}

.side-panel{background:#0a0a0a;border-left:1px solid rgba(255,255,255,0.06);
  overflow-y:auto;padding:24px;display:flex;flex-direction:column;gap:20px}

.card{background:#111;border:1px solid rgba(255,255,255,0.06);border-radius:16px;padding:20px}
.card-title{font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:2px;
  color:#FF6A00;margin-bottom:16px}

.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.stat-item{text-align:center;padding:12px;background:#0a0a0a;border-radius:12px}
.stat-value{font-size:1.8rem;font-weight:900;color:#fff}
.stat-value.orange{color:#FF6A00}
.stat-value.green{color:#0f0}
.stat-value.red{color:#f00}
.stat-label{font-size:0.65rem;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1px;margin-top:4px}

.controls{display:flex;flex-direction:column;gap:12px}
.btn{padding:12px 20px;border-radius:12px;border:none;font-weight:700;font-size:0.8rem;
  cursor:pointer;text-transform:uppercase;letter-spacing:1px;transition:all 0.3s}
.btn-primary{background:#FF6A00;color:#fff}
.btn-primary:hover{background:#FF8533;transform:translateY(-1px)}
.btn-outline{background:transparent;color:#fff;border:2px solid rgba(255,255,255,0.2)}
.btn-outline:hover{border-color:#FF6A00;color:#FF6A00}
.btn-danger{background:#c00;color:#fff}
.btn-danger:hover{background:#f00}
.btn-row{display:flex;gap:8px}
.btn-row .btn{flex:1}

.slider-group{display:flex;flex-direction:column;gap:8px}
.slider-label{display:flex;justify-content:space-between;font-size:0.8rem;color:rgba(255,255,255,0.6)}
.slider-label span:last-child{color:#FF6A00;font-weight:700}
input[type=range]{-webkit-appearance:none;width:100%;height:6px;background:#333;border-radius:3px;outline:none}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;
  background:#FF6A00;border-radius:50%;cursor:pointer}

.events{max-height:300px;overflow-y:auto}
.event{padding:10px 14px;margin:6px 0;background:#0a0a0a;border-radius:10px;
  border-left:3px solid #FF6A00;font-size:0.8rem}
.event .time{color:rgba(255,255,255,0.4);font-size:0.7rem}
.event .type{color:#fff;font-weight:600}
.event .level{color:#FF6A00}

.gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.gallery img{width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:8px;cursor:pointer;
  transition:transform 0.3s}
.gallery img:hover{transform:scale(1.05)}

@media(max-width:900px){
  .main{grid-template-columns:1fr;grid-template-rows:50vh auto}
  .side-panel{border-left:none;border-top:1px solid rgba(255,255,255,0.06)}
}
</style>
</head>
<body>
<div class="header">
  <div class="logo">⚡ Huragan Vision</div>
  <div class="header-status">
    <span class="status-dot" id="statusDot"></span>
    <span class="status-text" id="statusText">Connecting...</span>
  </div>
</div>

<div class="main">
  <div class="stream-panel">
    <img id="stream" src="/stream" alt="Camera Stream" onerror="this.style.display='none';document.getElementById('noStream').style.display='flex'">
    <div class="no-stream" id="noStream" style="display:none;position:absolute;flex-direction:column;align-items:center;gap:12px">
      <span style="font-size:3rem">📷</span>
      <span>Camera Offline</span>
    </div>
    <div class="stream-overlay">
      <div>
        <div style="font-size:0.7rem;color:rgba(255,255,255,0.5);margin-bottom:6px">MOTION LEVEL</div>
        <div class="motion-bar"><div class="motion-fill" id="motionFill"></div></div>
      </div>
      <div style="font-size:0.8rem;font-weight:700" id="motionText">0%</div>
    </div>
  </div>

  <div class="side-panel">
    <div class="card">
      <div class="card-title">Live Stats</div>
      <div class="stat-grid">
        <div class="stat-item"><div class="stat-value orange" id="fpsVal">0</div><div class="stat-label">FPS</div></div>
        <div class="stat-item"><div class="stat-value" id="motionVal">0%</div><div class="stat-label">Motion</div></div>
        <div class="stat-item"><div class="stat-value green" id="eventsVal">0</div><div class="stat-label">Events</div></div>
        <div class="stat-item"><div class="stat-value" id="snapsVal">0</div><div class="stat-label">Snapshots</div></div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Controls</div>
      <div class="controls">
        <div class="btn-row">
          <button class="btn btn-primary" onclick="takeSnapshot()">📸 Snapshot</button>
          <button class="btn btn-outline" id="toggleBtn" onclick="toggleDetection()">⏸ Pause</button>
        </div>
        <div class="slider-group">
          <div class="slider-label"><span>Sensitivity</span><span id="sensVal">50%</span></div>
          <input type="range" min="0" max="100" value="50" id="sensSlider" oninput="setSensitivity(this.value)">
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Recent Events</div>
      <div class="events" id="eventsList">
        <div style="color:rgba(255,255,255,0.3);font-size:0.8rem">No events yet</div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Snapshots</div>
      <div class="gallery" id="gallery">
        <div style="color:rgba(255,255,255,0.3);font-size:0.8rem;grid-column:1/-1">No snapshots yet</div>
      </div>
    </div>
  </div>
</div>

<script>
let enabled = true;

async function updateStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    
    // Status
    const dot = document.getElementById('statusDot');
    const txt = document.getElementById('statusText');
    if (d.status === 'recording') { dot.className = 'status-dot rec'; txt.textContent = '● RECORDING'; }
    else if (d.status === 'monitoring') { dot.className = 'status-dot on'; txt.textContent = '○ MONITORING'; }
    else { dot.className = 'status-dot off'; txt.textContent = '⏸ PAUSED'; }
    
    // Stats
    document.getElementById('fpsVal').textContent = d.fps;
    document.getElementById('motionVal').textContent = d.motion_level + '%';
    document.getElementById('eventsVal').textContent = d.events_count;
    document.getElementById('snapsVal').textContent = d.snapshots_count;
    
    // Motion bar
    const fill = document.getElementById('motionFill');
    fill.style.width = d.motion_level + '%';
    fill.style.background = d.motion_level < 30 ? '#0f0' : d.motion_level < 70 ? '#FF6A00' : '#f00';
    document.getElementById('motionText').textContent = d.motion_level + '%';
    
    // Sensitivity
    document.getElementById('sensSlider').value = d.sensitivity;
    document.getElementById('sensVal').textContent = d.sensitivity + '%';
    enabled = d.enabled;
    document.getElementById('toggleBtn').textContent = enabled ? '⏸ Pause' : '▶ Resume';
    document.getElementById('toggleBtn').className = enabled ? 'btn btn-outline' : 'btn btn-primary';
    
    // Events
    const el = document.getElementById('eventsList');
    if (d.events.length) {
      el.innerHTML = d.events.slice(-10).reverse().map(e =>
        `<div class="event"><div class="time">${new Date(e.time).toLocaleTimeString()}</div>
         <div class="type">${e.type.replace(/_/g,' ')}</div>
         ${e.motion_level ? `<div class="level">Level: ${e.motion_level}%</div>` : ''}
         ${e.duration ? `<div class="level">Duration: ${e.duration}s</div>` : ''}</div>`
      ).join('');
    }
    
    // Gallery
    const gl = document.getElementById('gallery');
    if (d.snapshots && d.snapshots.length) {
      gl.innerHTML = d.snapshots.slice(-6).reverse().map(s =>
        `<img src="/motion/snapshots/${s.file}" title="${s.time}">`
      ).join('');
    }
  } catch(e) {}
}

async function toggleDetection() {
  await fetch('/api/toggle', {method:'POST'});
  updateStatus();
}

async function setSensitivity(v) {
  document.getElementById('sensVal').textContent = v + '%';
  await fetch('/api/sensitivity', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:+v})});
}

async function takeSnapshot() {
  await fetch('/api/snapshot', {method:'POST'});
  updateStatus();
}

setInterval(updateStatus, 1000);
updateStatus();
</script>
</body>
</html>"""


# ===== Camera Capture Thread =====
def capture_loop():
    """Capture frames from camera and process motion"""
    print("[CAM] Starting capture loop...")

    # Try different camera URLs
    urls = [
        f"http://{CAMERA_LOCAL_IP}:{CAMERA_WEB_PORT}/cam",
        f"http://{CAMERA_TAILSCALE_IP}:{CAMERA_WEB_PORT}/cam",
    ]

    cap = None
    for url in urls:
        print(f"[CAM] Trying: {url}")
        test_cap = cv2.VideoCapture(url)
        if test_cap.isOpened():
            ret, frame = test_cap.read()
            if ret and frame is not None:
                cap = test_cap
                print(f"[CAM] Connected via: {url}")
                break
            test_cap.release()

    if cap is None or not cap.isOpened():
        print("[CAM] Direct OpenCV connection failed. Using FFmpeg pipeline...")
        # Use FFmpeg to convert WebRTC/MJPEG to raw frames
        for url in urls:
            try:
                ffmpeg_cmd = [
                    'ffmpeg', '-y', '-i', url,
                    '-f', 'rawvideo', '-pix_fmt', 'bgr24',
                    '-an', '-sn', '-'
                ]
                process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                # Read first frame to check
                # We'll use a different approach - save frames via HTTP
                process.kill()
            except:
                pass

        # Fallback: periodic HTTP snapshot capture
        print("[CAM] Using HTTP snapshot polling mode...")
        detector.status = "polling"
        import urllib.request

        while True:
            try:
                for url in urls:
                    try:
                        resp = urllib.request.urlopen(url, timeout=5)
                        data = resp.read()
                        # Try to decode as image
                        arr = np.frombuffer(data, dtype=np.uint8)
                        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            alert, annotated = detector.process_frame(frame)
                            stream_server.set_frame(annotated)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"[CAM] Error: {e}")
                detector.status = "reconnecting"

            time.sleep(0.1)  # ~10 FPS in polling mode
        return

    detector.status = "monitoring"
    print("[CAM] Streaming!")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[CAM] Frame lost. Reconnecting...")
            cap.release()
            time.sleep(2)
            cap = cv2.VideoCapture(urls[0])
            continue

        alert, annotated = detector.process_frame(frame)
        stream_server.set_frame(annotated)


# ===== Main =====
def main():
    print("=" * 50)
    print("HURAGAN VISION - Motion Detection System")
    print("=" * 50)
    print(f"Dashboard: http://0.0.0.0:{DASHBOARD_PORT}")
    print(f"MJPEG Stream: http://0.0.0.0:{MJPEG_PORT}")
    print("=" * 50)

    # Start dashboard server
    server = ThreadedHTTPServer(('0.0.0.0', DASHBOARD_PORT), DashboardHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[HTTP] Dashboard on port {DASHBOARD_PORT}")

    # Start capture in main thread
    try:
        capture_loop()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping...")
        server.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()