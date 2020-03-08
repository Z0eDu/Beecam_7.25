import numpy as np
import cv2
import glob
import os
import time
# termination criteria
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
objp = np.zeros((6*3,3), np.float32)
objp[:,:2] = np.mgrid[0:3,0:6].T.reshape(-1,2)
objp = objp.reshape(-1,1,3)
print(objp.shape)
# Arrays to store object points and image points from all the images.
objpoints = [] # 3d point in real world space
imgpoints = [] # 2d points in image plane.
win = 'Calibrate'
cv2.namedWindow(win)
images = glob.glob('/home/pi/beecam/var/image*.jpg')
for fname in images:
    print 'Filename: ', fname
    img = cv2.imread(fname)
    # Find the chess board corners
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, (6,3))
    print('ad ',ret, corners)
    # If found, add object points, image points (after refining them)
    if ret == True:
        cv2.cornerSubPix(gray,corners,(11,11),(-1,-1),criteria)
        imgpoints.append(corners)
        print('corners',corners)
        objpoints.append(objp)
        # Draw and display the corners
        display = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        cv2.drawChessboardCorners(display, (6,3), corners, ret)
        cv2.imshow(win,display)
        #while cv2.waitKey(5) not in range(128): pass
        #cv2.waitKey(500)
    else:
		os.system('sudo rm '+fname)
		print('delete: ',fname)
objpoints=np.array(objpoints)
imgpoints=np.array(imgpoints)
print('shape: ',objpoints.shape)
print('shape: ',np.asarray(imgpoints).shape)
#print 'Objects points: {0}, image points: {1}'.format(objpoints, imgpoints)

ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1])#,None,None)    
fx = K[0,0]
fy = K[1,1]
cx = K[0,2]
cy = K[1,2]
print('  fx = {}'.format(K[0,0]))
print('  fy = {}'.format(K[1,1]))
print('  cx = {}'.format(K[0,2]))
print('  cy = {}'.format(K[1,2]))
print()
cv2.destroyAllWindows()
