import socket
import time
import io
import time
import threading
import picamera
import numpy as np
from PIL import Image
import cv2 
import datetime
import os
import RPi.GPIO as GPIO
from matplotlib import pyplot as plt
import math
import logging 
#from multiprocessing import Process, Queue
import  queue

import sys
import logging
from psutil import virtual_memory

logger=logging.getLogger('debug')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(relativeCreated)6d %(message)s')
fh=logging.FileHandler('./debug.log')
fh.setFormatter(formatter)
logger.addHandler(fh)

q = queue.Queue(-1)

flag_toggele_top_camera=0
last_time_bee_enter=0


#set up UDP
#def UDP(
UDP_IP="192.168.1.20"
UDP_PORT=5005

#sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) # UDP


global done
done = False
global q_done
q_done = False
# Create a pool of image processors
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)
GPIO.setup(5, GPIO.IN)   #bailout button
GPIO.output(23, 1)

DATE_FMT_STR='%Y-%m-%d_%H-%M-%S'
DATE_FMT_STR_IMG='%Y-%m-%d_%H-%M-%S_%f'

def get_run_count(runFile='runCount.dat'):
    '''
    Get the current run count, increment, and return
    '''
    fh=open(runFile,'r')
    s=fh.readline()
    fh.close()
    count=int(s)
    fh=open(runFile,'w')
    fh.write(str(count+1) + '\n')
    
    fh.close()
    return count

def format_folder(dt):
    '''
    Create folder and return save_prefix
    '''
    usb_dir=''
    #Check if a usb key is mounted
    if not os.system('lsblk | grep sda1'):
        usb_dir = '/media/pi/98DA-5580/'
    else:
        print('WARNING: Did not find usb-key, writing to local dir.')
        
    pref=dt.strftime('__' + DATE_FMT_STR)
    pref = usb_dir + str(get_run_count()) +pref 
    os.mkdir(pref)
    os.mkdir(pref + '/var')
    return pref + '/'


save_prefix=format_folder(datetime.datetime.today())
print (save_prefix)

#consumers
consumers=[]
def consumer(q):
    global q_done
    while not q_done:
        try:
            image,name=q.get(timeout=5)
            cv2.imwrite(name,np.array(image))
            logger.info(name+strftime("%H:%M:%S", localtime()))
        except:
            logger.debug("timeout_queue, q_done: "+str(q_done))
            
    logger.debug("end of process. q_done: "+str(q_done))
    
for i in range(2):
    p=threading.Thread(target=consumer,args=(q,))
    p.daemon=True    
    consumers.append(p)
    p.start()


def create_opencv_image_from_stringio(img_stream, cv2_img_flag=0):
    img_stream.seek(0)
    img_array = np.asarray(bytearray(img_stream.read()), dtype=np.uint8)
    return cv2.imdecode(img_array, cv2_img_flag)

class ImageProcessor(threading.Thread):
    def __init__(self):
        super(ImageProcessor, self).__init__()
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.start()
        self.cnt=0
        self.name=""
        
    def run(self):
        # This method runs in a separate thread
        global flag_toggele_top_camera
        global last_time_bee_enter
        while not self.terminated:
            
            if self.event.wait(1):
                try:
                    
                    self.stream.seek(0)
                    
                    #img_array = np.asarray(bytearray(self.stream.read()), dtype=np.uint8)
                    #cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    
                    origin=Image.open(self.stream).crop((0,90,640,400))
                    gray=origin.convert('L')
                    
                    pxl_count=sum(sum(np.uint16(gray)/255))
                   # print(self.cnt,"",pxl_count)
        
                    if (pxl_count<90000):
                         #print(self.cnt,"",pxl_count)
                         
                         if(virtual_memory().percent>80):
                             time.sleep(0.8)
                             print("exceed 80 memory")
                             logger.info("mem: %d 0.5"%virtual_memory().percent)
                         try:
                             q.put((origin,self.name))
                             logger.debug("cnt: %d size: %d memory: %d"%(self.cnt,q.qsize(),virtual_memory().percent))
                         except:
                             print("error in putting")
                             logger.debug("error in putting")

                         #print("cnt: %d size: %d memory: "%(self.cnt,q.qsize(),virtual_memory().percent))
                      
                         


                    
                        
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()
                    # Return ourselves to the pool
                    with lock:
                        pool.append(self)
                        #if flag_toggele_top_camera==0 and pxl_count<90000:
                        #if pxl_count<90000:
                            #try:
                                #message="start %2d"%time.time()
                                #sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
                            #except:
                                #print("error in sending")




def streams():
    
    global done 
    global cnt
    global test
    b=0
    global a
    c=a
    while not done:
        with lock:
            
            if pool:
                processor = pool.pop()
                cnt+=1
            else:
                processor = None
                
        if processor:
            if cnt %50==0 and cnt >0:
                if b:
                    c=b
                b=time.time()
                #print('Captured %d frames at %.2ffps' % (50,50 / (b - c)))
                logger.debug('Captured %d frames at %.2ffps' % (50,50 / (b - c)))
            
            processor.cnt=cnt
            processor.name=save_prefix+'%04d.jpg'%(processor.cnt)
            yield processor.stream
            processor.event.set()
            
            
        else:
            # When the pool is starved, wait a while for it to refill
            time.sleep(0.1)



        

#flag to indicate the top camera to start
top_camera=0
last_time_bee_enter=0


lock = threading.Lock()
pool = []
cnt = 0
test=0





'''Dictionary for bee enter/exit events'''
bee_log_dict={-1: {'entries':[], 'exits': []} }
bee_time={}

start_time=time.time()
bee_log_dict['start_time']=start_time
bee_log_dict['start_time_iso']=datetime.datetime.today().isoformat()

camera=picamera.PiCamera()
pool = [ImageProcessor() for i in range(6)]
width,height=640,480
camera.resolution = (width,height)
camera.iso = 800
camera.shutter_speed=1000
camera.framerate = 60
time.sleep(2)
camera.vflip=True
camera.hflip=True

def GPIO5_callback(channel):
    print("when pushed: ",q.qsize)

    global done
    done =True
    print("exit")
    while pool:
        with lock:
            processor = pool.pop()
        processor.terminated = True
        processor.join()
    
    
    
    #f.close()


GPIO.add_event_detect(5, GPIO.RISING, callback=GPIO5_callback, bouncetime=300)



global a
a=time.time()
#camera.start_preview()
camera.capture_sequence(streams(), use_video_port=True)
#camera.stop_preview()
b=time.time()
print('Captured %d frames at %.2ffps' % (cnt,cnt / (b - a)))

# Shut down the processors in an orderly fashion


while pool:
    with lock:
        processor = pool.pop()
    processor.terminated = True
    processor.join()

camera.close()

print("not last ",q.qsize())
if (q.qsize()>300):
    for i in range(2):
        p=threading.Thread(target=consumer,args=(q,))
        p.daemon=True    
        consumers.append(p)
        p.start()
        
while(q.qsize()):
    GPIO.output(22, True)
    print("wait: %d"%q.qsize())
    time.sleep(5)
    
print("last ",q.qsize())

q_done=True

while consumers:
    p=consumers.pop()
    p.join()
    
GPIO.output(22, False)
GPIO.output(23, False)
GPIO.cleanup()
camera.close()