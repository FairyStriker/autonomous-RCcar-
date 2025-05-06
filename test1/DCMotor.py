class DCmotor:
    def __init__(self, in1, in2, pwm, stby):
        self.in1 = in1
        self.in2 = in2
        self.pwm = pwm
        self.stby = stby
        
    def forward(self,speed):
        self.in1.value(1)
        self.in2.value(0)
        duty = int((speed/100)*65535)
        self.pwm.duty_u16(duty)
        
    def backward(self,speed):
        self.in1.value(0)
        self.in2.value(1)
        duty = int((speed/100)*65535)
        self.pwm.duty_u16(duty)
        
    def motor_stop(self):
        self.in1.value(0)
        self.in2.value(0)
        self.pwm.duty_u16(0)