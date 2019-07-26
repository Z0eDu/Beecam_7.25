import RPi.GPIO as GPIO
import time as t
import os
import subprocess
import sys
import datetime
import cv2
import numpy as np
import json
from picamera import PiCamera
import file_analyze as ana
import threading
import serial
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera
from argparse import ArgumentParser
import apriltag
'''Needed to use the PI screen with the gui display'''
#piTFT environment variables

parser = ArgumentParser(
        description='test apriltag Python bindings')
    
apriltag.add_arguments(parser)
options = parser.parse_args()


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


GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.IN)   #bailout button
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP)    #beam sensor 1
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)   #beam sensor 2
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)    #beam sensor 1
GPIO.setup(20, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)



# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera(resolution=(640,480), framerate=32)
camera.iso = 800
camera.exposure_mode='night'
camera.shutter_speed=2000
t.sleep(2)
print camera.shutter_speed
rawCapture = PiRGBArray(camera, size=(640,480))


start_time=t.time()
bee_log_dict['start_time']=start_time
bee_log_dict['start_time_iso']=datetime.datetime.today().isoformat()

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


pics_taken = {}





def GPIO27_callback(channel):
    if not GPIO.input(27):
        global quit_program
        quit_program = True
        for i in pics_taken.keys():
            pics_taken[i].join()
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
thread_cnt=0

time_of_clock=t.time()

while(not quit_program):
    
    
    if lock[0]=='unlocked' and not pics_taken=={}:  
        if thread_cnt<cnt:
            thread_cnt+=1
            print 'thread: ',str(thread_cnt)
            pics_taken[thread_cnt].start()
            
        #except:
            #print 'exceed'
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
            time_of_clock=t.time()
        
        elif t.time()-time_of_clock>170:
               
            t.sleep(1)
            time_of_clock=t.time()
            GPIO.cleanup(24)
            t.sleep(1)

        if (t.time()-trigger_t<interval):
            
            
            pre_num_name=num_name
            cnt = cnt + 1
            print ('cnt: '+str(cnt))

            time_pre_image=t.time()

            camera.capture(rawCapture, format="bgr", use_video_port=True)
            image = rawCapture.array
            cv2.imwrite(save_prefix+"top" + str(cnt) + ".jpg", image)
            
            rawCapture.truncate(0)
            
            print("Elapsed Time for capture: ", str(t.time()-time_pre_image))
            
            save_time=datetime.datetime.today().isoformat()[:-7]
            thread=threading.Thread(target=ana.analyze,args=(lock,options,pre_detection,save_time,bee_time,pre,cnt,pre_num_name,save_prefix,bee_log_dict,start_time))
        
            pics_taken[cnt]=thread
            
            

            
            
    
           
print('Bye bye!')

