import serial
ser = serial.Serial ("/dev/ttyS0")    #Open named port 
ser.baudrate = 9600                     #Set baud rate to 9600
while(True):	
	data = ser.read(20)                     #Read ten characters from serial port to data
	print(data)                        #Send back the received data
ser.close()        
