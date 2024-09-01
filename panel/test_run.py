#!/usr/bin/env python3

from lib.aht20 import AHT20
from lib.bmp_280 import BMP280
from time import sleep

CONVERT_HPA_MMHG = 0.7506
# OFFSET_TEMPERATURE = -0.6

bmp = BMP280(port=1,
             addr=0x77,
             mode=BMP280.NORMAL_MODE,
             oversampling_p=BMP280.OVERSAMPLING_P_x16,
             oversampling_t=BMP280.OVERSAMPLING_T_x4,
             filter=BMP280.IIR_FILTER_x2,
             standby=BMP280.T_STANDBY_1000)

aht20 = AHT20(addr=0x38)

while True:
    humidity = aht20.get_humidity()
    temp_aht20 = aht20.get_temperature()

    pressure_hpa = bmp.read_pressure()
    pressure_mmhg = pressure_hpa * CONVERT_HPA_MMHG
    temp_bmp280 = bmp.read_temperature()  # + OFFSET_TEMPERATURE

    print("Pressure (hPa): %s - (mmHg): %s, Temp_BMP280 (C): %s, Temp_AHT20 (C): %s, Humidity: %s" % (
        round(pressure_hpa, 2), round(pressure_mmhg, 2),
        round(temp_bmp280, 2), round(temp_aht20, 2),
        round(humidity, 2)))
    sleep(1)
# print("Temperature (°C): " + str(temp))
