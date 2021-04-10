import RPi.GPIO as GPIO
import time
import threading

DHT11_GPIO_PIN=4
RELAY_GPIO_PIN=17

def Peripheral_Init():
    GPIO.setmode(GPIO.BCM)		#以BCM编码格式
    GPIO.setup(DHT11_GPIO_PIN, GPIO.OUT)
    GPIO.setup(RELAY_GPIO_PIN, GPIO.OUT)

def GetDHT11():
    data = []			#温湿度值
    j = 0				#计数器
    time.sleep(0.2)			#时延一秒
    GPIO.setup(DHT11_GPIO_PIN, GPIO.OUT)
    GPIO.output(DHT11_GPIO_PIN, GPIO.LOW)
    time.sleep(0.02)		#给信号提示传感器开始工作
    GPIO.output(DHT11_GPIO_PIN, GPIO.HIGH)
    
    GPIO.setup(DHT11_GPIO_PIN, GPIO.IN)
    
    while GPIO.input(DHT11_GPIO_PIN) == GPIO.LOW:
        continue
    
    while GPIO.input(DHT11_GPIO_PIN) == GPIO.HIGH:
        continue
    
    while j < 40:
        k = 0
        while GPIO.input(DHT11_GPIO_PIN) == GPIO.LOW:
            continue
        
        while GPIO.input(DHT11_GPIO_PIN) == GPIO.HIGH:
            k += 1
            if k > 100:
                break
        
        if k < 8:
            data.append(0)
        else:
            data.append(1)
    
        j += 1
    
    humidity_bit = data[0:8]		#分组
    humidity_point_bit = data[8:16]
    temperature_bit = data[16:24]
    temperature_point_bit = data[24:32]
    check_bit = data[32:40]
    
    humidity = 0
    humidity_point = 0
    temperature = 0
    temperature_point = 0
    check = 0
    
    for i in range(8):
        humidity += humidity_bit[i] * 2 ** (7 - i)				#转换成十进制数据
        humidity_point += humidity_point_bit[i] * 2 ** (7 - i)
        temperature += temperature_bit[i] * 2 ** (7 - i)
        temperature_point += temperature_point_bit[i] * 2 ** (7 - i)
        check += check_bit[i] * 2 ** (7 - i)
    
    tmp = humidity + humidity_point + temperature + temperature_point		#十进制的数据相加
    
    if check == tmp:								#数据校验，相等则输出
        #GPIO.cleanup()
        return {"result":"ok","temperature":temperature,"humidity":humidity}
    else:										#错误输出错误信息，和校验数据
        #GPIO.cleanup()
        return {"result":"failed"}


class WP_AutoShutdown(threading.Thread):
    setback=None

    def __init__(self,setback):
        threading.Thread.__init__(self)
        self.setback=setback

    def run(self):
        GPIO.output(RELAY_GPIO_PIN, GPIO.HIGH)
        self.setback.water_pump=True
        time.sleep(5)
        GPIO.output(RELAY_GPIO_PIN, GPIO.LOW)
        self.setback.water_pump=False
        return

def WP_Shutdown():
    GPIO.output(RELAY_GPIO_PIN, GPIO.LOW)

def Peripheral_Shutdown():
    GPIO.cleanup()