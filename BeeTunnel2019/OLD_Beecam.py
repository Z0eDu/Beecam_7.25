import RPi.GPIO as GPIO
import time as t
import datetime
import os
import sys
import logging
import logging.handlers
import cv2
from picamera import PiCamera
import threading
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera

import tunnelconfig as tc #configuration file for each tunnel


'''
This script should start automatically even when no
interactive Bash shell has been started.

The following lines should be added to /etc/rc.local:

cd /home/pi/BeeTunnel2019
sudo python Beecam.py > beecam.log 

If you want to start and interact with the script after
booting up with a screen and keyboard, first kill Beecam process.
Look up the PID with

>> ps -axf | grep Beecam

and then kill it 

>> sudo kill PID
'''

#DEBUG=True
DEBUG=False

'''
Set up logging
'''

logger=logging.getLogger('tunnel')
logger.setLevel('DEBUG')

stdout_handler = logging.StreamHandler()

formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")

stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

logger.info('Hello Logger!')

def crop_img(src,xmin=tc.BBXmin,xmax=tc.BBXmax,ymin=tc.BBYmin,ymax=tc.BBYmax):
    '''
    Default values for crop
    src should be a back and white image
    The cropping in this version is broken, and it ONLY crops in 
    the Y direction for some reason. This crop fuction flips the flips back
    '''
    cropy=src[ymin:ymax][:]
    tmp=cropy.transpose()
    tmp2=tmp[xmin:xmax][:]
    
    return tmp2.transpose() 


'''Dictionary for bee enter/exit events'''
bee_log_dict={-1: {'entries':[], 'exits': []} }
bee_time={}

        
def get_run_count(runFile='runCount.dat'):
    '''
    Get the current run count, increment, and return
    '''
    fh=open(runFile,'r')
    s=fh.readline()
    fh.close()
    cnt=int(s)+1
    fh=open(runFile,'w')
    fh.write(str(cnt) + '\n')
    fh.close()
    return cnt

DATE_FMT_STR='%Y-%m-%d_%H-%M-%S'
DATE_FMT_STR_IMG='%Y-%m-%d_%H-%M-%S_%f'

def format_folder(dt):
    '''
    Create folder and return save_prefix
    '''
    usb_dir=''
    #Check if a usb key is mounted
    if not os.system('lsblk | grep usb0'):
        usb_dir = '/media/usb0/'
    else:
        print('WARNING: Did not find usb-key, writing to local dir.')
        
    pref=dt.strftime('__' + DATE_FMT_STR)
    pref = usb_dir + 'run-' + str(get_run_count()) +pref 
    os.mkdir(pref)
    os.mkdir(pref + '/var')
    os.mkdir(pref + '/debug')
    return pref + '/'

def write_config_to_log():
    tcdict_keys=tc.__dict__.keys()
    for k in tcdict_keys:
        if not k[0]=='_':
            logger.info('config:'+ k + ':' + str(tc.__dict__[k]))
    
def save_img(name_str,img):
    '''
    Save image in prefix path that runs the background.
    Since writing to the USB key can be slow, this allows the 
    camera to capture image at the set frame rate store them in 
    memory and then finish writing them to disk later. 
    '''

    def thread_save_img(lock,name,img):
        lock[0]='locked'
        #log.info('writing image' + name_str)
        logger.info('writing image' + name_str)
        cv2.imwrite(save_prefix + name_str,img)
        lock[0]='unlocked'

    bg_threads.append(threading.Thread(target=thread_save_img,args=(lock,name_str,img.copy())))

    
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.IN)   #bailout button

GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP)    #beam sensor 1
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)   #beam sensor 2

GPIO.setup(20, GPIO.IN, pull_up_down=GPIO.PUD_UP)  #Led
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)  #scale


def toggle_scale(ttime=0.07):
    '''
    Pull down scale pin for ttime [70ms] to "press" power button
    '''
    GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  
    t.sleep(ttime)
    GPIO.setup(21, GPIO.IN)

def cycle_scale(ttime=0.07, itime=0.3):
    logger.info("Power cycling scale.")
    toggle_scale(ttime=ttime)
    t.sleep(itime)
    toggle_scale(ttime=ttime)




t.sleep(2)

start_time=t.time()
bee_log_dict['start_time']=start_time
bee_log_dict['start_time_iso']=datetime.datetime.today().isoformat()

save_prefix=format_folder(datetime.datetime.today())

file_handler = logging.FileHandler(save_prefix + 'tunnel.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)



# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera(resolution=tc.camera_resolution,
                  framerate=tc.camera_fps,
                  sensor_mode=tc.camera_mode)
                  
camera.zoom=tc.camera_zoom
camera.iso = tc.camera_iso
camera.exposure_mode=tc.camera_exposure_mode
camera.shutter_speed=tc.camera_shutter_speed

rawCapture = PiRGBArray(camera, size=tc.camera_resolution)

'''
#redundant wiht config file
logger.info('Camera ISO:' + str(camera.iso))
logger.info('Camera Shutter:' + str(camera.shutter_speed))
logger.info('Camera Resolution:' + str(camera.resolution))
'''

write_config_to_log()


sensor1 = False     #exiting sensor
sensor2 = False     #entering sensor
current_time = 0.0
hasPollen = False
cnt = 0
db_cnt = 0
num_name = ""

pre_detection={}

global paused
paused = False

global quit_program
quit_program = False

'''
List to hole backgound function calls
'''
bg_threads=[]


'''
Use the onboard stop switch
'''
def GPIO27_callback(channel):
    if not GPIO.input(27):
        global quit_program
        quit_program = True
        for t in bg_threads:
            t.join()
        GPIO.cleanup()

#GPIO.add_event_detect(27, GPIO.BOTH, callback=GPIO27_callback, bouncetime=300)

sensor1,sensor2=False,False
sensor_on_times=0
enter,exitt=False,False
start_time=t.time()
trigger_t=0
interval=5
pre=['']

lock = ['unlocked']

scale_reset_timer=t.time()

toggle_scale()

tare_again=False

while(not quit_program):
        
    if lock[0]=='unlocked' and not len(bg_threads)==0:
        bg_threads.pop(0).start()

    if (not paused): 
        pre_sensor1,pre_sensor2=sensor1,sensor2
        sensor1,sensor2=not GPIO.input(5),not GPIO.input(26)

        #Trigger on falling edge
        if(not sensor1 and pre_sensor1):

            enter=True
            leave=False
            trigger_t=t.time()
            scale_reset_timer=t.time()
            tare_again=True
            logger.info('Sensor 1 Triggered - Falling Edge')
            
        if (not sensor2 and pre_sensor2):

            leave=True
            enter=False
            trigger_t=t.time()
            scale_reset_timer=t.time()
            tare_again=True
            logger.info('Sensor 2 Triggered - Falling Edge')

        #Trigger on raising edge
        if(sensor1 and not pre_sensor1):

            enter=True
            leave=False
            trigger_t=t.time()
            scale_reset_timer=t.time()
            tare_again=True
            logger.info('Sensor 1 Triggered - Rising Edge')
            
        if (sensor2 and not pre_sensor2):

            leave=True
            enter=False
            trigger_t=t.time()
            scale_reset_timer=t.time()
            tare_again=True
            logger.info('Sensor 2 Triggered - Rising Edge')
        
        if t.time()-scale_reset_timer>170:

            logger.info('Scale reset timeout, cycling scale.')
            cycle_scale()
            scale_reset_timer=t.time()        
            
        if (t.time()-trigger_t<interval):
            
            '''
            Caputure image and threshold pixels 
            '''
            camera.capture(rawCapture, format="bgr", use_video_port=True)
            image = rawCapture.array

            #Convert and threshold
            image_BW=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
            val,image_TH=cv2.threshold(image_BW,tc.THRESHOLD,1,cv2.THRESH_BINARY)            

            #Crop and count (NEED TO UPCAST from 'uint8' othewise sum overflows without warning) 
            image_TH_C=crop_img(image_TH)
            pxl_count=sum(sum(image_TH_C.astype('uint16')))

            if DEBUG and db_cnt < 15:

                '''
                Save some pictures for debugging
                '''
                
                db_cnt=db_cnt+1

                logger.debug("Debug Counter= " + str(db_cnt) + "  Image Counter +1 = " + str(cnt))
                logger.debug('Pixel Count: ' + str(pxl_count))                            
                
                save_img("debug/DB_top" + str(db_cnt) + "BW_CROP.jpg", crop_img(image_BW))
                save_img("debug/DB_top" + str(db_cnt) + "TH_CROP.jpg", 255*image_TH_C)
                imgPaint=255*image_TH_C

            
                font= cv2.FONT_HERSHEY_SIMPLEX
                bottomLeftCornerOfText = (10,50)
                fontScale=1
                fontColor=(0,255,255)
                lineType=2

                cv2.putText(imgPaint,str(pxl_count), bottomLeftCornerOfText, font, fontScale,fontColor,lineType)
                save_img("debug/DB_top" + str(db_cnt) + "TH_CROP_CNT.jpg", imgPaint)
                save_img("debug/DB_top" + str(db_cnt) + ".jpg", image)
                              

            '''
            Only capture images with enough change dark pixels
            '''
            if(pxl_count < tc.PXLCountThresh):
                
                pre_num_name=num_name
                cnt = cnt + 1
                time_pre_image=t.time()


                dt=datetime.datetime.today()
                
                save_img(dt.strftime(DATE_FMT_STR_IMG)
                         + "_"+ tc.board_ID + "_"
                         + str(cnt) + ".jpg", image)

                logger.info("Capture time/pxl_count for "
                            + str(cnt) + ":"
                            + str(t.time()-time_pre_image) + ':'
                            + str(pxl_count))
		
                
            rawCapture.truncate(0)
        
        else: #Not currently in capture interval
            if tare_again:
                tare_again=False
                logger.info("Scale reset outside of capture interval.")
                cycle_scale()
           
logger.info('Bye bye!')

