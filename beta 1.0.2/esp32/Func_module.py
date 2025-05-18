#Func_module.py

from machine import Pin
from hcsr04 import HCSR04

class sensors_data:
    def __init__(self,max_cm=50):
        self.cm_timeout = int(29.1 * max_cm * 2)
        self.pins = [(15, 4), (13, 12), (17, 16), (23, 22), (27, 26), (33, 32)]
        self.echo_sensors = [HCSR04(trig, echo, self.cm_timeout) for trig, echo in self.pins]
        self.ir_sensors = [Pin(34,Pin.IN),Pin(35,Pin.IN)]

    def read_all_sensors(self):
        """
        초음파 6개, IR 2개 값을 읽어서 딕셔너리로 반환.
        오류 발생 시 -1 반환.
        결과 예시:
        {
            "UL0": 34, "UL1": 55, ..., "IR0": 1, "IR1": 0
        }
        """
        result = {}

        for i, us in enumerate(self.echo_sensors):
            try:
                dist = int(us.distance_cm())
            except Exception:
                dist = -1
            result[f"UL{i}"] = dist

        for i, ir in enumerate(self.ir_sensors):
            try:
                val = ir.value()
            except Exception:
                val = -1
            result[f"IR{i}"] = val

        return result
