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

    def receive_sensor_data(self):
        """RC카로부터 센서 데이터를 수신하고 파싱합니다."""
        if not self.socket:
            # print("센서 데이터 수신 실패: 연결되지 않았습니다.") # 너무 자주 호출될 수 있으므로 주석 처리
            return None

        try:
            # recv는 타임아웃의 영향을 받음 (__init__ 또는 connect에서 설정)
            data_bytes = self.socket.recv(128) # 수신 버퍼 크기 (64에서 약간 늘림)

            if not data_bytes: # 상대방 소켓이 정상적으로 닫힌 경우 (EOF)
                print("ESP32 연결이 종료된 것 같습니다 (데이터 없음 수신).")
                self.close_socket_gracefully()
                return None

            try:
                data_chunk = data_bytes.decode('utf-8')
                self.recv_buffer += data_chunk
            except UnicodeDecodeError:
                print(f"데이터 디코딩 오류. 수신된 바이트: {data_bytes}")
                # 문제가 있는 부분만 버퍼에서 제거하거나, 버퍼를 비울 수 있음
                # 여기서는 일단 해당 청크는 무시하고 진행
                return None # 또는 이전까지의 유효한 데이터만 처리

            # 완성된 라인(들) 처리 (개행 문자를 메시지 구분자로 사용)
            if "\n" in self.recv_buffer:
                line, self.recv_buffer = self.recv_buffer.split("\n", 1)
                if line: # 빈 줄이 아닐 경우에만 파싱
                    print(f"수신된 라인(파싱 전): '{line.strip()}'") # 디버깅용
                    parsed_data = self.parse_sensor_data(line)
                    return parsed_data
                else: # 빈 줄이 메시지로 온 경우 (거의 없음)
                    return None
            else:
                # 아직 완전한 메시지(라인)가 없음
                return None

        except socket.timeout:
            # print("센서 데이터 수신 시간 초과.") # 이 메시지는 매우 빈번하게 발생하므로 주석 처리 권장
            return None # 타임아웃 시 None을 반환하여 GUI가 멈추지 않도록 함
        except ConnectionResetError:
            print("ESP32에 의해 연결이 재설정되었습니다 (ConnectionResetError).")
            self.close_socket_gracefully()
            return None
        except OSError as e: # recv에서 발생할 수 있는 소켓 관련 오류
             print(f"센서 데이터 수신 중 OS 오류: {e}")
             self.close_socket_gracefully()
             return None
        except Exception as e:
            print(f"센서 데이터 수신 중 예기치 않은 오류: {e}")
            # 오류의 심각성에 따라 소켓을 닫을지 결정
            # self.close_socket_gracefully()
            return None

    def parse_sensor_data(self, data_line):
        """
        수신된 한 줄의 문자열 데이터를 파싱하여 딕셔너리로 반환합니다.
        예시 데이터 형식: "ULTRA:25,IR:1"
        반환 형식: { "ultra": 25, "ir": 1 }
        """
        data_line = data_line.strip()
        if not data_line: # 빈 문자열이면 None 반환
            return None

        sensor_dict = {}
        try:
            parts = data_line.split(',')
            for part in parts:
                if ':' not in part:
                    # print(f"파싱 오류: 형식에 맞지 않음 (':' 없음) - '{part}' in '{data_line}'")
                    continue # 형식에 맞지 않는 부분은 건너뜀

                key, value = part.split(':', 1) # 값 부분에 ':'이 포함될 수 있으므로 maxsplit=1
                key = key.strip().lower()
                value = value.strip()

                try:
                    sensor_dict[key] = int(value) # 정수 변환 시도
                except ValueError:
                    # 정수 변환 실패 시 원본 문자열 값 또는 다른 특정 값으로 저장 (예: 부동소수점 시도)
                    try:
                        sensor_dict[key] = float(value)
                    except ValueError:
                        # print(f"파싱 경고: 숫자 변환 실패 - 키 '{key}', 값 '{value}'")
                        sensor_dict[key] = value # 최후에는 문자열로 저장
            return sensor_dict if sensor_dict else None # 빈 딕셔너리도 유효할 수 있으나, 여기서는 파싱된게 없으면 None
        except Exception as e:
            print(f"데이터 파싱 중 예외 발생 ('{data_line}'): {e}")
            return None


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
