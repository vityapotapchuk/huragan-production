with open('/home/server/vision.py', 'r') as f:
    content = f.read()

old_file = '''    def _serve_file(self, directory, filename):
        path = os.path.join(directory, filename)
        if os.path.exists(path):'''

new_file = '''    def _serve_file(self, directory, filename):
        path = os.path.join(directory, filename)
        if os.path.exists(path):
            self.send_response(200)
            if filename.endswith('.jpg'):
                self.send_header('Content-type', 'image/jpeg')
            elif filename.endswith('.mp4'):
                self.send_header('Content-type', 'video/mp4')
            self.end_headers()
            try:
                with open(path, 'rb') as f:
                    self.wfile.write(f.read())
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_response(404)
            self.end_headers()'''

content = content.replace(old_file, new_file)

with open('/home/server/vision.py', 'w') as f:
    f.write(content)

print('Fixed!')