#main.py

from machine import Pin, PWM
from DCMotor import DCmotor
from ServoMotor import Servo
from wifi_web import WebServer
import time

# DC모터 초기화
in1 = Pin(18, Pin.OUT)
in2 = Pin(19, Pin.OUT)
pwm = PWM(Pin(21))
pwm.freq(1000)
stby = Pin(17, Pin.OUT)
stby.value(1)
motor = DCmotor(in1, in2, pwm, stby)

# 서보 모터 초기화
servo = Servo(25)
angle = 90
servo.servo_angle(angle)

# 웹 서버 설정
server = WebServer(ssid="Jsy", password="12345678")
server.start()

# 메인 루프
while True:
    key = server.handle_client()
    if key == "UP":
        motor.forward(100)
    elif key == "DOWN":
        motor.backward(100)
    elif key == "LEFT":
        angle = max(45, angle - 15)
        servo.servo_angle(angle)
    elif key == "RIGHT":
        angle = min(135, angle + 15)
        servo.servo_angle(angle)
    elif key == "STOP":
        motor.motor_stop()
