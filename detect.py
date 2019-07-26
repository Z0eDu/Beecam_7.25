import cv2

import numpy as np
fgbg=cv2.BackgroundSubtractorMOG()
for i in range(45,46):
	
	image=cv2.imread('run-46__2019-07-25_16-04-23/top%d.jpg'%i)[200:300,:]
	#fgmask=fgbg.apply(image)
	#th=cv2.threshold(fgmask,10,255,cv2.THRESH_BINARY_INV)
	
	#print(sum(sum(image==255)))
	#print(np.amax(image))
	cv2.imwrite('test',image)
