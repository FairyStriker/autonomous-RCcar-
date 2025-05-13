#AutoPilot.py

import cv2
import numpy as np
import math

class autopilot:
    def __init__ (self,url,width=640,height=480):
        self.url = url
        self.width = width
        self.height = height
        self.cap = cv2.VideoCapture(self.url)
        self.cap.set(3, self.width)
        self.cap.set(4, self.height)

    def process_frame(self,frame):
        """프레임을 처리하여 라인 추적을 위한 이진화 및 각도 계산"""

        frame = cv2.flip(frame, 1)
        roi = frame[300:480, 0:640]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blur, 60, 255, cv2.THRESH_BINARY_INV)

        ref_x = 320  # 화면 중앙 기준선
        target_y = 120  # ROI 내 y 기준

        # 수평 스캔 라인 기준으로 검정 픽셀 찾기
        scan_line = binary[target_y]
        black_indices = np.where(scan_line == 255)[0]

        direction = "None"
        angle_deg = 0

        if len(black_indices) >= 2:
            left = black_indices[0]
            right = black_indices[-1]
            center_x = (left + right) // 2

            # 세로 기준 ref_y
            ref_y = 0
            dy = target_y - ref_y
            dx = center_x - ref_x

            angle_rad = math.atan2(dx, dy)
            angle_deg = round(np.degrees(angle_rad), 1)  # 수치로 변환
            # 시각화
            cv2.line(roi, (ref_x, 0), (ref_x, 180), (255, 0, 0), 2)  # 기준선
            cv2.line(roi, (ref_x, 0), (center_x, target_y), (0, 255, 0), 2)  # 각도선
            cv2.circle(roi, (center_x, target_y), 5, (0, 0, 255), -1)
            
            #출력
            cv2.putText(frame, f"Angle: {angle_deg} deg", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        return frame,angle_deg

    def camera_release(self):
        self.cap.release()
