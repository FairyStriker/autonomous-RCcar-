from machine import Pin
import time

# 왼쪽과 오른쪽 IR 센서 설정
ir_left = Pin(14, Pin.IN)     # GPIO14
ir_right = Pin(27, Pin.IN)    # GPIO27

while True:
    left_val = ir_left.value()
    right_val = ir_right.value()

    # 출력 확인
    print("왼쪽:", left_val, "오른쪽:", right_val)

    if left_val == 0:
        print("왼쪽 감지됨 → 오른쪽으로 회피")
    elif right_val == 0:
        print("오른쪽 감지됨 → 왼쪽으로 회피")
    else:
        print("감지 없음 → 직진")

    time.sleep(0.1)
