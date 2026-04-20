#!/usr/bin/env python3
"""
Huragan Notifier — Telegram & Email notifications for motion events
"""

import os
import json
import urllib.request
import urllib.parse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime


class Notifier:
    def __init__(self, telegram_token="", telegram_chat_id="",
                 email_from="", email_password="", email_to="",
                 notify_telegram=False, notify_email=False):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.email_from = email_from
        self.email_password = email_password
        self.email_to = email_to
        self.notify_telegram = notify_telegram
        self.notify_email = notify_email

    def _build_multipart(self, fields, files):
        """Build multipart/form-data body with proper encoding"""
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

    def send_telegram(self, text, video_path=None, snapshot_path=None):
        """Send notification via Telegram Bot API"""
        if not self.telegram_token or not self.telegram_chat_id:
            return False
        try:
            base = f"https://api.telegram.org/bot{self.telegram_token}"
            
            # Send video clip if available
            if video_path and os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                print(f"[TELEGRAM] Sending video: {os.path.basename(video_path)} ({os.path.getsize(video_path)} bytes)")
                body, boundary = self._build_multipart(
                    {'chat_id': self.telegram_chat_id, 'caption': text},
                    {'video': video_path}
                )
                req = urllib.request.Request(
                    f"{base}/sendVideo",
                    data=body,
                    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
                )
                response = urllib.request.urlopen(req, timeout=120)
                result = json.loads(response.read().decode())
                if result.get('ok'):
                    print(f"[TELEGRAM] Video sent successfully!")
                    return True
                else:
                    print(f"[TELEGRAM] Video send failed: {result.get('description', 'unknown')}")
                    # Fallback: send snapshot instead
                    if snapshot_path and os.path.exists(snapshot_path):
                        return self.send_telegram(text, video_path=None, snapshot_path=snapshot_path)

            # Send snapshot if video not available
            elif snapshot_path and os.path.exists(snapshot_path):
                print(f"[TELEGRAM] Sending photo: {os.path.basename(snapshot_path)}")
                body, boundary = self._build_multipart(
                    {'chat_id': self.telegram_chat_id, 'caption': text},
                    {'photo': snapshot_path}
                )
                req = urllib.request.Request(
                    f"{base}/sendPhoto",
                    data=body,
                    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
                )
                urllib.request.urlopen(req, timeout=60)
                print(f"[TELEGRAM] Photo sent successfully!")
                return True

            # Text only fallback
            else:
                url = f"{base}/sendMessage"
                data = urllib.parse.urlencode({'chat_id': self.telegram_chat_id, 'text': text}).encode()
                req = urllib.request.Request(url, data=data)
                urllib.request.urlopen(req, timeout=10)
                print("[TELEGRAM] Text message sent")
                return True

        except Exception as e:
            print(f"[TELEGRAM] Error: {e}")
            # Fallback to text message if video/photo fails
            try:
                url = f"{base}/sendMessage"
                data = urllib.parse.urlencode({'chat_id': self.telegram_chat_id, 'text': text}).encode()
                req = urllib.request.Request(url, data=data)
                urllib.request.urlopen(req, timeout=10)
                print("[TELEGRAM] Fallback text message sent")
                return True
            except:
                return False

    def send_email(self, subject, text, video_path=None, snapshot_path=None):
        """Send notification via Email (SMTP)"""
        if not self.email_from or not self.email_password or not self.email_to:
            return False
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            msg['Subject'] = subject
            msg.attach(MIMEText(text, 'plain'))

            if video_path and os.path.exists(video_path):
                with open(video_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(video_path)}"')
                    msg.attach(part)

            if snapshot_path and os.path.exists(snapshot_path):
                with open(snapshot_path, 'rb') as f:
                    part = MIMEBase('image', 'jpeg')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(snapshot_path)}"')
                    msg.attach(part)

            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.email_from, self.email_password)
                server.send_message(msg)
            print(f"[EMAIL] Sent to {self.email_to}")
            return True
        except Exception as e:
            print(f"[EMAIL] Error: {e}")
            return False

    def notify_motion(self, motion_level, clip_path=None, snapshot_path=None):
        """Send motion notification via all enabled channels"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = f"⚡ Huragan Vision — Motion Detected!\n\nLevel: {motion_level}%\nTime: {ts}"
        
        # Wait for video file to be fully written
        if clip_path:
            for _ in range(10):
                if os.path.exists(clip_path) and os.path.getsize(clip_path) > 0:
                    break
                import time
                time.sleep(0.5)

        if self.notify_telegram:
            self.send_telegram(text, video_path=clip_path, snapshot_path=snapshot_path)

        if self.notify_email:
            subject = f"⚡ Motion Detected — {motion_level}% — {ts}"
            self.send_email(subject, text, video_path=clip_path, snapshot_path=snapshot_path)