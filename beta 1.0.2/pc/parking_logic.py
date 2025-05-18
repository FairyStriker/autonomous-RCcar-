# parking_logic.py

import time

# 전면 우측 대각선 초음파 센서 인덱스 (ESP_command.py의 parse_sensor_data 반환값 기준)
# 실제 RC카의 센서 데이터 키값에 맞춰 수정해야 합니다.
# 예시: ESP32에서 "ULTRA_FR_DIAG:값" 형태로 데이터를 보낸다고 가정
FRONT_RIGHT_DIAG_ULTRA_KEY = "ultra_fr_diag" # ESP32에서 오는 실제 키로 변경 필요
# 뒷바퀴 IR 센서 키 (라인 감지용)
IR_REAR_LEFT_KEY = "ir_rl" # ESP32에서 오는 실제 키로 변경 필요
IR_REAR_RIGHT_KEY = "ir_rr" # ESP32에서 오는 실제 키로 변경 필요


# 주차 공간으로 판단할 최소 거리 (cm) - 튜닝 필요
PARKING_SPACE_MIN_DEPTH_CM = 50  # 예시 값, 실제 주차 공간 깊이에 맞게 조정
# 차량 폭 + 약간의 여유 (cm) - 튜닝 필요 (현재 로직에서는 직접 사용되지 않으나 개념적으로 필요)
# PARKING_SPACE_MIN_WIDTH_CM = 30

# 주차 시도 전 전진 시간 (초) - 속도와 거리에 따라 튜닝 필요
PRE_PARKING_FORWARD_DURATION_S = 0.5 # 예시: 0.5초간 전진
# 우회전 후진 시간 (초) - 각도와 속도에 따라 튜닝 필요
TURN_IN_DURATION_S = 2.5 # 예시: 2.5초간 우회전 후진
# 직진 후진 최대 시간 (초) - IR 센서 감지 실패 시 타임아웃
STRAIGHT_IN_MAX_DURATION_S = 5.0

# 주차 시도 전체 시간 (초) - 튜닝 필요
PARKING_MANEUVER_TIMEOUT_S = 15  # 주차 시도 최대 시간

# 주차 단계 정의
PARKING_STEP_SEARCHING = "searching"
PARKING_STEP_PRE_FORWARD = "pre_forward"
PARKING_STEP_TURN_IN = "turn_in"
PARKING_STEP_STRAIGHT_IN = "straight_in"
PARKING_STEP_COMPLETE = "complete"
PARKING_STEP_FAILED = "failed"
PARKING_STEP_ABORT = "abort" # P 감지 후 공간 없음

class AutoParking:
    def __init__(self, esp_comm):
        self.esp = esp_comm
        self.current_parking_step = PARKING_STEP_SEARCHING
        self.parking_maneuver_start_time = None
        self.step_start_time = None # 각 단계 시작 시간

    def send_rc_command(self, command, angle, speed):
        cmd_str = f"{command},{angle},{speed}"
        print(f"[AutoParking] 전송: {cmd_str}")
        if not self.esp.send_command(cmd_str):
            print(f"[AutoParking] Error: Failed to send command {cmd_str}")
            return False
        return True

    def stop_car(self):
        return self.send_rc_command("STOP", 90, 0)

    def check_parking_space(self, sensor_data):
        if sensor_data is None or FRONT_RIGHT_DIAG_ULTRA_KEY not in sensor_data:
            return False

        distance = sensor_data[FRONT_RIGHT_DIAG_ULTRA_KEY]
        print(f"[AutoParking] 우측 대각선 센서 거리: {distance} cm")

        if distance > PARKING_SPACE_MIN_DEPTH_CM:
            print(f"[AutoParking] 주차 공간 가능성 감지 (거리: {distance} cm)")
            return True
        return False

    def attempt_parking_maneuver(self, sensor_data):
        current_time = time.time()

        # 전체 주차 시간 초과 확인
        if self.parking_maneuver_start_time and \
           (current_time - self.parking_maneuver_start_time > PARKING_MANEUVER_TIMEOUT_S):
            print("[AutoParking] 전체 주차 시간 초과!")
            self.stop_car()
            self.current_parking_step = PARKING_STEP_FAILED
            return PARKING_STEP_FAILED

        if self.current_parking_step == PARKING_STEP_SEARCHING:
            if self.check_parking_space(sensor_data):
                self.current_parking_step = PARKING_STEP_PRE_FORWARD
                print("[AutoParking] 상태 변경: PRE_FORWARD (주차 공간 찾음, 약간 전진 시작)")
                self.parking_maneuver_start_time = current_time # 전체 주차 시간 타이머 시작
                self.step_start_time = current_time # PRE_FORWARD 단계 시작 시간
                self.send_rc_command("FWD", 90, 80) # 예시: 직진, 속도 80
                return "parking"
            else:
                # 빈 공간을 계속 찾고 있음 (또는 여기서 abort 결정 가능)
                # P표지판은 인식했지만 공간이 없으면 abort
                # 이 함수는 P인식 후에 호출되므로, 여기서 공간 없으면 abort
                print("[AutoParking] 주차 공간 없음 (SEARCHING 단계). 자동 주차 중단.")
                self.reset_parking_state() # 상태 초기화
                return PARKING_STEP_ABORT

        elif self.current_parking_step == PARKING_STEP_PRE_FORWARD:
            if current_time - self.step_start_time >= PRE_PARKING_FORWARD_DURATION_S:
                print("[AutoParking] PRE_FORWARD 완료. TURN_IN 시작")
                self.current_parking_step = PARKING_STEP_TURN_IN
                self.step_start_time = current_time
                self.send_rc_command("BACK", 45, 80) # 예시: 우회전(스티어링 각도 45), 후진, 속도 80
            else:
                # 계속 전진 중 (명령은 이미 보냄)
                pass # FWD, 90, 80 명령은 유지
            return "parking"

        elif self.current_parking_step == PARKING_STEP_TURN_IN:
            if current_time - self.step_start_time >= TURN_IN_DURATION_S:
                print("[AutoParking] TURN_IN 완료 (시간 기반). STRAIGHT_IN 시작")
                self.current_parking_step = PARKING_STEP_STRAIGHT_IN
                self.step_start_time = current_time
                self.send_rc_command("BACK", 90, 70) # 핸들 중앙, 후진, 속도 70
            else:
                # 계속 우회전 후진 중 (명령은 이미 보냄)
                pass # BACK, 45, 80 명령은 유지
            return "parking"

        elif self.current_parking_step == PARKING_STEP_STRAIGHT_IN:
            ir_rl = sensor_data.get(IR_REAR_LEFT_KEY, 1) # 라인 미감지 시 1 (또는 센서 특성에 맞게)
            ir_rr = sensor_data.get(IR_REAR_RIGHT_KEY, 1) # 라인 미감지 시 1

            # 실제 IR센서가 라인을 감지할 때 0 값을 보낸다고 가정
            if ir_rl == 0 and ir_rr == 0:
                print("[AutoParking] IR 센서 주차 라인 감지. 주차 완료.")
                self.stop_car()
                self.current_parking_step = PARKING_STEP_COMPLETE
                return PARKING_STEP_COMPLETE

            if current_time - self.step_start_time > STRAIGHT_IN_MAX_DURATION_S:
                print("[AutoParking] STRAIGHT_IN 시간 초과 (IR 센서 미감지). 주차 실패 간주.")
                self.stop_car()
                self.current_parking_step = PARKING_STEP_FAILED
                return PARKING_STEP_FAILED
            else:
                # 계속 직진 후진 중 (명령은 이미 보냄)
                pass # BACK, 90, 70 명령은 유지
            return "parking"

        elif self.current_parking_step == PARKING_STEP_COMPLETE:
            # 이 상태는 이미 완료를 의미하므로, 외부에서 reset_parking_state 호출
            return PARKING_STEP_COMPLETE

        elif self.current_parking_step == PARKING_STEP_FAILED:
            # 이 상태는 이미 실패를 의미하므로, 외부에서 reset_parking_state 호출
            return PARKING_STEP_FAILED

        elif self.current_parking_step == PARKING_STEP_ABORT:
            # 이 상태는 이미 중단을 의미하므로, 외부에서 reset_parking_state 호출
            return PARKING_STEP_ABORT

        return "parking" # 기본적으로 진행 중 상태

    def reset_parking_state(self):
        self.current_parking_step = PARKING_STEP_SEARCHING
        self.parking_maneuver_start_time = None
        self.step_start_time = None
        print("[AutoParking] 주차 상태 초기화됨.")

    def is_parking_active(self):
        """현재 자동 주차 로직이 중간 단계에 있는지 확인"""
        return self.current_parking_step not in [
            PARKING_STEP_SEARCHING,
            PARKING_STEP_COMPLETE,
            PARKING_STEP_FAILED,
            PARKING_STEP_ABORT
        ]
