#!/bin/bash

#echo "22" > /sys/class/gpio/export
echo "out" > /sys/class/gpio/gpio22/direction
count=0
while [ $count -le 5 ];
do  
	reach=$(sudo ntpq -c "associations"|awk 'FNR == 3  {print $5}' )
	if [ $reach == "yes" ];
	then
	var=$(sudo ntpq -pn | awk  'FNR == 3  {print $9}')
	var1=${var#-}
	var2=${var1%.*}
	echo "offset is $var1 ms" 
		if [ $var2 -lt 5 ];
		then
			echo "0" > /sys/class/gpio/gpio22/value
			echo "yes connect to ntp server"
			break
		#sudo python3 continous_capture.py
		fi
	else 
	
		echo "1" > /sys/class/gpio/gpio22/value
		echo "fail to connect to server and restart ntp"
		sudo /etc/init.d/ntp restart
		count=$(($count + 1))
		sleep 10
	fi
echo "timeout"
done


