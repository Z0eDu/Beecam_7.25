import io
import time
import threading
import picamera
import numpy as np
from PIL import Image, ImageFile
import random
import cv2 
import datetime
import os
import RPi.GPIO as GPIO
#from keras.models import load_model
from matplotlib import pyplot as plt
import math
import queue 
#import tensorflow as tf
#from tensorflow.python.keras.backend import set_session
from multiprocessing import Process
import socket
from psutil import virtual_memory
import sys
import logging 

#detection
#session = tf.Session()
#graph=tf.get_default_graph()
#set_session(session)
#model = load_model('tag_model.h5')
os.system('bash /home/pi/Desktop/code/start.sh') 
logger=logging.getLogger('debug')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(relativeCreated)6d %(message)s')
fh=logging.FileHandler('./debug.log')
fh.setFormatter(formatter)
logger.addHandler(fh)

GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(5, GPIO.IN)   #bailout button


threads=[]
q=queue.Queue(maxsize=-1)
data=0

#udp
UDP_IP="192.168.1.20"
UDP_PORT=5005
#sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
#sock.settimeout(10)
#sock.bind((UDP_IP,UDP_PORT))


q_done=False
save_cnt=0

class Tag_detect(threading.Thread):
    def __init__(self):
        super(Tag_detect, self).__init__()
        self.cnt=0
        self.name=""
        self.terminated = False
        self.event = threading.Event()
        self.auto_join=False
#     def tag_read(self,image):
#         global session
#         global graph
#         set_session(session)
#         image = image.reshape(1,90,90,1)
#         image = image.astype('float32')
#         image /= 255
#         with graph.as_default():
#             prediction = model.predict(image,batch_size=1,verbose=1)
#             pred_class = np.argmax(prediction,axis = 1)
#             pred_class = pred_class
#             return pred_class


    def tag_extract(self,img):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (45, 20, 0), (100, 200,255))
        imask = mask>0
        green = np.zeros_like(img, np.uint8)
        green[imask] = img[imask]
        gray = cv2.cvtColor(green, cv2.COLOR_BGR2GRAY)

        contours, hierarchy = cv2.findContours(
            gray,
            cv2.RETR_LIST,
            cv2.CHAIN_APPROX_SIMPLE
        )
        roi=0
        detected_circle=0
        for contour in contours:
            area = cv2.contourArea(contour)

            if area>4200:
                br = cv2.boundingRect(contour)
                m = cv2.moments(contour)
                center = (int(m['m10'] / m['m00']), int(m['m01'] / m['m00']))
                a,b=center
                cv2.circle(green, center, 3, (255, 0, 0), -1)
                cv2.drawContours(green, contour, -1, (0,255,0), 3)
                r=45
                top=0
                bottom=0
                left=0
                right=0
                t1=b-r
                b1=b+r
                l1=a-r
                r1=a+r
                
                #print(b-r,b+r,a-r,a+r)
                if a+r>640:
                    right=a+r-640
                    r1=640
                if b+r>480:
                    bottom=b+r-480
                    b1=480
                if b-r<0:
                    top=0-b+r
                    t1=0
                if a-r<0:
                    left=0-a+r
                    l1=0
                roi = img[t1:b1,l1:r1]
                if top<10 and right <10 and bottom<10 and left<10:
                    detected_circle=1
                    h, s, v = cv2.split(roi)                        
                    image = cv2.copyMakeBorder( v, top, bottom, left, right, cv2.BORDER_CONSTANT,value=74)
                    
                    return (True,image)
        return (False,None)
                        
    

    def run(self):
        
        global save_cnt
        while not self.terminated:
            if (q.qsize()):
                try:
                    GPIO.output(23, 0)
                    image,self.name,self.tag_name=q.get(timeout=2)
                    with lock:
                        local_cnt=save_cnt
                        save_cnt+=1
                    #you can comment out this if you only want to save tags.
                    #this is the whole image pushed to the queue
                    cv2.imwrite(self.name+'%d.jpg'%(local_cnt),np.array(image))
                    
                    flag,tag=self.tag_extract(np.array(image))
                    
                    if flag:
                        #this is the tag if the image has one
                        
                        cv2.imwrite(self.tag_name+'%d.jpg'%(local_cnt),tag)
                        logger.info('%d-'%(local_cnt)+time.strftime("%H:%M:%S", time.localtime())+".jpg")
                except queue.Empty as error:
                    print("Writer: Timeout occurred {}".format(str(error)))
                    logger.info("Writer: Timeout occurred {}".format(str(error)))
                    pass
            else:
                GPIO.output(23, 1)
                time.sleep(1)
        self.event.clear()
        if self.auto_join:
            pool3.append(self)
    
    

# Create a pool of image processors


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
        usb_dir = '/media/pi/4139-6134/'
    else:
        print('WARNING: Did not find usb-key, writing to local dir.')
        
    pref=dt.strftime('_' + DATE_FMT_STR)
    pref = usb_dir + str(get_run_count()) +pref 
    os.mkdir(pref)
    os.mkdir(pref + '/var')
    return pref + '/'


save_prefix=format_folder(datetime.datetime.today())
print (save_prefix)
logger.info("\n")
logger.info(save_prefix)

##

class ImageProcessor(threading.Thread):
    def __init__(self):
        super(ImageProcessor, self).__init__()
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.start()
        self.cnt=0
        self.name=""
        self.tag_name=""
    def run(self):
        # This method runs in a separate thread

        while not self.terminated:
            
            if self.event.wait(1):
                try:
                    flag=0              
                    self.stream.seek(0)
                    #ImageFile.LOAD_TRUNCATED_IMAGES=True
                    im=Image.open(self.stream)
                    origin=im.crop((0,120,640,480))
                    gray=origin.convert('L')
                    pxl_count=sum(sum(np.uint16(gray)/255))
                    if pxl_count<87000:
                        if(virtual_memory().percent>80):
                                 time.sleep(0.8)
                                 logger.info("cnt: %d size: %d memory: %d"%(self.cnt,q.qsize(),virtual_memory().percent))
                    
                        
                        q.put((origin,self.name,self.tag_name))
                        print("qsize ",q.qsize(),pxl_count)
                    
                    #cv2.imwrite(self.name,np.array(origin))
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()
                    # Return ourselves to the pool
                    with lock:
                        pool.append(self)




def streams():
    
    global done 
    global cnt

    b=0
    global a
    c=a
    last_start=0
    GPIO.output(22, 1)
    

    while not done:
    
        with lock:
            
            #print(pool)
            
            if pool :
                
                processor = pool.pop()
                
            else:
                processor = None
        if processor:
            if cnt %50==0:
                if b:
                    c=b
                b=time.time()
                #print ('cnt',str(cnt))
                #print('Captured %d frames at %.2ffps' % (50,50 / (b - c)))
                logger.debug('Captured %d frames at %.2ffps' % (50,50 / (b - c)))
            cnt+=1
            #this cnt is the order of image from the start. even though some are not saved
            processor.cnt=cnt
            processor.name=save_prefix
            processor.tag_name=save_prefix+'var/'
            yield processor.stream
            processor.event.set()

        else:
            # When the pool is starved, wait a while for it to refill
            time.sleep(0.01)
    #except:
    #    logger.info('except: '+time.strftime("%X"))
    #    pass


        



done= False
lock = threading.Lock()
pool = []
cnt = 0



'''Dictionary for bee enter/exit events'''
bee_log_dict={-1: {'entries':[], 'exits': []} }
bee_time={}
start_time=time.time()
start_time=time.time()
bee_log_dict['start_time']=start_time
bee_log_dict['start_time_iso']=datetime.datetime.today().isoformat()

#camera setup

camera=picamera.PiCamera()
camera.resolution = (640, 480)
camera.iso = 800
camera.shutter_speed=800
camera.framerate = 45
pool = [ImageProcessor() for i in range(8)]
pool2 = [Tag_detect() for i in range(2)]

time.sleep(2)

a=time.time()
bail_out=0
#GPIO setup
def GPIO5_callback(channel):
    global bail_out
    if not bail_out:
        frames=cnt
        global a        
        print("when pushed: ",q.qsize())
        global done
        done =True
        print("exit")
        bail_out=1

    


GPIO.add_event_detect(5, GPIO.RISING, callback=GPIO5_callback, bouncetime=3000)



        


for i in pool2:
    
    i.event.set()
    i.start()
   
start_time=time.time()
flag_start_capture=0
#camera.start_preview()
camera.capture_sequence(streams(), use_video_port=True)
#camera.stop_preview()


# flag=0
# last_entry=0
# sock.settimeout(3)
# while not done:
#     try:
#         d,addr =sock.recvfrom(1024)
#         d=d.decode()
#         print("flag",flag)
#     #print(int(d[6:])-last_entry)
#         if flag==0:
#             flag=1
#             last_entry=int(d[6:])
#             for extra_saver in pool3:
#                 extra_saver.terminate=True
#             print("before loop")
#             for i in pool2:
#                 print("loop")
#                 i.event.set()
#                 i.start()
#             
#         if (int(d[6:])-last_entry>5):
#             print("stop")
#             for i in pool3:
#                 i.terminate=False
#                 print("loop2")
#                 i.auto_join=True
#                 i.event.set()
#                 i.start()
#             flag==0
#             
#         last_entry=int(d[6:])
#     except:
#         pass



#sock.close()


# Shut down the processors in an orderly fashion


GPIO.output(22, 0)
while pool:
    with lock:
        processor = pool.pop()
    processor.terminated = True
    logger.info("pool2 join")#you can add thread name 
    processor.join()


flag_pool3=0
#if qsize is large, we use more savers to save images. speed up the shutdown
if (q.qsize()>400):
    pool3 = [Tag_detect() for i in range(2)]
    time.sleep(0.1)
    flag_pool3=1
    for i in pool3:
        i.auto_join=True
        print("loop3")
        i.event.set()
        i.start()
        
while(q.qsize()):
    GPIO.output(22, False)
    print("wait: %d"%q.qsize())
    logger.info("wait: %d"%q.qsize())
    time.sleep(5)
    GPIO.output(22, True)
print("last ",q.qsize())
logger.info("last %d"%q.qsize())

while pool2:
    with lock:
        saver= pool2.pop()
    saver.terminated = True
    saver.join()
    logger.info("join2")


if flag_pool3:
    while pool3:   
        with lock:
            saver= pool3.pop()
        saver.terminated=True
        saver.join()
        logger.info("join3")
    

GPIO.cleanup()
camera.close()