import re

with open('vision.py', 'r') as f:
    content = f.read()

old = """    def _stop_recording(self):
        if not self.record_frames:
            self.is_recording = False
            self.record_trigger_time = None
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"motion_{ts}.mp4"
        output_path = os.path.join(CLIP_DIR, filename)

        # Save frames as JPGs in temp dir, then encode with ffmpeg to H.264
        tmpdir = tempfile.mkdtemp(prefix="vision_")
            for i, f in enumerate(self.record_frames):
                cv2.imwrite(os.path.join(tmpdir, f"frame_{i:06d}.jpg"), f,
                            [cv2.IMWRITE_JPEG_QUALITY, 90])

            result = subprocess.run([
                'ffmpeg', '-y',
                '-framerate', str(CLIP_FPS),
                '-i', os.path.join(tmpdir, 'frame_%06d.jpg'),
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-preset', 'fast',
                '-movflags', '+faststart',
                output_path
            ], capture_output=True, timeout=30)

            if result.returncode != 0:
                print(f"[REC] ffmpeg error: {result.stderr.decode()[:200]}")
                # Fallback: try with simpler encoding
                result2 = subprocess.run([
                    'ffmpeg', '-y',
                    '-framerate', str(CLIP_FPS),
                    '-i', os.path.join(tmpdir, 'frame_%06d.jpg'),
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    output_path
                ], capture_output=True, timeout=30)
                if result2.returncode != 0:
                    print(f"[REC] ffmpeg fallback also failed")

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
                notifier.notify_motion(self.motion_level, clip_path=output_path, snapshot_path=os.path.join(SNAPSHOT_DIR, self.snapshots[-1]["file"]) if self.snapshots else None)
                # Send Telegram notification with video clip
            else:
                print(f"[REC] Failed to create clip")
                self._log_event("recording_failed", 0)

        except subprocess.TimeoutExpired:
            print("[REC] ffmpeg timed out")
            self._log_event("recording_failed", 0)
            print(f"[REC] Error: {e}")
            self._log_event("recording_failed", 0)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        self.is_recording = False
        self.record_frames = []
        self.record_trigger_time = None"""

new = """    def _stop_recording(self):
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
                'ffmpeg', '-y',
                '-framerate', str(CLIP_FPS),
                '-i', os.path.join(tmpdir, 'frame_%06d.jpg'),
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-preset', 'fast',
                '-movflags', '+faststart',
                output_path
            ], capture_output=True, timeout=30)

            if result.returncode != 0:
                print(f"[REC] ffmpeg error: {result.stderr.decode()[:200]}")
                result2 = subprocess.run([
                    'ffmpeg', '-y',
                    '-framerate', str(CLIP_FPS),
                    '-i', os.path.join(tmpdir, 'frame_%06d.jpg'),
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    output_path
                ], capture_output=True, timeout=30)
                if result2.returncode != 0:
                    print(f"[REC] ffmpeg fallback also failed")

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
                snap_path = os.path.join(SNAPSHOT_DIR, self.snapshots[-1]["file"]) if self.snapshots else None
                notifier.notify_motion(self.motion_level, clip_path=output_path, snapshot_path=snap_path)
            else:
                print(f"[REC] Failed to create clip")
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
        self.record_trigger_time = None"""

content = content.replace(old, new)

with open('vision.py', 'w') as f:
    f.write(content)

print("Fixed!")