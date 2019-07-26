#!/usr/bin/env python
'''Demonstrate Python wrapper of C apriltag library by running on camera frames.'''
from __future__ import division
from __future__ import print_function

import os
import time as t
import datetime
import json
import serial
from argparse import ArgumentParser
import cv2
import apriltag
import math
import glob

'''
def add_bee_event(pre,log,bee_ID=-1,event_time=0,dir_out=True):
    if not bee_ID in log.keys():
        log[bee_ID]={'entries':[], 'exits': []} 
    if dir_out: 
        pre[0]='enter'
        if (len(log[bee_ID]['entries'])>0):
            if((event_time-log[bee_ID]['entries'][-1])<2):
               log[bee_ID]['entries'][-1]=event_time
            else:
               log[bee_ID]['entries'].append(event_time)
        if (len(log[bee_ID]['entries'])==0):
            log[bee_ID]['entries'].append(event_time)
            
    if not dir_out: 
        print('exit',event_time,bee_ID)
        if (len(log[bee_ID]['exits'])==0):
            print('we are here2312')
            log[bee_ID]['exits'].append(event_time)
            pre[0]='exit'
        elif (pre[0]=='' or pre[0]=='enter'):
            print('we are here',pre)
            log[bee_ID]['exits'].append(event_time)
            pre[0]='exit'
'''     
                 


def analyze(lock,options,pre_detection,save_time,bee_time,pre,cnt,pre_num_name,save_prefix,bee_log_dict,start_time):
    lock[0]='locked'
    
    
    fh_id_log =  open(save_prefix  + 'ImgID.log'   ,'a')
    
    #record time for each picuture
    
    
    
    
    window = 'Camera'
    cv2.namedWindow(window)
    detector = apriltag.Detector(options,searchpath=apriltag._get_demo_searchpath())
    
   
    rgb = cv2.imread(save_prefix +" top" + str(cnt) + ".jpg")
    print(save_prefix +"top" + str(cnt) + ".jpg")
    while rgb is None:
            rgb = cv2.imread(save_prefix +"top" + str(cnt) + ".jpg")
            t.sleep(0.1)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    k=t.time()
    detections, dimg = detector.detect(gray, return_image=True)
    print ('detecting time:',t.time()-k)
    lock[0]='unlocked'
    num_detections = len(detections)
    print('Detected {} tags.\n'.format(num_detections))
    current_detection=[]
    overlay = rgb // 2 + dimg[:, :, None] // 2
    
    if len(detections):
        for i, detection in enumerate(detections):
            centerY = detection.center[1]
            #assume bee only travels one direction a time
            #if the tag first time appears, start append to the list until the tag dispears
            current_detection.append(detection[1])
            print ('previous',pre_detection)
            if detection[1] in pre_detection.keys():
                if (float(centerY)-float(pre_detection[detection[1]])<0):

                    fh_id_log.write(str(cnt) + '\t' + str(detection[1]) +' exit '+ str(bee_time[cnt])+'\n')    
                    #add_bee_event(pre,bee_log_dict,tag[0],t.time()-start_time,True)
                else:
                    fh_id_log.write(str(cnt) + '\t' + str(detection[1]) +' enter '+ str(bee_time[cnt])+'\n')    
                    #add_bee_event(pre,bee_log_dict,tag[0],t.time()-start_time,False)
                   
            else:
                fh_id_log.write(str(cnt) + '\t' + str(detection[1]) + ' first ' + str(bee_time[cnt]) +'\n')    
            
            font= cv2.FONT_HERSHEY_SIMPLEX
            bottomLeftCornerOfText = (400,int(centerY))
            fontScale=1
            fontColor=(0,255,255)
            lineType=2
	
            cv2.putText(rgb,str(detection[1]), bottomLeftCornerOfText, font, fontScale,fontColor,lineType)
	    
 	
        for i, detection in enumerate(detections):
            pre_detection[detection[1]]=detection.center[1] #find the previous tags
       
            
    else:
        fh_id_log.write(str(cnt) + '\t' + '-1' + '\n')    
        pre_detection.clear()
    	
    fh_id_log.close()
    cv2.imwrite(save_prefix +" top_text" + str(cnt) + ".jpg",rgb)

    os.system('sync')
    
