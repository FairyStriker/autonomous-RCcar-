# ESP_command.py

import socket
import json # 센서 데이터 파싱을 위해 (ESP32가 JSON 형식으로 보낸다고 가정)
import time # 짧은 지연 등을 위해 사용될 수 있음

class ESP_PC_Network:
    def __init__(self, ip, port, timeout=0.5): # 기본 타임아웃 0.5초
        self.ip = ip
        self.port = port
        self.socket = None  # 초기에는 None으로 설정
        self.recv_buffer = ""
        self.timeout = timeout
        self.connect() # 생성 시 연결 시도

    def connect(self):
        """ESP32와 연결을 시도합니다."""
        try:
            self.close_socket_gracefully() # 기존 연결이 있다면 정리
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout) # ★★★ 연결 시도 전 타임아웃 설정 ★★★
            print(f"ESP32 연결 시도 중... ({self.ip}:{self.port}, timeout={self.timeout}s)")
            self.socket.connect((self.ip, self.port))
            print(f"✅ RC카(ESP32)와 연결 완료 ({self.ip}:{self.port})")
            return True
        except socket.timeout:
            print(f"❌ 연결 시간 초과 (timeout={self.timeout}s): {self.ip}:{self.port}")
            self.socket = None # 연결 실패 시 소켓 객체를 None으로 명확히 함
            return False
        except Exception as e:
            print(f"❌ 연결 실패: {e} ({self.ip}:{self.port})")
            self.socket = None
            return False

    def send_command(self, cmd):
        """RC카에 명령을 전송합니다."""
        if not self.socket:
            print(f"명령 '{cmd.strip()}' 전송 실패: 연결되지 않았습니다.")
            # 재연결을 시도할 수 있지만, 호출하는 쪽에서 상태를 보고 결정하는 것이 좋을 수 있음
            # if not self.reconnect():
            #     return False
            return False # 연결 안되어 있으면 실패 반환

        try:
            if not cmd.endswith("\n"):
                cmd += "\n"
            self.socket.sendall(cmd.encode('utf-8')) # 인코딩 명시
            # RC_GUI 클래스에서 이미 전송 로그를 출력하므로 여기서는 생략하거나 상세 로깅 시 사용
            # print(f"데이터 전송: {cmd.strip()}")
            return True
        except socket.timeout:
            print(f"명령 '{cmd.strip()}' 전송 시간 초과.")
            self.close_socket_gracefully() # 통신 문제 발생 시 소켓 정리
            return False
        except OSError as e: # sendall에서 발생할 수 있는 소켓 관련 오류 (예: Broken pipe)
             print(f"명령 '{cmd.strip()}' 전송 중 OS 오류: {e}")
             self.close_socket_gracefully()
             return False
        except Exception as e:
            print(f"명령 '{cmd.strip()}' 전송 중 예기치 않은 오류: {e}")
            self.close_socket_gracefully()
            return False


    def receive_data(self): # 이 함수는 현재 RC_GUI에서 사용되지 않지만, 타임아웃 처리를 추가한다면:
        """일반 데이터 수신 (현재 RC_GUI에서는 직접 사용 안 함)"""
        if not self.socket:
            return None
        try:
            data_bytes = self.socket.recv(1024) # 타임아웃 적용됨
            if not data_bytes:
                self.close_socket_gracefully()
                return None
            return data_bytes.decode('utf-8')
        except socket.timeout:
            return None
        except Exception as e:
            print(f"일반 데이터 수신 오류: {e}")
            # self.close_socket_gracefully() # 오류 성격에 따라
            return None

    def reconnect(self):
        """ESP32와 재연결을 시도합니다."""
        print("ESP32와 재연결 시도...")
        return self.connect() # connect 메소드가 이미 정리 및 연결 로직을 포함

    def close_socket_gracefully(self):
        """소켓 연결을 안전하게 종료하고 리소스를 정리합니다."""
        if self.socket:
            # print("소켓 연결 정리 중...")
            try:
                # SHUT_RDWR: 읽기/쓰기 모두 중단 알림 (상대방에게 FIN 패킷 전송)
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                # 이미 닫혔거나, 연결되지 않은 소켓 등에서 발생 가능
                pass
            finally:
                self.socket.close() # 소켓 리소스 반환
        self.socket = None # 참조 제거

    def close(self):
        """외부에서 호출하여 명시적으로 연결을 종료합니다."""
        print("외부 요청으로 ESP32 연결 종료 중...")
        self.close_socket_gracefully()
