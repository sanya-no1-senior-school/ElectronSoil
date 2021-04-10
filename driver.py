import threading
from PIL import Image,ImageDraw,ImageFont
import os
import time
import base64
import io
import json
import picamera
from peripheral import Peripheral_Init,GetDHT11,WP_AutoShutdown,Peripheral_Shutdown,WP_Shutdown



class CaptureThd(threading.Thread):
    t_start = None
    t_end=None
    stream:io.BytesIO = None
    camera=None
    picture_bin:bytes=None
    picture_ok=False
    capture_fps='0'
    time_slice=0

    lock:threading.RLock=None

    def __init__(self):
        threading.Thread.__init__(self)
        self.lock=threading.RLock()
        jsoncfg=open('config.json','r')
        json_str=jsoncfg.read()
        jsoncfg.close()

        CONFIG_JSONOBJ=json.loads(json_str)
        print("WEB SOCKET RASPBERRY CAMERA")
        print("========PARAMETERS=========")
        for key,value in CONFIG_JSONOBJ.items():
            print("%s: %s"%(key,value))

        self.camera=picamera.PiCamera()
        self.camera.resolution = (CONFIG_JSONOBJ["RESOLUTION_WIDTH"], CONFIG_JSONOBJ["RESOLUTION_HEIGHT"])# pi camera resolution
        self.camera.framerate = CONFIG_JSONOBJ["FRAME_RATE"] # frames/sec
        self.time_slice=1/CONFIG_JSONOBJ["FRAME_RATE"]
        self.camera.start_preview()
        time.sleep(3)                       # give 2 secs for camera to initilize
        print("CAMERA LOADED SUCCESSFULLY")
        self.t_start = time.time()
        self.stream = io.BytesIO()

    def run(self):
        for foo in self.camera.capture_continuous(self.stream, 'jpeg',use_video_port=True):
            self.stream.seek(0)
            self.picture_ok=False
            self.t_end=time.time()
            self.lock.acquire()
            self.picture_bin=self.stream.read()
            self.lock.release()
            #print("采集帧率：%.1f"%(1/(self.t_end-self.t_start)))
            self.capture_fps=1/(self.t_end-self.t_start)
            self.picture_ok=True
            self.stream.seek(0)
            self.stream.truncate()
            self.t_start=time.time()

class SensorThd(threading.Thread):
    temperature=0
    humidity=0
    status=''
    next_refresh_ts=0
    lock:threading.RLock=None

    def __init__(self):
        threading.Thread.__init__(self)
        self.lock=threading.RLock()

    def run(self):
        while True:
            ans:dict=GetDHT11()
            self.lock.acquire()
            if ans["result"]=="ok":
                self.temperature=ans["temperature"]
                self.humidity=ans["humidity"]
                self.status="温度：%.1f 湿度：%.1f"%(self.temperature,self.humidity)
            self.next_refresh_ts=time.time()+1.2
            self.lock.release()
            time.sleep(1.2)



class CaptureHelper:
    captureThd:CaptureThd=None
    sensorThd:SensorThd=None
    wp_AutoShutdown:WP_AutoShutdown=None
    water_pump=False

    def __init__(self):
        self.captureThd=CaptureThd()
        self.captureThd.setDaemon(True)
        self.captureThd.start()
        Peripheral_Init()
        self.sensorThd=SensorThd()
        self.sensorThd.setDaemon(True)
        self.sensorThd.start()

        # 用于文字边框展示，传入draw,坐标x,y，字体，边框颜色和填充颜色
    def text_border(self,draw,text, x, y, font, shadowcolor, fillcolor):
        # thin border
        draw.text((x - 1, y), text, font=font, fill=shadowcolor)
        draw.text((x + 1, y), text, font=font, fill=shadowcolor)
        draw.text((x, y - 1), text, font=font, fill=shadowcolor)
        draw.text((x, y + 1), text, font=font, fill=shadowcolor)
    
        # thicker border
        draw.text((x - 1, y - 1), text, font=font, fill=shadowcolor)
        draw.text((x + 1, y - 1), text, font=font, fill=shadowcolor)
        draw.text((x - 1, y + 1), text, font=font, fill=shadowcolor)
        draw.text((x + 1, y + 1), text, font=font, fill=shadowcolor)
    
        # now draw the text over it
        draw.text((x, y), text, font=font, fill=fillcolor)

    def ImageText(self,imgbyt,sentences):
        bio=io.BytesIO(imgbyt)
        ttfont = ImageFont.truetype("Deng.ttf",14)
        image:Image=Image.open(bio)
        image=image.resize((320,240),Image.ANTIALIAS)
        d_draw=ImageDraw.Draw(image)
        cnt=0
        for i in sentences:
            self.text_border(d_draw,i,5,5+16*cnt,ttfont,(100,100,100),(245,245,245))
            cnt=cnt+1
        bio1=io.BytesIO()
        image.save(bio1,format='jpeg',quality=55)
        return bio1.getvalue()

    def GetSingleImageBase64(self,packet_timestamp):
        ts=int(time.time()*1000)
        deltaTime=ts-packet_timestamp
        ping_status='Ping:%d ms'%deltaTime
        while self.captureThd.picture_ok is False:
            time.sleep(self.captureThd.time_slice/10)
            print('Waiting for SYNC')
        img_fps='图像采集帧率：%.1f'%((self.captureThd.capture_fps))
        wp_status='水泵状态：'
        if self.water_pump:
            wp_status+="WORKING"
        else:
            wp_status+="SHUTDOWN"
        
        sensor_refresh_time="传感器刷新：%04d ms"%((self.sensorThd.next_refresh_ts-time.time())*1000)
        #bytdata=self.ImageText(self.captureThd.picture_bin,[ping_status,img_fps\
        #    ,wp_status,self.sensorThd.status,sensor_refresh_time,\
        #    time.strftime("%a %b %d %H:%M:%S",time.localtime())])
        bytdata=self.ImageText(self.captureThd.picture_bin,[ping_status,img_fps\
            ,wp_status,self.sensorThd.status,sensor_refresh_time,\
            time.strftime("%a %b %d %H:%M:%S",time.localtime())])
        base64_byt=base64.b64encode(bytdata)
        return base64_byt.decode(encoding='utf-8').replace('"','')

    def WP_Set(self,how):
        if how==True:
            self.wp_AutoShutdown=WP_AutoShutdown(self)
            self.wp_AutoShutdown.start()
        else:
            self.wp_AutoShutdown=None
            self.water_pump=False
            WP_Shutdown()
        
