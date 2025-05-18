# AutoPilot.py

import cv2
import numpy as np
import math
from is_p_sign import is_p_sign # P 표지판 인식 함수 임포트

class autopilot:
    def __init__(self, url, width=640, height=480):
        self.url = url
        self.width = width
        self.height = height
        self.cap = cv2.VideoCapture(self.url)
        if not self.cap.isOpened():
            print(f"Error: 카메라를 열 수 없습니다. URL: {self.url}")
        else:
            self.cap.set(3, self.width)
            self.cap.set(4, self.height)
            print("카메라 초기화 성공.")


        # 라인 추적용 ROI 설정
        self.roi_start_y_ratio = 5/8
        self.roi_end_y_ratio = 1.0
        self.roi_start_x_ratio = 0.0
        self.roi_end_x_ratio = 1.0

        # P 표지판 감지를 위한 ROI 설정 (튜닝 필요)
        self.p_sign_roi_x_ratio = 0.3
        self.p_sign_roi_y_ratio = 0.1
        self.p_sign_roi_w_ratio = 0.4 # 너비 비율
        self.p_sign_roi_h_ratio = 0.3 # 높이 비율

        # 라인 추적용 기준 좌표 (ROI 내부) - 튜닝 필요
        self.tuned_ref_x = 320
        self.tuned_target_y = 120

    def process_frame(self, frame_orig, current_mode="auto"): # current_mode 인자: "auto", "park", 등
        """프레임을 처리하여 라인 추적 및 P 표지판 감지, 각도 계산"""
        if not self.cap or not self.cap.isOpened() or frame_orig is None:
            print("Error: 카메라가 준비되지 않았거나 프레임이 없습니다 (AutoPilot).")
            dummy_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            cv2.putText(dummy_frame, "CAM ERROR", (self.width//2 - 100, self.height//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255),2)
            return dummy_frame, 0, False


        frame = frame_orig.copy()
        frame_flipped = cv2.flip(frame, 1) # 화면 반전

        angle_deg = 0 # 기본값
        p_detected = False # 기본값

        # 1. 라인 추적 로직 (자율 주행 모드 또는 필요시 다른 모드에서도 사용 가능)
        if current_mode == "auto": # 예시: 자율 주행 모드에서만 라인 추적 활성화
            line_roi_start_y = int(self.height * self.roi_start_y_ratio)
            line_roi_end_y = int(self.height * self.roi_end_y_ratio)
            line_roi_start_x = int(self.width * self.roi_start_x_ratio)
            line_roi_end_x = int(self.width * self.roi_end_x_ratio)

            line_roi = frame_flipped[line_roi_start_y:line_roi_end_y, line_roi_start_x:line_roi_end_x]
            line_roi_h, line_roi_w = line_roi.shape[:2]


            if line_roi_h > 0 and line_roi_w > 0:
                gray_line = cv2.cvtColor(line_roi, cv2.COLOR_BGR2GRAY)
                blur_line = cv2.GaussianBlur(gray_line, (5, 5), 0)
                _, binary_line = cv2.threshold(blur_line, 60, 255, cv2.THRESH_BINARY_INV)

                current_target_y = max(0, min(self.tuned_target_y, line_roi_h - 1))
                current_ref_x = max(0, min(self.tuned_ref_x, line_roi_w - 1))

                if current_target_y < binary_line.shape[0]:
                    scan_line = binary_line[current_target_y]
                    black_indices = np.where(scan_line == 255)[0]

                    if len(black_indices) >= 2:
                        left = black_indices[0]
                        right = black_indices[-1]
                        center_x = (left + right) // 2
                        ref_y = 0
                        dy = current_target_y - ref_y
                        dx = center_x - current_ref_x
                        angle_rad = math.atan2(dx, dy)
                        angle_deg = round(np.degrees(angle_rad), 1)

                        cv2.line(line_roi, (current_ref_x, 0), (current_ref_x, line_roi_h), (255, 0, 0), 2)
                        cv2.line(line_roi, (current_ref_x, 0), (center_x, current_target_y), (0, 255, 0), 2)
                        cv2.circle(line_roi, (center_x, current_target_y), 5, (0, 0, 255), -1)
            else:
                print("Warning: Line ROI has zero height or width.")
        
        # 2. P 표지판 감지 로직 (자율 주행 모드에서만 실행)
        if current_mode == "auto": # "auto" 모드일 때만 P 표지판 감지 시도
            p_roi_x = int(self.width * self.p_sign_roi_x_ratio)
            p_roi_y = int(self.height * self.p_sign_roi_y_ratio)
            p_roi_w = int(self.width * self.p_sign_roi_w_ratio)
            p_roi_h = int(self.height * self.p_sign_roi_h_ratio)

            p_roi_x = max(0, p_roi_x)
            p_roi_y = max(0, p_roi_y)
            p_roi_end_x = min(self.width, p_roi_x + p_roi_w)
            p_roi_end_y = min(self.height, p_roi_y + p_roi_h)

            if p_roi_end_x > p_roi_x and p_roi_end_y > p_roi_y:
                p_sign_candidate_roi = frame_flipped[p_roi_y:p_roi_end_y, p_roi_x:p_roi_end_x]
                gray_p_roi = cv2.cvtColor(p_sign_candidate_roi, cv2.COLOR_BGR2GRAY)
                if is_p_sign(gray_p_roi):
                    p_detected = True
                    cv2.rectangle(frame_flipped, (p_roi_x, p_roi_y), (p_roi_end_x, p_roi_end_y), (0, 255, 255), 2)
                    cv2.putText(frame_flipped, "P DETECTED", (p_roi_x, p_roi_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            else:
                print("Warning: P sign ROI has zero height or width or is out of bounds.")
        
        # 3. 자동 주차 모드용 영상 처리 (필요시)
        # if current_mode == "park":
            # 여기에 자동 주차에 필요한 특수 영상 처리 로직 추가 가능
            # 예: 주차선 감지, 차량 위치 인식 등
            # cv2.putText(frame_flipped, "PARKING MODE VIEW", (10, self.height - 30),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,100,0), 2)
            # angle_deg, p_detected 값은 이 모드에서는 다르게 설정되거나 사용되지 않을 수 있음

        # 4. 결과 출력 및 반환
        if current_mode == "auto": # 자율 주행 시에만 각도 표시 (예시)
            cv2.putText(frame_flipped, f"Angle: {angle_deg:.1f} deg", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        if p_detected: # P 감지 시 화면에 표시 (current_mode가 "auto"일 때만 p_detected가 True가 될 수 있음)
             cv2.putText(frame_flipped, "P!", (self.width - 70, 50), cv2.FONT_HERSHEY_TRIPLEX, 1.5, (0,0,255),2)


        return frame_flipped, angle_deg, p_detected

    def camera_release(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
            print("카메라 리소스 해제됨.")
