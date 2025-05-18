# RC_GUI.py

import tkinter as tk
import threading
import cv2
import time # parking_logic 에서 사용하므로 import
from ESP_command import ESP_PC_Network
from AutoPilot import autopilot
from parking_logic import AutoParking # 제공해주신 주차 로직 임포트
from parking_logic import PARKING_STEP_SEARCHING, PARKING_STEP_COMPLETE, PARKING_STEP_FAILED, PARKING_STEP_ABORT # 상태값 임포트


class RC_GUI:
    def __init__(self, root_window,ip,port,url=0):
        self.root = root_window
        self.root.title("RC car System")
        self.root.geometry("300x320")
        self.root.bind("<KeyPress>", self.key_pressed)
        self.root.bind("<KeyRelease>", self.key_released)
        self.mode = "None"
        self.command = "STOP"
        self.angle = 90
        self.ip = ip
        self.port = port
        self.url = url

        self.auto_pilot_thread = None
        self.auto_running = False
        self.parking_thread = None
        self.parking_in_progress = False

        self.video_thread = None
        self.show_video = False
        
        self.cap_resource = None
        self.net = ESP_PC_Network(self.ip,self.port)
        self.auto_parker = AutoParking(self.net) # AutoParking 객체 초기화


        tk.Label(self.root, text="RC카 제어", font=("Arial", 16)).pack(pady=10)

        self.mode_status_label = tk.Label(self.root, text="모드: 선택 안됨", font=("Arial", 12), fg="blue")
        self.mode_status_label.pack(pady=5)

        tk.Button(self.root, text="수동 모드", command=self.set_manual).pack(pady=5)
        tk.Button(self.root, text="자율 주행", command=self.set_auto).pack(pady=5)
        tk.Button(self.root, text="자동 주차", command=self.set_parking).pack(pady=5)
        tk.Button(self.root, text="ESP32 상태", command=self.espstate_screen).pack(pady=5)

        self.key_info_label = tk.Label(self.root, text="", fg="gray")
        self.key_info_label.pack(pady=5)

        self.update_mode_label()

    def initialize_autopilot_resource(self):
        if self.cap_resource:
            if hasattr(self.cap_resource, 'cap') and self.cap_resource.cap and self.cap_resource.cap.isOpened():
                print("기존 카메라 리소스 해제 중...")
                self.cap_resource.cap.release()
        
        print("자율주행/주차 리소스 초기화 중...")
        try:
            self.cap_resource = autopilot(self.url) 
            if not hasattr(self.cap_resource, 'cap') or not self.cap_resource.cap.isOpened():
                print("❌ 카메라를 열 수 없습니다. autopilot 객체나 카메라 설정을 확인하세요.")
                self.cap_resource = None
                return False
            print("✅ 자율주행/주차 리소스 초기화 완료.")
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
        
        tk.Button(self.esp_window, text="자율주행/주차 영상 보기/숨기기", command=self.toggle_operation_video).pack(pady=10)

        self.cap_label = tk.Label(self.esp_window, text="", fg="gray")
        self.cap_label.pack(pady=5)
        
        self.update_mode_label() 
        self.update_sensor_data()

    def on_esp_window_close(self):
        if self.show_video:
            self.stop_video_loop()
        if hasattr(self, 'esp_window') and self.esp_window.winfo_exists():
            self.esp_window.destroy()

    def update_sensor_data(self):
        if hasattr(self, 'esp_window') and self.esp_window.winfo_exists(): 
            sensor_text = ""
            try:
                # ESP_PC_Network의 receive_sensor_data가 파싱된 딕셔너리를 반환한다고 가정
                raw_data = self.net.receive_sensor_data() 
                if raw_data:
                    # parking_logic.py에서 정의한 키들이 있는지 확인하고 표시
                    # 예시: FRONT_RIGHT_DIAG_ULTRA_KEY, IR_REAR_LEFT_KEY, IR_REAR_RIGHT_KEY
                    # 실제 `raw_data`의 키값에 맞춰서 아래 코드를 수정해야 합니다.
                    # from parking_logic import FRONT_RIGHT_DIAG_ULTRA_KEY, IR_REAR_LEFT_KEY, IR_REAR_RIGHT_KEY
                    # sensor_text += f"{FRONT_RIGHT_DIAG_ULTRA_KEY}: {raw_data.get(FRONT_RIGHT_DIAG_ULTRA_KEY, 'N/A')}\n"
                    # sensor_text += f"{IR_REAR_LEFT_KEY}: {raw_data.get(IR_REAR_LEFT_KEY, 'N/A')}\n"
                    # sensor_text += f"{IR_REAR_RIGHT_KEY}: {raw_data.get(IR_REAR_RIGHT_KEY, 'N/A')}\n"
                    # sensor_text += "-----\n" # 구분선
                    for sensor_num, sensor_value in raw_data.items():
                        sensor_text += f"{sensor_num}: {sensor_value}\n"
                    self.sensor_label.config(text=sensor_text.strip())
                else:
                    self.sensor_label.config(text="센서 데이터 없음 (수신 데이터 없음)")
            except Exception as e:
                print("센서 수신 오류:", e)
                self.sensor_label.config(text="센서 데이터 수신 오류")
            
            if hasattr(self, 'esp_window') and self.esp_window.winfo_exists(): # 창 닫힌 후 after 콜백 방지
                self.esp_window.after(100, self.update_sensor_data)


    def update_mode_label(self):
        text, color = "", "blue"
        key_info_text = ""

        if self.mode == "manual":
            text, color = "모드: 수동 모드", "green"
            key_info_text = "방향키로 조작 가능"
        elif self.mode == "auto":
            text, color = "모드: 자율 주행 중", "orange"
        elif self.mode == "park":
            parking_status_text = ""
            if hasattr(self, 'auto_parker') and self.auto_parker:
                 parking_status_text = f" ({self.auto_parker.current_parking_step})"
            text, color = f"모드: 자동 주차 중{parking_status_text}", "purple"
        else: 
            text = "모드: 선택 안됨"
        
        self.key_info_label.config(text=key_info_text)
        self.mode_status_label.config(text=text, fg=color)

        if hasattr(self, 'mode_status_label2') and self.mode_status_label2.winfo_exists():
            self.mode_status_label2.config(text=text, fg=color)
            
    def key_pressed(self, event):
        key = event.keysym
        if self.mode != "manual":
            return

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
        else: 
            return

        if new_command != self.command or new_angle != self.angle:
            self.command = new_command
            self.angle = new_angle
            cmd_to_send = f"{self.command},{self.angle},100" 
            try:
                self.net.send_command(cmd_to_send)
                # print(f"Sent: {cmd_to_send}") # 로그 너무 많음
            except Exception as e:
                print("❌ 전송 오류 (key_pressed):", e)
                self.net.reconnect() 

    def key_released(self, event):
        if self.mode != "manual":
            return
        
        if event.keysym in ['Up', 'Down']:
            self.command = "STOP"
            cmd_to_send = f"{self.command},{self.angle},0"
            try:
                self.net.send_command(cmd_to_send)
                # print(f"Sent: {cmd_to_send}") # 로그 너무 많음
            except Exception as e:
                print("❌ 전송 오류 (key_released):", e)
                self.net.reconnect()

    def stop_current_operations(self, stop_rc_car=True): # RC카 정지 여부 인자 추가
        if self.auto_running:
            print("자율 주행 중지 요청...")
            self.auto_running = False
            if self.auto_pilot_thread and self.auto_pilot_thread.is_alive():
                self.auto_pilot_thread.join(timeout=1)
            self.auto_pilot_thread = None 
            print("자율 주행 중지됨.")

        if self.parking_in_progress:
            print("자동 주차 중지 요청...")
            self.parking_in_progress = False
            if self.parking_thread and self.parking_thread.is_alive():
                self.parking_thread.join(timeout=1)
            self.parking_thread = None
            if self.auto_parker: # AutoParking 객체가 있다면 상태 리셋
                self.auto_parker.reset_parking_state()
            print("자동 주차 중지됨.")

        if self.show_video:
            self.stop_video_loop() 

        if self.cap_resource:
            if hasattr(self.cap_resource, 'cap') and self.cap_resource.cap and self.cap_resource.cap.isOpened():
                print("카메라 리소스 해제 중...")
                self.cap_resource.cap.release()
        
        if stop_rc_car: # RC카 정지 명령 (필요한 경우에만)
            try:
                cmd_stop = f"STOP,90,0"
                self.net.send_command(cmd_stop)
                print("RC카 정지 명령 전송 (stop_current_operations)")
            except Exception as e:
                print(f"❌ 정지 명령 전송 오류 (stop_current_operations): {e}")


    def set_manual(self):
        self.stop_current_operations() # 모든 작업 중지 및 RC카 정지
        self.mode = "manual"
        self.angle = 90
        # stop_current_operations 에서 이미 정지 명령을 보냄
        # cmd_stop = f"STOP,{self.angle},0"
        # try:
        #     self.net.send_command(cmd_stop)
        # except Exception as e:
        #     print(f"❌ 수동 모드 전환 중 정지 명령 전송 오류: {e}")
        self.update_mode_label()
        print("수동 모드로 전환됨.")

    def set_auto(self):
        self.stop_current_operations() 
        self.mode = "auto" 
        self.update_mode_label() 
        
        if not self.initialize_autopilot_resource():
            self.mode_status_label.config(text="모드: 자율주행 실패 (카메라)", fg="red")
            if hasattr(self, 'mode_status_label2') and self.mode_status_label2.winfo_exists():
                 self.mode_status_label2.config(text="모드: 자율주행 실패 (카메라)", fg="red")
            self.mode = "None" 
            self.update_mode_label() 
            return

        if not self.auto_running: 
            self.auto_running = True
            self.auto_pilot_thread = threading.Thread(target=self.run_autopilot, daemon=True)
            self.auto_pilot_thread.start()
            print("자율 주행 모드로 전환됨. 스레드 시작.")
        else:
            print("⚠️ 자율 주행이 이미 실행 중이거나 플래그 오류. (auto_running이 True)")


    def run_autopilot(self):
        print("자율 주행 스레드 시작됨.")
        if not (self.cap_resource and hasattr(self.cap_resource, 'cap') and self.cap_resource.cap.isOpened()):
            print("❌ run_autopilot: 카메라가 준비되지 않았습니다.")
            self.auto_running = False 
            self.root.after(0, lambda: self.mode_status_label.config(text="모드: 자율주행 실패 (카메라)", fg="red"))
            if hasattr(self, 'mode_status_label2') and self.mode_status_label2.winfo_exists():
                 self.root.after(0, lambda: self.mode_status_label2.config(text="모드: 자율주행 실패 (카메라)", fg="red"))
            return
        
        p_sign_detected_once = False 

        while self.auto_running and self.mode == "auto": 
            ret, frame = self.cap_resource.cap.read() 
            if not ret:
                print("⚠️ 자율 주행 중 프레임을 읽을 수 없습니다. 루프를 중단합니다.")
                self.auto_running = False 
                break 
            
            try:
                processed_frame, angle_deg, p_detected = self.cap_resource.process_frame(frame, current_mode="auto")

                if p_detected and not p_sign_detected_once:
                    p_sign_detected_once = True 
                    print("🅿️ P 표지판 감지! 자동 주차 모드로 전환합니다. (자율 주행 중)")
                    self.root.after(0, self.set_parking_after_p_detection) # GUI 변경 및 스레드 시작은 메인 스레드에서
                    # 자율 주행 스레드는 여기서 종료되어야 함
                    self.auto_running = False # 현재 자율주행 스레드 종료 플래그
                    break # P 감지 후 자율주행 루프 즉시 탈출


                servo_angle = max(45, min(135, int(90 + angle_deg))) 
                
                if servo_angle != self.angle: # 각도 변경 시에만 전송 (FWD 유지)
                    self.angle = servo_angle
                    # 자율 주행 중에는 계속 FWD 유지, 각도만 변경
                    cmd_to_send = f"FWD,{self.angle},80" # 예시: 속도 80 (튜닝 필요)
                    try:
                        self.net.send_command(cmd_to_send)
                    except Exception as e:
                        print("❌ 전송 오류 (run_autopilot):", e)
                
                time.sleep(0.05) # CPU 사용량 줄이기 위한 짧은 대기 (0.05초 = 20 FPS 가정)


            except Exception as e:
                print(f"❌ 자율 주행 중 알 수 없는 오류: {e}")
                self.auto_running = False 
                break

        if not p_sign_detected_once: # P 표지판 못 찾고 루프 종료 시
             print("자율주행 스레드 루프 종료 (P 표지판 미감지 또는 외부 중단).")
        # P 감지 후에는 set_parking_after_p_detection에서 다음 단계 진행


    def set_parking_after_p_detection(self):
        """ P 표지판 감지 후 자동 주차 모드로 전환 """
        if self.mode == "auto": # 여전히 자율주행 모드였을 때만 (안전장치)
            print("P 표지판 감지에 따라 자동 주차 모드 진입 시도.")
            # self.stop_current_operations(stop_rc_car=False) # 현재 자율주행 스레드는 이미 종료되었거나 종료될 예정
                                                       # RC카는 즉시 정지시키지 않고 주차 로직에서 제어
            self.set_parking() # 자동 주차 모드 설정 및 스레드 시작


    def set_parking(self):
        """자동 주차 모드로 전환합니다."""
        # 현재 다른 작업이 실행 중일 수 있으므로 정리 (RC카는 바로 멈추지 않을 수 있음)
        self.stop_current_operations(stop_rc_car=False) # RC카 정지는 주차 로직 시작 시 결정

        self.mode = "park"
        if self.auto_parker: # 이전 상태 리셋
            self.auto_parker.reset_parking_state()
        self.update_mode_label()


        # 주차 시에는 카메라가 항상 필요하다고 가정
        if not self.initialize_autopilot_resource():
            self.mode_status_label.config(text="모드: 자동주차 실패 (카메라)", fg="red")
            if hasattr(self, 'mode_status_label2') and self.mode_status_label2.winfo_exists():
                 self.mode_status_label2.config(text="모드: 자동주차 실패 (카메라)", fg="red")
            self.mode = "None" # 실패 시 모드 초기화
            self.update_mode_label()
            return

        if not self.parking_in_progress: # 중복 실행 방지
            self.parking_in_progress = True
            self.parking_thread = threading.Thread(target=self.run_parking_algorithm, daemon=True)
            self.parking_thread.start()
            print("🅿️ 자동 주차 모드로 전환됨. 스레드 시작.")
        else:
            print("⚠️ 자동 주차가 이미 실행 중이거나 플래그 오류. (parking_in_progress가 True)")


    def run_parking_algorithm(self):
        """자동 주차 알고리즘을 실행합니다."""
        print("자동 주차 알고리즘 스레드 시작됨.")
        
        # AutoParking 객체는 __init__에서 생성됨
        if not self.auto_parker:
            print("❌ AutoParking 객체가 초기화되지 않았습니다.")
            self.parking_in_progress = False
            self.root.after(0, self.set_manual_after_operation, "주차 객체 오류")
            return

        # 카메라 리소스 확인 (영상 표시를 위함. 주차 로직 자체는 센서 기반일 수 있음)
        # if not (self.cap_resource and hasattr(self.cap_resource, 'cap') and self.cap_resource.cap.isOpened()):
        #     print("⚠️ run_parking_algorithm: 카메라가 준비되지 않았지만, 센서 기반 주차를 시도합니다.")
            # 카메라는 영상 표시에만 사용하고, 주차 로직은 센서로만 진행 가능하도록 할 수 있음

        self.auto_parker.reset_parking_state() # 항상 초기 상태에서 시작
        
        parking_active = True
        while self.parking_in_progress and self.mode == "park" and parking_active:
            sensor_data = self.net.receive_sensor_data() # ESP32로부터 센서 데이터 수신
            # print(f"Parking Algorithm Loop - Sensor Data: {sensor_data}") # 디버깅용

            if sensor_data is None:
                print("⚠️ 주차 중 센서 데이터를 받지 못했습니다. 잠시 후 재시도.")
                time.sleep(0.1) # 잠시 대기 후 다시 시도
                continue

            # AutoParking 로직 실행
            # attempt_parking_maneuver는 다음 상태를 반환 (예: "parking", "complete", "failed", "abort")
            parking_status = self.auto_parker.attempt_parking_maneuver(sensor_data)
            self.root.after(0, self.update_mode_label) # 주차 단계 변경 시 GUI 레이블 업데이트

            if parking_status == PARKING_STEP_COMPLETE:
                print("✅ 자동 주차 성공!")
                self.root.after(0, self.set_manual_after_operation, "주차 완료")
                parking_active = False
            elif parking_status == PARKING_STEP_FAILED:
                print("❌ 자동 주차 실패.")
                self.root.after(0, self.set_manual_after_operation, "주차 실패")
                parking_active = False
            elif parking_status == PARKING_STEP_ABORT:
                print("🚫 자동 주차 중단 (공간 없음 또는 기타).")
                self.root.after(0, self.set_manual_after_operation, "주차 공간 없음")
                parking_active = False
            elif not self.parking_in_progress: # 외부에서 중지 요청 시 (플래그 변경 감지)
                print("자동 주차 외부 중단됨.")
                if self.auto_parker: self.auto_parker.stop_car() # 차 멈춤
                parking_active = False
            
            # 프레임 읽기 (영상 표시용, 주차 로직에 필수는 아님)
            if self.show_video and self.cap_resource and self.cap_resource.cap.isOpened():
                ret, frame = self.cap_resource.cap.read()
                # if ret:
                #     # 필요시 주차 중인 화면에 추가 정보 표시 가능
                #     # processed_frame, _, _ = self.cap_resource.process_frame(frame, current_mode="park")
                #     # cv2.imshow("Operation View", processed_frame) # video_loop_run에서 처리
                #     pass
                pass

            time.sleep(0.1) # 주차 로직의 각 스텝 사이의 지연 (너무 빠르지 않게)

        self.parking_in_progress = False # 스레드 종료 전 플래그 확실히 끔
        if parking_active: # 루프가 parking_active=False 조건 외의 이유로 종료된 경우
            print("자동 주차 알고리즘 스레드 루프 비정상 종료.")
            if self.auto_parker: self.auto_parker.stop_car()
            self.root.after(0, self.set_manual_after_operation, "주차 비정상 종료")
        
        # auto_parker 상태는 해당 객체 내에서 관리됨. 필요시 여기서 reset 호출.
        # if self.auto_parker: self.auto_parker.reset_parking_state()
        print("자동 주차 알고리즘 스레드 종료.")


    def set_manual_after_operation(self, reason="작업 완료"):
        """ 작업(자율주행, 자동주차) 완료 후 수동 모드로 전환 """
        # 다른 작업이 이미 시작되지 않았는지 확인 (중요)
        if not self.auto_running and not self.parking_in_progress:
            print(f"{reason} 후 수동 모드로 전환합니다.")
            self.mode = "manual" # 모드를 먼저 수동으로 설정
            self.stop_current_operations() # 나머지 정리 및 차량 정지
            self.update_mode_label()
        else:
            print(f"{reason} 발생했으나, 다른 작업이 진행 중이므로 수동 전환 안 함.")


    def toggle_operation_video(self):
        if self.mode not in ["auto", "park"]:
            print("자율 주행 또는 자동 주차 모드에서만 영상을 볼 수 있습니다.")
            if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
                 self.cap_label.config(text="자율 주행/주차 모드에서만 영상 확인 가능")
            return

        if not self.show_video: 
            self.start_video_loop()
        else: 
            self.stop_video_loop()

    def start_video_loop(self):
        if (self.mode != "auto" or not self.auto_running) and \
           (self.mode != "park" or not self.parking_in_progress): # 주차 중에도 영상 가능
            # 단, parking_in_progress만 True이고 스레드가 아직 안 돌았을 수 있으니,
            # 실제 영상 표시는 스레드 내부에서 프레임 가져올 때 결정
            if not (self.mode == "park" and self.parking_thread and self.parking_thread.is_alive()): # 주차 스레드 활성화 시에도 허용
                 print("비디오 시작 실패: 자율 주행 또는 자동 주차 중이 아닙니다.")
                 return


        if not (self.cap_resource and hasattr(self.cap_resource, 'cap') and self.cap_resource.cap.isOpened()):
            print("❌ 비디오 루프: 카메라가 준비되지 않았습니다.")
            if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
                self.cap_label.config(text="카메라 준비 안됨")
            return

        self.show_video = True
        if self.video_thread is None or not self.video_thread.is_alive():
            self.video_thread = threading.Thread(target=self.video_loop_run, daemon=True)
            self.video_thread.start()
            if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
                self.root.after(0, lambda: self.cap_label.config(text="영상 로딩 중... (Q: 종료)"))
        print("비디오 루프 시작 요청됨.")


    def stop_video_loop(self):
        if self.show_video: 
            print("비디오 루프 중지 요청 (stop_video_loop).")
            self.show_video = False 

            if self.video_thread and self.video_thread.is_alive():
                self.video_thread.join(timeout=1.0) # 타임아웃 약간 줄임
                if self.video_thread.is_alive():
                    print(f"⚠️ 비디오 스레드가 {self.video_thread.name} 시간 내에 완전 종료되지 않았습니다.")
            # cleanup_video_resources는 video_loop_run의 finally에서 호출됨
        else:
            # 영상이 이미 꺼져있거나 스레드가 없는 경우에도 정리 시도
            self.cleanup_video_resources()


    def video_loop_run(self):
        print("비디오 루프 스레드 시작됨.")
        window_name = "Operation View" 

        if not (self.cap_resource and hasattr(self.cap_resource, 'cap') and self.cap_resource.cap.isOpened()):
            print("❌ video_loop_run: 카메라가 준비되지 않았습니다.")
            self.show_video = False 
            if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
                self.root.after(0, lambda: self.cap_label.config(text="카메라 오류"))
            self.root.after(0, self.cleanup_video_resources) # 메인스레드에서 정리하도록 예약
            return

        try:
            while self.show_video: # self.show_video 플래그만으로 루프 제어
                # 현재 활성 모드(자율주행 또는 주차)인지 내부에서 한번 더 체크 가능
                is_operation_active = (self.mode == "auto" and self.auto_running) or \
                                      (self.mode == "park" and self.parking_in_progress)
                if not is_operation_active and self.show_video:
                    # 활성 작업 없이 영상만 켜져있는 경우 (예: 작업 완료 후 영상 창 안닫힘)
                    # 검은 화면 또는 대기 메시지 표시 가능
                    dummy_frame = np.zeros((self.cap_resource.height, self.cap_resource.width, 3), dtype=np.uint8)
                    cv2.putText(dummy_frame, "No active operation. Press Q to close.",
                                (50, self.cap_resource.height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.imshow(window_name, dummy_frame)
                    if cv2.waitKey(30) & 0xFF == ord('q'):
                        self.show_video = False # 루프 종료
                        break
                    continue


                ret, frame = self.cap_resource.cap.read()
                if not ret:
                    print("⚠️ 비디오 루프: 프레임 읽기 실패.")
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1 : # 창이 닫혔으면 루프 종료
                        self.show_video = False
                        break
                    cv2.waitKey(100) 
                    continue
                
                try:
                    # 현재 모드에 따라 다른 처리 (자율주행 시 라인, 주차 시 다른 정보 등)
                    display_mode_for_frame = "auto" if self.mode == "auto" else "park" # 또는 None
                    processed_frame, _, p_detected_in_frame = self.cap_resource.process_frame(frame, current_mode=display_mode_for_frame)
                    
                    # 주차 모드일 때 AutoParking 상태를 화면에 표시 (예시)
                    if self.mode == "park" and self.auto_parker:
                        cv2.putText(processed_frame, f"Parking: {self.auto_parker.current_parking_step}",
                                    (10, processed_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

                    cv2.imshow(window_name, processed_frame)
                except cv2.error as e: # OpenCV 관련 에러 (창 닫힘 등)
                    print(f"OpenCV 에러 (비디오 루프): {e}. 영상 루프 종료.")
                    self.show_video = False # 루프 종료
                    break
                except Exception as e:
                    print(f"비디오 프레임 처리/표시 중 오류: {e}")
                    # 원본 프레임이라도 표시 시도
                    try: cv2.imshow(window_name, frame)
                    except: pass


                if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
                    if not self.cap_label.cget("text").startswith("Q를 눌러"): # 메시지 중복 방지
                        self.root.after(0, lambda: self.cap_label.config(text="Q를 눌러 카메라 종료"))

                key = cv2.waitKey(1) & 0xFF 
                if key == ord('q'):
                    print("Q키 입력으로 비디오 종료 요청됨.")
                    self.show_video = False                                                         
                    break 
            
        finally: 
            print(f"비디오 루프 스레드 '{window_name}' 종료 수순 시작 (show_video: {self.show_video}).")
            try:
                if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) >= 1: # 창이 아직 있다면
                    cv2.destroyWindow(window_name)
                    print(f"'{window_name}' 창이 비디오 스레드에서 닫힘.")
            except cv2.error: # 이미 닫혔거나 할 수 없음
                pass
            except Exception as e:
                print(f"'{window_name}' 창 닫기 시도 중 알 수 없는 오류: {e}")

            # self.show_video = False # 확실히 False로 설정
            self.root.after(0, self.cleanup_video_resources) # 메인 스레드에서 리소스 정리


    def cleanup_video_resources(self):
        # print("비디오 리소스 정리 시작...")
        current_thread_name = self.video_thread.name if self.video_thread else "N/A"

        if self.video_thread and self.video_thread.is_alive():
            # print(f"Cleanup: 비디오 스레드 ({current_thread_name})가 아직 살아있어 join 시도.")
            self.video_thread.join(timeout=0.1) # 매우 짧은 추가 대기
            if self.video_thread.is_alive():
                 print(f"⚠️ Cleanup: 비디오 스레드 ({current_thread_name})가 여전히 종료되지 않음.")

        self.video_thread = None 
        self.show_video = False # 최종적으로 플래그를 False로

        if hasattr(self, 'cap_label') and self.cap_label.winfo_exists():
            self.cap_label.config(text="") 
        
        # print(f"비디오 리소스 정리 완료 (이전 스레드: {current_thread_name}).")
