# wifi_ESP.py

import network
import socket
import time

class wifi_TCP:
    def __init__(self, ssid, password, static_ip, subnet_mask, gateway, dns_server, port=8000):
        self.ssid = ssid
        self.password = password
        self.static_ip = static_ip
        self.subnet_mask = subnet_mask
        self.gateway = gateway
        self.dns_server = dns_server
        self.port = port
        self.addr = None
        self.sock = None
        self.cl = None
        self.recv_buffer = ""

    def connect_wifi(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)

        if not wlan.isconnected():
            print("WiFi 연결 중...")
            wlan.config(dhcp_hostname="my-esp32")
            wlan.ifconfig((self.static_ip, self.subnet_mask, self.gateway, self.dns_server))
            wlan.connect(self.ssid, self.password)

            while not wlan.isconnected():
                time.sleep(0.5)

        print("WiFi 연결 완료:", wlan.ifconfig())
        return wlan.ifconfig()[0]

    def start_server(self):
        ip = self.connect_wifi()
        self.addr = socket.getaddrinfo(ip, self.port)[0][-1]
        self.sock = socket.socket()
        self.sock.bind(self.addr)
        self.sock.listen(1)
        print("TCP 서버 시작:", self.addr)

    def accept_client(self):
        print("클라이언트 연결 대기 중...")
        self.cl, self.addr = self.sock.accept()
        print("클라이언트 연결됨:", self.addr)

    def send_sensor_data(self,sensor_dict):
        """
        센서 데이터를 전송합니다.
        예: {"UL0": 34, "UL1": 50, "IR0": 1}
        전송 문자열: "UL0:34,UL1:50,IR0:1,IR1:0\n"
        """
        try:
            data_str = ",".join([f"{k}:{v}" for k, v in sensor_dict.items()]) + "\n"
            self.cl.send(data_str.encode())
            print("센서 전송:", data_str.strip())
        except Exception as e:
            print("센서 전송 실패:", e)

    def receive_command(self):
        """
        수신 명령 예시: "AUTO,90,60"
        → return ("AUTO", 90, 60)
        """
        try:
            data = self.cl.recv(1024).decode()
            self.recv_buffer += data
            while (self.recv_buffer != ""):
                if "\n" in self.recv_buffer:
                    line, self.recv_buffer = self.recv_buffer.split("\n",1)
                    print("명령 수신:", line.strip())
                    print("buffer =",self.recv_buffer)
                    parts = line.strip().split(",")
                    if len(parts) == 3:
                        mode, servo, speed = parts
            print("part : ",)
            print("bf : ",self.recv_buffer)
            return mode, int(servo), int(speed)
        except Exception as e:
            print("명령 수신 오류:", e)

        return None, None, None

    def close_client(self, cl):
        try:
            self.cl.close()
            print("클라이언트 연결 종료")
        except:
            pass

    def stop_server(self):
        try:
            self.sock.close()
            print("서버 종료")
        except:
            pass

