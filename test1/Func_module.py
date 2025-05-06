#Func_module.py

from machine import Pin
from hcsr04 import HCSR04

def echo_distance(max_cm):
    cm_timeout = int(29.1 * max_cm * 2)
    pins = [(5, 4), (13, 12), (15, 14), (23, 22), (27, 26), (33, 32)]
    sensors = [HCSR04(trig, echo, cm_timeout) for trig, echo in pins]
    distances = [sensor.distance_cm() for sensor in sensors]
    return distances
