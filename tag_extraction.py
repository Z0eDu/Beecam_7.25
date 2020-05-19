import cv2
import pytesseract
import numpy as np
from matplotlib import pyplot as plt
import math
from PIL import Image
import glob

# add code to read image from another thread

import time
from keras.models import load_model


model = load_model('tag_model_v2.h5')

# add some code to read image from another thread

def tag_read(image):
    image = image.reshape(1,78,78,1)
    image = image.astype('float32')
    image /= 255
    prediction = model.predict(image,batch_size=1,verbose=1)
    pred_class = np.argmax(prediction,axis = 1)
    pred_class = pred_class
    print (pred_class)
    return pred_class



def tag_extract(image):
    #print("in tag extraction")
    # read image and apply color filter
    
    #image = cv2.imread(image)
    img = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV) 
    mask = cv2.inRange(hsv, (30, 40, 20), (90, 255,255))
    
    imask = mask>0
    green = np.zeros_like(img, np.uint8)
    green[imask] = img[imask]
    gray = cv2.cvtColor(green, cv2.COLOR_BGR2GRAY)

    # detect circles
    detected_circles = cv2.HoughCircles(gray,  
                       cv2.HOUGH_GRADIENT, 1, 20, param1 = 50, 
                   param2 = 1, minRadius = 10, maxRadius = 50) 

    if detected_circles is not None: 

        # Convert the circle parameters a, b and r to integers. 
        detected_circles = np.uint16(np.around(detected_circles))
        #print(detected_circles)
        pt = detected_circles[0,0]
        a, b, r = pt[0], pt[1], pt[2]
        cv2.circle(green, (a, b), r, (255, 255, 255), 2) 
    else:
        return None
    # crop the tag
    roi = img[b-r:b+r,a-r:a+r]
    
    # empty image if tag is on the edge
    if roi.shape[0] == 0 or roi.shape[1] == 0:
        tag = np.zeros((78,78))
        tag = np.uint8(tag)
       # cv2.imwrite(name,tag)
        return tag
    
    # make tag a scare
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    if gray_roi.shape[0] != gray_roi.shape[1]:
        if gray_roi.shape[0] < gray_roi.shape[1]:
            new_roi = np.zeros((gray_roi.shape[1],gray_roi.shape[1]))
            new_roi[0:gray_roi.shape[0],0:gray_roi.shape[1]] = gray_roi
        else: 
            new_roi = np.zeros((gray_roi.shape[0],gray_roi.shape[0]))
            new_roi[0:gray_roi.shape[0],0:gray_roi.shape[1]] = gray_roi
        gray_roi = new_roi

    # crop to size 78*78
    if gray_roi.shape[0] > 78:
        gray_roi = gray_roi[r-39:r+39,r-39:r+39]
        tag = gray_roi
    elif roi.shape[0] < 78:
        tag = np.zeros((78,78))
        tag[39-r:39+r,39-r:39+r] = gray_roi
        tag = np.uint8(tag)
    else:
        tag = gray_roi
        #cv2.imwrite(name,tag)
    return tag

# get the tag

path=glob.glob("/home/pi/Desktop/t/*.jpg")
#print (path)

#print( path)
f=open('data.txt','a')
for i in path:
    #
    #print(i[:-4]+'_tag.jpg')
    #cv2.imwrite(i[:-4]+'_tag.jpg',tag)
    #print (name+'var/'+str(cnt)+'.jpg')
    #if tag is not None:
# tag=cv2.imread("109_1.jpg")
    tag=cv2.imread(i)
    tag = tag_extract(tag)
    cv2.imwrite('tag.jpg',tag)
    pred = tag_read(tag)
# print(pred)
    
    f.write(i[:-4]+"   "+str(pred)+"\n")

f.close()
# add code to send tag to another thread or save tag image
