from machine import Pin, PWM
from hcsr04 import HCSR04
from DCMotor import DCmotor
from ServoMotor import Servo
import time

class parking:
    def __init__(self,DCMotor,servo):
        self.dc = DCMotor
        self.servo = servo
        self.sensors1 = HCSR04(33,32)
        self.sensors2 = HCSR04(22,23)	#후면부좌측
        self.sensors3 = HCSR04(17,16)	#후면부중앙
        self.sensors4 = HCSR04(15,4)	#후면부우측

        self.limit_distance = int(10)
        self.t = 0
        
    def forward(self,sec, speed=50):
        self.dc.forward(speed)
        time.sleep(sec)
        self.dc.motor_stop()
        
    def backward(self,sec,speed=50):
        self.dc.backward(speed)
        time.sleep(sec)
        self.dc.motor_stop()

    def left(self):
        self.servo.servo_angle(60)

    def right(self):
        self.servo.servo_angle(120)

    def straight(self):
        self.servo.servo_angle(90)
        
    def step1(self):
        data1 = int(self.sensors1.distance_cm())

        if data1 > 10:
            self.forward(1,100)
            self.right()
            print("주차공간 있음")
            return True

        else:
            self.dc.motor_stop()
            print("주차공간 없음")
            return False
        
    def step2(self):
        print("2단계 진입")
        data2 = int(self.sensors2.distance_cm())	#좌측
        data3 = int(self.sensors3.distance_cm())	#중앙
        data4 = int(self.sensors4.distance_cm())	#우측
        time.sleep(0.1)
        diff = data2 - data4
        print (data3)

        if 0 < data3 < self.limit_distance:
            self.dc.motor_stop()
            self.straight()
            if abs(diff) < 10:
                print("주차완료")
            return False

        if 0 < data4 < 7:
            self.right()
            self.forward(1,100)
        elif 0 < data2 < 7:
            self.left()
            self.forward(1,100)
        else:
            self.straight()
        return True
    
    def run_autoparking(self):
        can_proceed_to_step2 = self.step1()
        if can_proceed_to_step2:
            self.dc.backward(40)
            keep_running_step2 = True
            while keep_running_step2:
                self.dc.backward(40)
                keep_running_step2 = self.step2()
                time.sleep(0.1)
                
                if not keep_running_step2: # step2가 False를 반환하면 (주차 완료)
                    break
            if keep_running_step2:
                print("경고: 자동 주차 루프가 예기치 않게 종료되었습니다.")
                self.dc.motor_stop()
                
        else:
            print("자동 주차를 시작할 수 없습니다 (1단계 실패).")

        print("자동 주차 시스템 종료.")