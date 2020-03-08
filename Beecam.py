import RPi.GPIO as GPIO
import time as t
import os
import sys
import datetime
import cv2
import numpy as np
from picamera import PiCamera
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera

import threading

'''Needed to use the PI screen with the gui display'''
#piTFT environment variables

          
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
DATE_FMT_STR_IMG='%m-%d_%H-%M-%S_%f'

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
    return pref + '/'


def save_img(lock,name_str,img):
    lock[0]='locked'
    print('writing image' + name_str)
    cv2.imwrite(name_str,img)
    lock[0]='unlocked'

GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.IN)   #bailout button
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP)    #beam sensor 1
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)   #beam sensor 2
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)   #Used for scale 


# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera(resolution=(640,480), framerate=5)
camera.iso = 800
camera.exposure_mode='night'
camera.shutter_speed=2000
t.sleep(2)
print camera.shutter_speed
rawCapture = PiRGBArray(camera, size=(640,480))
GPIO.cleanup(21)

start_time=t.time()

save_prefix=format_folder(datetime.datetime.today())

sensor1 = False     #exiting sensor
sensor2 = False     #entering sensor
current_time = 0.0
hasPollen = False
cnt = 0
num_name = ""

pre_detection={}

global paused
paused = False

global quit_program
quit_program = False

def GPIO27_callback(channel):
    if not GPIO.input(27):
        global quit_program
        quit_program = True
        camera.close()                   
        GPIO.cleanup()

        
GPIO.add_event_detect(27, GPIO.BOTH, callback=GPIO27_callback, bouncetime=300)

sensor1,sensor2=False,False
sensor_on_times=0
enter,exitt=False,False
start_time=t.time()
trigger_t=0
interval=5
pre=['']

lock = ['unlocked']
thread_cnt=-1

time_of_clock=t.time()

threads=[]



while(not quit_program):

    '''
    Only have one image written at a time.
    '''
    if lock[0]=='unlocked' and not len(threads)==0:  
        threads.pop(0).start()
    
    if (not paused): 
        pre_sensor1,pre_sensor2=sensor1,sensor2
        sensor1,sensor2=not GPIO.input(5),not GPIO.input(26)

        if(not sensor1 and pre_sensor1):
            enter=True
            leave=False
            trigger_t=t.time()
            time_of_clock=t.time()
            
        elif (not sensor2 and pre_sensor2):
            leave=True
            enter=False
            trigger_t=t.time()
            time_of_clock=t.time() #scale
        
        elif t.time()-time_of_clock>170:
            GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)   
            t.sleep(1)
            GPIO.cleanup(21)
            GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)   
            t.sleep(1)
            GPIO.cleanup(21)

        if (t.time()-trigger_t<interval):
            pre_num_name=num_name
            cnt = cnt + 1
            print ('cnt: '+str(cnt))

            time_pre_image=t.time()

            dt=datetime.datetime.today()
            
            camera.capture(rawCapture, format="bgr", use_video_port=True)
            image = rawCapture.array
            #cv2.imwrite(save_prefix+"top" + str(cnt) + ".jpg", image)
            #image=np.ones((2,2))
            
            
            #imb=image.copy()
            #cv2.imwrite(save_prefix+dt.strftime(DATE_FMT_STR_IMG) + "_" + str(cnt) + ".jpg", image)
            im_name=save_prefix+dt.strftime(DATE_FMT_STR_IMG) + "_side_" + str(cnt) + ".jpg"
            #save_img(im_name,image.copy())

            threads.append(threading.Thread(target=save_img,args=(lock,im_name,image.copy())))

            print(str(cnt))
            
            rawCapture.truncate(0)
            
            print("Elapsed Time for capture: ", str(t.time()-time_pre_image))

            

            
            
    
           
print('Bye bye!')

