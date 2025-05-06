#wifi_wab.py

import network
import socket
import time

class WebServer:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.addr = None
        self.sock = None

    def connect_wifi(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            print("Connecting to WiFi...")
            wlan.connect(self.ssid, self.password)
            while not wlan.isconnected():
                time.sleep(0.5)
        print("Connected:", wlan.ifconfig())
        return wlan.ifconfig()[0]

    def start(self):
        ip = self.connect_wifi()
        self.addr = socket.getaddrinfo(ip, 80)[0][-1]
        self.sock = socket.socket()
        self.sock.bind(self.addr)
        self.sock.listen(1)
        print("Web server listening on", self.addr)

    def handle_client(self):
        cl, addr = self.sock.accept()
        print("Client connected from", addr)
        request = cl.recv(1024).decode()

        key = None
        if "keydown" in request:
            if "ArrowUp" in request:
                key = "UP"
            elif "ArrowDown" in request:
                key = "DOWN"
            elif "ArrowLeft" in request:
                key = "LEFT"
            elif "ArrowRight" in request:
                key = "RIGHT"
        elif "keyup" in request:
            key = "STOP"

        response = self.web_page()
        cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
        cl.sendall(response)
        cl.close()

        return key

    def web_page(self):
        return """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>RC Car</title></head>
<body>
<h2>RC카 키보드 제어</h2>
<p>키보드 방향키로 제어하세요.</p>
<script>
document.addEventListener('keydown', function(e) {
    fetch('/?keydown=' + e.key);
});
document.addEventListener('keyup', function(e) {
    fetch('/?keyup=' + e.key);
});
</script>
</body>
</html>"""
