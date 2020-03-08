import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)


while True:
	GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)    #beam sensor 1
	print('1')
	time.sleep(5)
	GPIO.cleanup(21)
	print('2')
	time.sleep(10)
	
