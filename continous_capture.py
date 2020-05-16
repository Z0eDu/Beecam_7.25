import io
import time
import threading
import picamera
import numpy as np
from PIL import Image
import random
import cv2 as cv
import datetime
import os
# Create a pool of image processors

done= False
lock = threading.Lock()
pool = []
cnt = 0
test=0
backSub =cv.createBackgroundSubtractorMOG2() 

DATE_FMT_STR='%Y-%m-%d_%H-%M-%S'
DATE_FMT_STR_IMG='%Y-%m-%d_%H-%M-%S_%f'


'''Dictionary for bee enter/exit events'''
bee_log_dict={-1: {'entries':[], 'exits': []} }
bee_time={}

start_time=time.time()
bee_log_dict['start_time']=start_time
bee_log_dict['start_time_iso']=datetime.datetime.today().isoformat()

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
        
    pref=dt.strftime('__' + DATE_FMT_STR)
    pref = usb_dir + str(get_run_count()) +pref 
    os.mkdir(pref)
    os.mkdir(pref + '/var')
    return pref + '/'

save_prefix=format_folder(datetime.datetime.today())

print (save_prefix)

class ImageProcessor(threading.Thread):
    def __init__(self):
        super(ImageProcessor, self).__init__()
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.start()
        self.cnt=0
        
    def run(self):
        # This method runs in a separate thread
        global cnt
        global test
        while not self.terminated:
            
            if self.event.wait(1):
                try:
                    flag=0
                    self.stream.seek(0)
                    origin=Image.open(self.stream).crop((7,130,640,480))
                    f=origin.convert('LA')
                    
                    print (self.cnt)
                    threshold = 30
                    im = f.point(lambda p: p > threshold and 255)  
               
                    fp=np.uint16(f)/255
               
                    pxl_count=sum(sum(fp))
                    print(pxl_count)
                    if pxl_count[0] <57000:
                        flag=1
                    #print(save_prefix+str(self.cnt)+'.jpg')
                    origin.save(save_prefix+str(self.cnt)+'.jpg')
                    #origin.save("/home/pi/Desktop/4/"+str(self.cnt)+'.jpg')
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
    global test
    b=0
    global a
    c=a
    while not done:
        with lock:
            
            if cnt>1500:
                done=True
            
            if pool:
                processor = pool.pop()
            else:
                processor = None
                
        if processor:
            if cnt %10==0:
                if b:
                    c=b
                b=time.time()
                #print ('cnt',str(cnt))
                print('Captured %d frames at %.2ffps' % (10,10 / (b - c)))
            cnt+=1
            processor.cnt=cnt
            yield processor.stream
            processor.event.set()
            
        else:
            # When the pool is starved, wait a while for it to refill
            time.sleep(0.1)

with picamera.PiCamera() as camera:
    #camera.start_preview()
    pool = [ImageProcessor() for i in range(8)]
    camera.resolution = (640, 480)
    camera.iso = 800
    camera.shutter_speed=2000
    camera.framerate = 60
    time.sleep(2)

    global a
    a=time.time()
    camera.start_preview()
    camera.capture_sequence(streams(), use_video_port=True)
    camera.stop_preview()
    b=time.time()
    frames=100
    print('Captured %d frames at %.2ffps' % (
    frames,
    frames / (b - a)))
    #camera.stop_preview()
# Shut down the processors in an orderly fashion
while pool:
    with lock:
        processor = pool.pop()
    processor.terminated = True
    processor.join()
