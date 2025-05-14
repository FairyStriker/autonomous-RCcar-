#main.py

from machine import Pin, PWM,Timer
from DCMotor import DCmotor
from ServoMotor import Servo
from wifi_ESP import wifi_TCP
import time
from Func_module import *

server = None
cl = None
sensors = None

def send_sensor_callback(timer):
    sensor_data = sensors.read_all_sensors()
    server.send_sensor_data(sensor_data)

# DC모터 초기화
in1 = Pin(18, Pin.OUT)
in2 = Pin(19, Pin.OUT)
pwm = PWM(Pin(21))
pwm.freq(1000)
stby = Pin(5, Pin.OUT)
stby.value(1)
motor = DCmotor(in1, in2, pwm, stby)

# 서보 모터 초기화
servo = Servo(25)
angle = 90
servo.servo_angle(angle)

# 웹 서버 설정(자세한 값은 추후에 수정)
server = wifi_TCP(
    ssid="song",
    password="0000009628",
    static_ip="192.168.0.123",
    subnet_mask="255.255.255.0",
    gateway="192.168.0.1",
    dns_server="8.8.8.8"
)
server.start_server()
cl = server.accept_client()
sensors = sensors_data()
timer0 = Timer(0)
timer0.init(period=500, mode=Timer.PERIODIC,callback=send_sensor_callback)

while True:
    if server.cl is None:
        server.cl = server.accept_client()
    try:
        mode, angle, speed = server.receive_command()
        print(mode,angle,speed)

        servo.servo_angle(angle)
        if mode == "FWD":
            motor.forward(speed)
        elif mode == "BACK":
            motor.backward(speed)
        elif mode == "STOP":
            motor.motor_stop()

    except:
        try:
            server.cl.close()
        except:
            pass
        
        server.cl = None


    


