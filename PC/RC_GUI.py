#RC_GUI.py

import tkinter as tk
import threading
import cv2
from ESP_command import ESP_PC_Network
from AutoPilot import autopilot
import numpy as np

class RC_GUI:
    def __init__(self,root_window,ip,port,url=0):
        self.root = root_window
        self.root.title("RC car System")
        self.root.geometry("300x320")
        self.root.bind("<KeyPress>", self.key_pressed)
        self.root.bind("<KeyRelease>", self.key_released)
        self.ip = ip
        self.port = port
        self.url = url
        
        self.mode = "None"
        self.command = "STOP"
        self.angle = 90

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
        tk.Button(self.root, text="자동 주차", command=self.set_parking).pack(pady=5)
        tk.Button(self.root, text="자율주행 보기/숨기기", command=self.toggle_operation_video).pack(pady=10)

        self.key_info_label = tk.Label(self.root, text="", fg="gray")
        self.key_info_label.pack(pady=5)

        self.update_mode_label()

    def update_mode_label(self):
        text, color = "", "blue"
        key_info_text = ""

        if self.mode == "manual":
            text, color = "모드: 수동 모드", "green"
            key_info_text = "방향키로 조작 가능"
        elif self.mode == "auto":
            text, color = "모드: 자율 주행 중", "orange"
        elif self.mode == "park":
            text, color = "모드: 자동 주차 중", "purple"
        else: 
            text = "모드: 선택 안됨"
        
        self.key_info_label.config(text=key_info_text)
        self.mode_status_label.config(text=text, fg=color)

    def stop_current_operations(self, stop_rc_car=True): # RC카 정지 여부 인자 추가
        if self.auto_running:
            print("자율 주행 중지 요청...")
            self.auto_running = False
            if self.auto_pilot_thread and self.auto_pilot_thread.is_alive():
                self.auto_pilot_thread.join(timeout=1)
            self.auto_pilot_thread = None 
            print("자율 주행 중지됨.")

        if self.show_video:
            self.stop_video_loop() 

        if self.cap_resource:
            if hasattr(self.cap_resource, 'cap') and self.cap_resource.cap and self.cap_resource.cap.isOpened():
                print("카메라 리소스 해제 중...")
                self.cap_resource.cap.release()
        
        if stop_rc_car: # RC카 정지 명령 (필요한 경우에만)
            try:
                cmd_stop = f"STOP,90,0,0"
                self.net.send_command(cmd_stop)
                print("RC카 정지 명령 전송 (stop_current_operations)")
            except Exception as e:
                print(f"❌ 정지 명령 전송 오류 (stop_current_operations): {e}")

                
    def set_manual(self):
        self.stop_current_operations() # 모든 작업 중지 및 RC카 정지
        self.mode = "manual"
        self.update_mode_label()
        print("수동 모드로 전환됨.")

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
        elif key == 'Right':
            new_angle = min(135, self.angle + 15)
        elif key == 'Left':
            new_angle = max(45, self.angle - 15)
        else: 
            return

        if new_command != self.command or new_angle != self.angle:
            self.command = new_command
            self.angle = new_angle
            cmd_to_send = f"{self.command},{self.angle},100,0" 
            try:
                self.net.send_command(cmd_to_send)
            except Exception as e:
                print("❌ 전송 오류 (key_pressed):", e)
                self.net.reconnect() 

    def key_released(self, event):
        if self.mode != "manual":
            return
        
        if event.keysym in ['Up', 'Down']:
            self.command = "STOP"
            cmd_to_send = f"{self.command},{self.angle},0,0"
            try:
                self.net.send_command(cmd_to_send)
            except Exception as e:
                print("❌ 전송 오류 (key_released):", e)
                self.net.reconnect()

    def set_auto(self):
        self.stop_current_operations() 
        self.mode = "auto" 
        self.update_mode_label() 
        
        if not self.initialize_autopilot_resource():
            self.mode_status_label.config(text="모드: 자율주행 실패 (카메라)", fg="red")
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


    def run_autopilot(self):
        print("자율 주행 스레드 시작됨.")
        if not (self.cap_resource and hasattr(self.cap_resource, 'cap') and self.cap_resource.cap.isOpened()):
            print("❌ run_autopilot: 카메라가 준비되지 않았습니다.")
            self.auto_running = False 
            self.root.after(0, lambda: self.mode_status_label.config(text="모드: 자율주행 실패 (카메라)", fg="red"))
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


                servo_angle = max(60, min(120, int(90 + angle_deg))) 
                
                if servo_angle != self.angle: # 각도 변경 시에만 전송 (FWD 유지)
                    self.angle = servo_angle
                    # 자율 주행 중에는 계속 FWD 유지, 각도만 변경
                    cmd = f"FWD,{self.angle},80,0" # 예시: 속도 80 (튜닝 필요)
                    try:
                        self.net.send_command(cmd)
                    except Exception as e:
                        print("❌ 전송 오류 (run_autopilot):", e)


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
            self.set_parking() # 자동 주차 모드 설정 및 스레드 시작


    def set_parking(self):
        """자동 주차 모드로 전환합니다."""
        self.stop_current_operations()  # 현재 다른 작업이 실행 중일 수 있으므로 정리

        self.mode = "park"
        self.update_mode_label()

        cmd = f"{self.command},{self.angle},100,1" 
        try:
            self.net.send_command(cmd)
        except Exception as e:
            print("❌ 전송 오류 (key_pressed):", e)
            self.net.reconnect()


    def toggle_operation_video(self):
        if self.mode not in ["auto", "park"]:
            print("자율 주행 또는 자동 주차 모드에서만 영상을 볼 수 있습니다.")
            return

        if not self.show_video: 
            self.start_video_loop()
        else: 
            self.stop_video_loop()


    def start_video_loop(self):
        if (self.mode != "auto") and (self.mode != "park"):
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
                if not self.show_video:
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
                    processed_frame, _, _ = self.cap_resource.process_frame(frame,"video")
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


        

    
