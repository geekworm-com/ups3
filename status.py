# coding=UTF-8
#
# U-GEEK Raspi Smart UPS HAT V3
#

import os
import sys
import time
import smbus
import signal
import threading
from neopixel import *

# Global settings
BUS_ADDR 		= 1
disconnectflag 	= False
exit_thread 	= False
max17048_soc	= 0
POWEROFF_POWER  = 5
count           = 0

#MAX17048 settings
MAX17048_ADDR 	= 0x36

# BQ25895 setgins
BQ25895_ADDRESS = 0x6A
REG_WATCHDOG    = 0x07
BYTE_WATCHDOG_STOP = 0b10001101 #Stop Watchdog timer
REG_ILIM 		= 0x00 #ILIM register
#BYTE_ILIM 		= 0b01101000 #2A input current limit
#BYTE_ILIM 		= 0b01111100 #3A input current limit
BYTE_ILIM 		= 0b01111111 #3.25A input current limit
REG_ICHG 		= 0x04 
BYTE_ICHG 		= 0b01111111 #.5A charging current limit
REG_CONV_ADC 	= 0x02
REG_BATFET 		= 0x09
BYTE_BATFET 	= 0b01001000 #delay before battery == disconnected
BAT_CAPACITY 	= 2500 #Battery capacity in mah
CURRENT_DRAW 	= 2000 #Current draw in mah
REG_CONV_ADC 	= 0x02
BYTE_CONV_ADC_START = 0b10011101
BYTE_CONV_ADC_STOP  = 0b00011101
REG_BATFET_DIS  = 0x09
BYTE_BATFET_DIS = 0b01101000
REG_STATUS		= 0x0B #address of status register
REG_BATV		= 0x0e
REG_FAULT		= 0x0c
REG_BATI		= 0x12

# Init i2c bus
def init_i2c():
	global bus
	bus = smbus.SMBus(BUS_ADDR)

# Init max17048	
def max17048_init():
	bus.write_word_data(MAX17048_ADDR, 0xFE ,0xFFFF)
	return True

# Get voltage from max17048
def max17048_getstatus():
	global max17048_v, max17048_soc
	max17048_v_16 = bus.read_word_data(MAX17048_ADDR, 0x02);
	soc = bus.read_word_data(MAX17048_ADDR, 0x04);
	max17048_v = (((max17048_v_16 & 0x00FF) << 8) + (max17048_v_16 >> 8)) * 78.125 / 1000000
	max17048_soc = (((soc & 0x00FF) << 8) + (soc >> 8)) / 256

# Init bq25895
def bq25895_init():
	bus.write_byte_data(BQ25895_ADDRESS, REG_WATCHDOG, BYTE_WATCHDOG_STOP)
	bus.write_byte_data(BQ25895_ADDRESS, REG_ILIM, BYTE_ILIM)
	bus.write_byte_data(BQ25895_ADDRESS, REG_ICHG, BYTE_ICHG)
	bus.write_byte_data(BQ25895_ADDRESS, REG_BATFET, BYTE_BATFET)

def bq25895_int_to_bool_list(num):
	return [bool(num & (1<<n)) for n in range(8)]

def bq25895_translate(val, in_from, in_to, out_from, out_to):
	out_range = out_to - out_from
	in_range = in_to - in_from
	in_val = val - in_from
	val=(float(in_val)/in_range)*out_range
	out_val = out_from+val
	return out_val
	
def bq25895_read_reg(reg):
	return bus.read_byte_data(BQ25895_ADDRESS, reg)

# BQ25895 read status
def bq25895_read_status():
	global SLEEPDELAY, disconnectflag, batpercentprev, bq25895_status
	bus.write_byte_data(BQ25895_ADDRESS, REG_CONV_ADC, BYTE_CONV_ADC_START)
	sample = bus.read_byte_data(BQ25895_ADDRESS, REG_STATUS)
	status = bq25895_int_to_bool_list(sample)
	time.sleep(1.2)
	sample = bus.read_byte_data(BQ25895_ADDRESS, REG_BATV)
	batvbool = bq25895_int_to_bool_list(sample)
	bus.write_byte_data(BQ25895_ADDRESS, REG_CONV_ADC, BYTE_CONV_ADC_STOP)
	#print(sample)
	vsys_stat = status[0]
	sdp_stat = status[1]
	pg_stat = status[2]
	chrg_stat = status[4] * 2 + status[3]
	vbus_stat = status[7] * 4 + status[6] * 2 + status[5]
	
	if status[2]:
		power = "Connected"
	else:
		power = "Not Connected"

	if status[3] and status[4]:
		charge = "Charging done"
	elif status[4] and  not status[3]:
		charge = "Charging"
	elif not status[4] and status[3]:
		charge = "Pre-Charge"
	else:
		charge = "Not Charging"
	
	#convert batv register to volts
	batv = 2.304
	batv += batvbool[6] * 1.280
	batv += batvbool[5] * 0.640
	batv += batvbool[4] * 0.320
	batv += batvbool[3] * 0.160
	batv += batvbool[2] * 0.08
	batv += batvbool[1] * 0.04
	batv += batvbool[0] * 0.02   

	batpercent = bq25895_translate(batv,3.5,4.184,0,1)
	if batpercent<0 :
		batpercent = 0
	elif batpercent >1 :
		batpercent = 1
	
	timeleftmin = int( batpercent * 60* BAT_CAPACITY / CURRENT_DRAW)
	if timeleftmin < 0 :
		timeleftmin = 0
	
	if power == "Connected" :
		timeleftmin = -1        
	
	if power == "Not Connected" and disconnectflag == False :
		disconnectflag = True
		message = "echo Power Disconnected, system will shutdown in %d minutes! | wall" % (timeleftmin)
		#os.system(message)
	
	if power == "Connected" and disconnectflag == True :
		disconnectflag = False
		message = "echo Power Restored, battery at %d percent | wall" % (batpercentprev * 100)
		#os.system(message)

	batpercentprev = batpercent
	
	bq25895_status = { 
		'Input': power,
		'ChargeStatus' : charge,
		'BatteryVoltage' : '%.2f' % batv,
		"BatterySOC" : int(batpercent*100),
		'TimeRemaining' : int(timeleftmin)
	}
	
	if(batv < 3.5):
		bus.write_byte_data(BQ25895_ADDRESS, REG_BATFET_DIS, BYTE_BATFET_DIS)
		
def print_bq25895status():
	global count
	count = count + 1
	print ("         Count: " , count)
	print ("         Input: " , bq25895_status['Input'])
	print ("  ChargeStatus: " , bq25895_status['ChargeStatus'])
	print ("BatteryVoltage: " , bq25895_status['BatteryVoltage'], "V")
	#print "    BatterySOC: " , bq25895_status['BatterySOC'] , "%"
	#print ""
	# print("VSYS_STAT: ", bin(vsys_stat), "SDP_STAT: ", bin(sdp_stat), 
		# "PG_STAT:", bin(pg_stat), "CHRG_STAT:" , bin(chrg_stat), 
		# "VBUS_STAT:", bin(vbus_stat))
	
def print_max17048status():
	#print "Status of max17048:"
	#print "BatteryVoltage: " , '%.2f' % max17048_v , "V"
	print ("           SOC: " , max17048_soc , "%")
	#print "Status of bq25895:"

def get_print_all_status():
	max17048_getstatus()
	bq25895_read_status()
	print_bq25895status()
	print_max17048status()
	print ("")
	
def handler(signum, frame):
	print ("Signal is received:" + str(signum))
	os.system("systemctl start smartups")
	exit_thread=True
	thread_led.join()
	exit
	
def handle_signal():
	signal.signal(signal.SIGUSR1, handler)
	signal.signal(signal.SIGUSR2, handler)
	signal.signal(signal.SIGALRM, handler)
	signal.signal(signal.SIGINT, handler)
	signal.signal(signal.SIGQUIT, handler)

# Main Loop
if __name__ == '__main__':
	service_status = os.system("systemctl is-active --quiet smartups")
	if service_status is 0:
		os.system("systemctl stop smartups")
	status_loop = False
	init_i2c()
	max17048_init()
	bq25895_init()
	print ("Reading status...")
	
	try:
		get_print_all_status()

		if len(sys.argv) > 0:
			if sys.argv[1] == "-t":
				status_loop = True
			
		while status_loop is True:
			get_print_all_status()
			
		os.system("systemctl start smartups")
	except:
		os.system("systemctl start smartups")
		exit
