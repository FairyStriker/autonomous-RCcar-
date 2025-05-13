# RC_GUI.py

import tkinter as tk
import threading
import cv2 # cv2 import 추가 (video_loop 등에서 사용)
from ESP_command import ESP_PC_Network # 명시적 import 권장
from AutoPilot import autopilot # 명시적 import 권장

class RC_GUI:
    def __init__(self, root_window,ip,port):
        self.root = root_window
        self.root.title("RC car System")
        self.root.geometry("300x280") # 높이 약간 조정
        self.root.bind("<KeyPress>", self.key_pressed)
        self.root.bind("<KeyRelease>", self.key_released)
        self.mode = "None"
        self.command = "STOP"
        self.angle = 90
        self.ip = ip
        self.port = port

        self.auto_pilot_thread = None
        self.auto_running = False
        self.video_thread = None
        self.show_video = False
        
        self.cap_resource = None

        self.net = ESP_PC_Network(self.ip,self.port)

        tk.Label(self.root, text="RC카 제어", font=("Arial", 16)).pack(pady=10)

        self.mode_status_label = tk.Label(self.root, text="모드: 선택 안됨", font=("Arial", 12), fg="blue")
        self.mode_status_label.pack(pady=5)

        tk.Button(self.root, text="수동 모드", command=self.set_manual).pack(pady=5)
        tk.Button(self.root, text="자율 주행", command=self.set_auto).pack(pady=5)
        tk.Button(self.root, text="ESP32 상태", command=self.espstate_screen).pack(pady=5)

        # 키보드 조작 안내 레이블 (수동 모드 시 업데이트)
        self.key_info_label = tk.Label(self.root, text="", fg="gray")
        self.key_info_label.pack(pady=5)

        self.update_mode_label() # 초기 모드 레이블 업데이트 (main, esp window 둘다)

    def initialize_autopilot_resource(self):
        if self.cap_resource:
            if hasattr(self.cap_resource, 'cap') and self.cap_resource.cap and self.cap_resource.cap.isOpened():
                print("기존 카메라 리소스 해제 중...")
                self.cap_resource.cap.release()
        
        print("자율주행 리소스 초기화 중...")
        try:
            self.cap_resource = autopilot(0)
            if not hasattr(self.cap_resource, 'cap') or not self.cap_resource.cap.isOpened():
                print("❌ 카메라를 열 수 없습니다. autopilot 객체나 카메라 설정을 확인하세요.")
                self.cap_resource = None # 실패 시 None으로 명확히 설정
                return False
            print("✅ 자율주행 리소스 초기화 완료.")
            return True
        except Exception as e:
            print(f"❌ autopilot 객체 생성 중 오류: {e}")
            self.cap_resource = None
            return False

    def espstate_screen(self):
        if hasattr(self, 'esp_window') and self.esp_window.winfo_exists():
            self.esp_window.lift()
            return

        self.esp_window = tk.Toplevel(self.root)
        self.esp_window.title("ESP32 상태")
        self.esp_window.geometry("300x400")
        self.esp_window.protocol("WM_DELETE_WINDOW", self.on_esp_window_close)

        tk.Label(self.esp_window, text="ESP32 상태", font=("Arial", 16)).pack(pady=10)
        self.mode_status_label2 = tk.Label(self.esp_window, text="모드: 선택 안됨", font=("Arial", 12), fg="blue")
        self.mode_status_label2.pack(pady=5)

        self.sensor_label = tk.Label(self.esp_window, text="센서 데이터 없음", font=("Arial", 10), fg="black", justify="left")
        self.sensor_label.pack(pady=5)

        # 버튼 텍스트 변경: "Cam 영상 보기" -> "자율주행 영상 보기/숨기기"
        tk.Button(self.esp_window, text="자율주행 영상 보기/숨기기", command=self.toggle_autopilot_video).pack(pady=10)

        self.cap_label = tk.Label(self.esp_window, text="", fg="gray")
        self.cap_label.pack(pady=5)
        
        self.update_mode_label() # ESP 창의 모드 레이블도 업데이트
        self.update_sensor_data()

    def on_esp_window_close(self):
        if self.show_video:
            self.stop_video_loop()
        if hasattr(self, 'esp_window') and self.esp_window.winfo_exists():
            self.esp_window.destroy()

    def update_sensor_data(self):
        if hasattr(self, 'esp_window') and self.esp_window.winfo_exists(): # 창 존재 여부 확인
            sensor_text = ""
            try:
                raw_data = self.net.receive_sensor_data()
                if raw_data:
                    for sensor_num, sensor_value in raw_data.items():
                        sensor_text += f"{sensor_num}: {sensor_value}\n"
                    self.sensor_label.config(text=sensor_text.strip())
                    # print("수신된 센서 데이터:\n", sensor_text.strip()) # 디버깅 시 활성화
                else:
                    self.sensor_label.config(text="센서 데이터 없음 (수신 데이터 없음)")
            except Exception as e:
                print("센서 수신 오류:", e)
                self.sensor_label.config(text="센서 데이터 수신 오류")
            
            self.esp_window.after(1000, self.update_sensor_data)

    def update_mode_label(self):
        text, color = "", "blue" # 기본값 설정
        key_info_text = ""

        if self.mode == "manual":
            text, color = "모드: 수동 모드", "green"
            key_info_text = "방향키로 조작 가능"
        elif self.mode == "auto":
            text, color = "모드: 자율 주행 중", "orange"
        elif self.mode == "park":
            text, color = "모드: 자동 주차 중", "purple" # 오타 수정: "purpre" -> "purple"
        else: # "None" 또는 기타 상태
            text = "모드: 선택 안됨"
        
        self.key_info_label.config(text=key_info_text)
        self.mode_status_label.config(text=text, fg=color)

        if hasattr(self, 'mode_status_label2') and self.mode_status_label2.winfo_exists():
            self.mode_status_label2.config(text=text, fg=color)
            
    def key_pressed(self, event):
        key = event.keysym
        if self.mode != "manual":
            return

        # 현재 command와 angle 상태를 기준으로 새 값을 결정
        new_command = self.command
        new_angle = self.angle

        if key == 'Up':
            new_command = "FWD"
        elif key == 'Down':
            new_command = "BACK"
        elif key == 'Left':
            new_angle = min(135, self.angle + 15)
        elif key == 'Right':
            new_angle = max(45, self.angle - 15)
        else: # 다른 키 입력은 무시
            return

        # 실제 상태 변경이 있을 때만 전송하고 self 값 업데이트
        if new_command != self.command or new_angle != self.angle:
            self.command = new_command
            self.angle = new_angle
            cmd_to_send = f"{self.command},{self.angle},100" # 예시: 속도 100
            try:
                self.net.send_command(cmd_to_send)
                print(f"Sent: {cmd_to_send}")
            except Exception as e:
                print("❌ 전송 오류 (key_pressed):", e)
                self.net.reconnect() # 예시: 재연결 시도

    def key_released(self, event):
        if self.mode != "manual":
            return
        
        # 전진 또는 후진 키를 뗄 때만 STOP (좌우 방향키는 각도만 유지)
        if event.keysym in ['Up', 'Down']:
            self.command = "STOP"
            # 현재 angle 값은 유지하고 속도만 0으로
            cmd_to_send = f"{self.command},{self.angle},0"
            try:
                self.net.send_command(cmd_to_send)
                print(f"Sent: {cmd_to_send}")
            except Exception as e:
                print("❌ 전송 오류 (key_released):", e)
                self.net.reconnect()

    def stop_current_operations(self):
        if self.auto_running:
            print("자율 주행 중지 요청...")
            self.auto_running = False
            if self.auto_pilot_thread and self.auto_pilot_thread.is_alive():
                self.auto_pilot_thread.join(timeout=1)
            if self.auto_pilot_thread and self.auto_pilot_thread.is_alive(): # 아직 살아있다면 강제 종료 고려 (위험)
                print("⚠️ 자율주행 스레드가 시간 내에 종료되지 않았습니다.")
            self.auto_pilot_thread = None # 스레드 객체 참조 제거
            print("자율 주행 중지됨.")

        if self.show_video:
            self.stop_video_loop() # 비디오 루프도 중지

        if self.cap_resource:
            if hasattr(self.cap_resource, 'cap') and self.cap_resource.cap and self.cap_resource.cap.isOpened():
                print("카메라 리소스 해제 중...")
                self.cap_resource.cap.release()
            # self.cap_resource = None # 필요시 None으로 설정하여 다음 auto 모드에서 확실히 새로 생성하도록 유도

    def set_manual(self):
        self.stop_current_operations()
        self.mode = "manual"
        # 수동 모드 진입 시 RC카에 정지 명령 전송 (안전을 위해)
        self.angle = 90
        cmd_stop = f"STOP,{self.angle},0"
        try:
            self.net.send_command(cmd_stop)
        except Exception as e:
            print(f"❌ 수동 모드 전환 중 정지 명령 전송 오류: {e}")
            # self.net.reconnect() # 필요시
        self.update_mode_label()
        print("수동 모드로 전환됨.")

    def set_auto(self):
        self.stop_current_operations() # 이전 작업 정리
        self.mode = "auto" # 모드 우선 설정
        self.update_mode_label() # 레이블 업데이트
        
        if not self.initialize_autopilot_resource():
            # 실패 메시지는 initialize_autopilot_resource 내부에서 처리하거나 여기서 추가 처리
            self.mode_status_label.config(text="모드: 자율주행 실패 (카메라)", fg="red")
            if hasattr(self, 'mode_status_label2') and self.mode_status_label2.winfo_exists():
                 self.mode_status_label2.config(text="모드: 자율주행 실패 (카메라)", fg="red")
            self.mode = "None" # 실패 시 모드 초기화
            self.update_mode_label() # 초기화된 모드로 레이블 다시 업데이트
            return

        # auto_running 플래그는 스레드 시작 직전에 True로 설정
        if not self.auto_running: # 스레드가 이미 실행 중이지 않을 때
            self.auto_running = True
            self.auto_pilot_thread = threading.Thread(target=self.run_autopilot, daemon=True)
            self.auto_pilot_thread.start()
            print("자율 주행 모드로 전환됨. 스레드 시작.")
        else:
            # 이 경우는 stop_current_operations에서 auto_running이 False로 설정되지 않았거나
            # 스레드가 정상 종료되지 않은 예외적인 상황일 수 있음.
            print("⚠️ 자율 주행이 이미 실행 중이거나 플래그 오류. (auto_running이 True)")


    def run_autopilot(self):
        print("자율 주행 스레드 시작됨.")
        if not (self.cap_resource and hasattr(self.cap_resource, 'cap') and self.cap_resource.cap.isOpened()):
            print("❌ run_autopilot: 카메라가 준비되지 않았습니다.")
            self.auto_running = False # 스레드 실행 조건 False로 변경
            # GUI 스레드에서 레이블 업데이트
            self.root.after(0, lambda: self.mode_status_label.config(text="모드: 자율주행 실패 (카메라)", fg="red"))
            if hasattr(self, 'mode_status_label2') and self.mode_status_label2.winfo_exists():
                 self.root.after(0, lambda: self.mode_status_label2.config(text="모드: 자율주행 실패 (카메라)", fg="red"))
            return
        
        while self.auto_running and self.mode == "auto": # self.auto_running 플래그 확인
            ret, frame = self.cap_resource.cap.read() # 수정: self.cap -> self.cap_resource
            if not ret:
                print("⚠️ 자율 주행 중 프레임을 읽을 수 없습니다. 루프를 중단합니다.")
                self.auto_running = False # 플래그 변경하여 루프 종료 유도
                break 
            
            try:
                _, angle = self.cap_resource.process_frame(frame)
                servo_angle = max(45, min(135, int(90 + angle)))
                
                # 실제 상태 변경이 있을 때만 전송하고 self 값 업데이트
                if servo_angle != self.angle:
                    self.angle = servo_angle
                    cmd_to_send = f"FWD,{self.angle},100" # 예시: 속도 100
                    try:
                        self.net.send_command(cmd_to_send)
                        print(f"Sent: {cmd_to_send}")
                    except Exception as e:
                        print("❌ 전송 오류 (key_pressed):", e)
                        self.net.reconnect() # 예시: 재연결 시도

            except Exception as e:
                print(f"❌ 자율 주행 중 알 수 없는 오류: {e}")
                # 연속 오류 시 루프 중단을 위한 카운터 등을 추가할 수 있음
                cv2.waitKey(10) # 짧은 지연으로 CPU 과부하 방지
                self.auto_running = False # 심각한 오류 시 루프 중단
                break

        print("자율주행 스레드 루프 종료.")
        # 스레드 종료 시 auto_running 플래그는 이미 False이거나 외부에서 False로 설정됨.
        # 카메라 자원 해제는 stop_current_operations에서 처리.

    def toggle_autopilot_video(self):
        # 버튼 이름이 "자율주행 영상 보기/숨기기"이므로, 현재 상태에 따라 토글
        if self.mode != "auto":
            print("자율 주행 모드에서만 영상을 볼 수 있습니다.")
            if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
                 self.cap_label.config(text="자율 주행 모드에서만 영상 확인 가능")
            return

        if not self.show_video: # 현재 영상이 꺼져있다면 -> 켜기
            self.start_video_loop()
        else: # 현재 영상이 켜져있다면 -> 끄기
            self.stop_video_loop()

    def start_video_loop(self):
        if self.mode != "auto" or not self.auto_running: # 자율주행 중일때만 영상 표시
            print("비디오 시작 실패: 자율 주행 중이 아닙니다.")
            return

        if not (self.cap_resource and hasattr(self.cap_resource, 'cap') and self.cap_resource.cap.isOpened()):
            print("❌ 비디오 루프: 카메라가 준비되지 않았습니다.")
            if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
                self.cap_label.config(text="카메라 준비 안됨")
            return

        self.show_video = True
        # 스레드가 없거나, 있어도 죽은 상태면 새로 생성
        if self.video_thread is None or not self.video_thread.is_alive():
            self.video_thread = threading.Thread(target=self.video_loop_run, daemon=True)
            self.video_thread.start()
            if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
                # Tkinter GUI 업데이트는 메인 스레드에서 하도록 예약
                self.root.after(0, lambda: self.cap_label.config(text="영상 로딩 중... (Q: 종료)"))
        print("비디오 루프 시작 요청됨.")



    def stop_video_loop(self):
        # 이 함수는 주로 외부(버튼 클릭, 모드 변경 등)에서 비디오 종료를 요청할 때 사용됨
        if self.show_video: # 영상이 현재 켜져있다고 판단될 때만 실행
            print("비디오 루프 중지 요청 (stop_video_loop).")
            self.show_video = False # video_loop_run 스레드의 루프 종료 유도

            # video_loop_run 스레드가 스스로 창을 닫고 종료할 것이므로,
            # 여기서는 스레드가 안전하게 종료될 시간을 기다리는 것이 주 목적.
            if self.video_thread and self.video_thread.is_alive():
                print(f"비디오 스레드 ({self.video_thread.name}) 종료 대기 중...")
                self.video_thread.join(timeout=2.0) # 타임아웃을 조금 늘려 스레드가 정리할 시간을 줌
                if self.video_thread.is_alive():
                    print(f"⚠️ 비디오 스레드가 {self.video_thread.name} 시간 내에 완전 종료되지 않았습니다.")
                else:
                    print(f"비디오 스레드 ({self.video_thread.name}) 정상 종료 확인됨.")
            # cleanup_video_resources는 video_loop_run의 finally에서 self.root.after로 호출됨
            # 여기서는 호출하지 않아도 될 수 있지만, 만약을 위해 호출하거나 cleanup_video_resources 내부에서 중복 방지
            # self.cleanup_video_resources() # 중복 호출될 수 있으므로 주의
        else:
            # 영상이 이미 꺼져있거나(self.show_video == False), 스레드가 없는 경우
            # print("비디오가 이미 꺼져있거나 스레드가 없습니다. 추가 정리 시도.")
            self.cleanup_video_resources() # 스레드 객체 등이 남아있을 수 있으므로 정리 시도

    def video_loop_run(self):
        print("비디오 루프 스레드 시작됨.")
        window_name = "Autopilot View" # 창 이름을 변수로 관리

        if not (self.cap_resource and hasattr(self.cap_resource, 'cap') and self.cap_resource.cap.isOpened()):
            print("❌ video_loop_run: 카메라가 준비되지 않았습니다.")
            self.show_video = False # 플래그 업데이트
            if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
                self.root.after(0, lambda: self.cap_label.config(text="카메라 오류"))
            # 스레드 종료 시 stop_video_loop를 호출하여 self.video_thread를 None으로 설정하도록 유도
            self.root.after(0, self.cleanup_video_resources)
            return

        try:
            while self.show_video and self.auto_running and self.mode == "auto":
                ret, frame = self.cap_resource.cap.read()
                if not ret:
                    print("⚠️ 비디오 루프: 프레임 읽기 실패.")
                    cv2.waitKey(100) # 장치에 따라 잠시 대기 후 재시도
                    continue
                
                try:
                    processed_frame, _ = self.cap_resource.process_frame(frame)
                    cv2.imshow(window_name, processed_frame)
                except AttributeError: # process_frame이 없는 경우 등
                    cv2.imshow(window_name, frame) # 원본 프레임이라도 표시
                except Exception as e:
                    print(f"비디오 프레임 처리/표시 중 오류: {e}")

                if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
                    if not self.cap_label.cget("text").startswith("Q를 눌러"):
                        self.root.after(0, lambda: self.cap_label.config(text="Q를 눌러 카메라 종료"))

                key = cv2.waitKey(1) & 0xFF # imshow 후에는 항상 waitKey 필요
                if key == ord('q'):
                    print("Q키 입력으로 비디오 종료 요청됨.")
                    self.show_video = False # 루프 종료 조건 변경
                    # Q키로 종료 시 stop_video_loop를 호출하여 모든 정리 절차를 따르도록 함
                    # self.root.after(0, self.stop_video_loop) # 이렇게 하면 stop_video_loop가 두 번 불릴 수 있음
                                                            # (한번은 Q로, 한번은 루프 종료 후 finally에서)
                                                            # 그냥 show_video = False로 두고 루프 자연 종료 유도
                    break 
            
        finally: # 루프가 정상적으로 종료되거나 (show_video = False), break로 빠져나오거나, 예외 발생 시
            print(f"비디오 루프 스레드 '{window_name}' 종료 수순 시작 (show_video: {self.show_video}).")
            # 이 스레드에서 창을 닫도록 하거나, 메인 스레드에 요청
            # self.root.after(0, self.destroy_opencv_window, window_name)
            # 위 방법이 더 안전하지만, 일단은 직접 닫아보고 문제 발생 시 위 코드로 변경
            try:
                if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) >= 1:
                    cv2.destroyWindow(window_name)
                    print(f"'{window_name}' 창이 비디오 스레드에서 닫힘.")
            except cv2.error as e:
                # 창이 이미 다른 곳에서 닫혔거나 존재하지 않을 수 있음
                # print(f"'{window_name}' 창 닫기 시도 중 오류 (무시 가능): {e}")
                pass
            
            # 스레드 종료 후 관련 리소스 정리 함수 호출 예약
            self.root.after(0, self.cleanup_video_resources)


    def cleanup_video_resources(self):
        """비디오 관련 스레드 객체 및 GUI 요소를 정리합니다."""
        # print("비디오 리소스 정리 시작...") # 디버깅용

        # OpenCV 창은 video_loop_run의 finally에서 닫히도록 시도함
        # 여기서는 주로 스레드 객체 참조와 Tkinter 레이블을 정리
        current_thread_name = self.video_thread.name if self.video_thread else "N/A"

        if self.video_thread and self.video_thread.is_alive():
            # 아직 스레드가 살아있다면 join을 시도 (이론상 여기까지 오면 스레드는 종료되었어야 함)
            # print(f"Cleanup: 비디오 스레드 ({current_thread_name})가 아직 살아있어 join 시도.")
            self.video_thread.join(timeout=0.5) # 짧은 추가 대기
            if self.video_thread.is_alive():
                 print(f"⚠️ Cleanup: 비디오 스레드 ({current_thread_name})가 여전히 종료되지 않음.")
                 # 이 경우, 스레드가 멈춘 것일 수 있으므로 강제 종료는 위험. 로그만 남김.

        self.video_thread = None # 스레드 객체 참조 제거
        self.show_video = False  # 확실히 플래그를 False로 설정 (중복일 수 있으나 안전을 위해)

        if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
            self.cap_label.config(text="") # 레이블 초기화
        
        # print(f"비디오 리소스 정리 완료 (이전 스레드: {current_thread_name}).")
