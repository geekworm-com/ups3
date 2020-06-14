# coding=UTF-8
#
# U-GEEK Raspi Smart UPS HAT V3
#

import os
import time
import smbus
import signal
import logging
import threading
from neopixel import *
from logging.handlers import RotatingFileHandler

# Global settings
BUS_ADDR 		= 1
disconnectflag 	= False
exit_thread 	= False
max17048_soc	= 0
POWEROFF_POWER = 5
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

# WS2812 settings
LED_COUNT      	= 16      # Number of LED pixels.
LED_PIN = 18
# LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    	= 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        	= 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 12
LED_INVERT     	= False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    	= 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
# LED Color
COLOR_RED = Color(0,255,0)
COLOR_GREEN = Color(255,0,0)
COLOR_BLUE = Color(0,0,255)
COLOR_YELLOW = Color(255,255,0)
COLOR_PURPLE = Color(0,255,255)
COLOR_CYAN = Color(255,0,255)
COLOR_WHITE = Color(255,255,255)
COLOR_BLACK = Color(0,0,0)


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
		power = "Disconnected"

	if status[3] and status[4]:
		charge = "Charging done"
	elif status[4] and  not status[3]:
		charge = "Charging"
	elif not status[4] and status[3]:
		charge = "Pre-Charge"
	else:
		charge = "Discharging"
	
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
	
	if power == "Disconnected" and disconnectflag == False :
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
		"BatteryPercentage" : int(batpercent*100),
		'TimeRemaining' : int(timeleftmin)
	}
	
	if(batv < 3.5):
		bus.write_byte_data(BQ25895_ADDRESS, REG_BATFET_DIS, BYTE_BATFET_DIS)
		
def print_bq25895status():
	print ("Input: " , bq25895_status['Input'])
	print ("ChargeStatus: " , bq25895_status['ChargeStatus'])
	print ("BatteryVoltage: " , bq25895_status['BatteryVoltage'], "V")
	print ("BatteryPercentage: " , bq25895_status['BatteryPercentage'] , "%")
	print("VSYS_STAT: ", bin(vsys_stat), "SDP_STAT: ", bin(sdp_stat), 
		"PG_STAT:", bin(pg_stat), "CHRG_STAT:" , bin(chrg_stat), 
		"VBUS_STAT:", bin(vbus_stat))
	
def print_max17048status():
	print ("Status of max17048:")
	print ('%.2f' % max17048_v , "V")
	print (max17048_soc , "%")
	print ("Status of bq25895:")

# Intialize the library (must be called once before other functions).
def led_init():
	global strip
	strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
	strip.begin()

def led_off():
	strip.setPixelColor(0, COLOR_BLACK)
	strip.setPixelColor(1, COLOR_BLACK)
	strip.setPixelColor(2, COLOR_BLACK)
	strip.setPixelColor(3, COLOR_BLACK)
	strip.show()
	
def led_full():
	strip.setPixelColor(0, COLOR_GREEN)
	strip.setPixelColor(1, COLOR_GREEN)
	strip.setPixelColor(2, COLOR_GREEN)
	strip.setPixelColor(3, COLOR_GREEN)
	strip.show()
	
# pre-charge
# led 1,2,3,4 flash
def led_precharge():
	for i in range(0,255):
		if exit_thread:
			return
		strip.setPixelColor(0, Color(i,0,0))
		strip.setPixelColor(1, Color(i,0,0))
		strip.setPixelColor(2, Color(i,0,0))
		strip.setPixelColor(3, Color(i,0,0))
		strip.show()
		time.sleep(0.005)
	for i in range(255,0,-1):
		if exit_thread:
			return
		strip.setPixelColor(0, Color(i,0,0))
		strip.setPixelColor(1, Color(i,0,0))
		strip.setPixelColor(2, Color(i,0,0))
		strip.setPixelColor(3, Color(i,0,0))
		strip.show()
		time.sleep(0.005)
	time.sleep(1)
	
# Charging to 25%
# led 1 flash,others black
def led_charginto25():
	strip.setPixelColor(0, COLOR_BLACK)
	strip.setPixelColor(1, COLOR_BLACK)
	strip.setPixelColor(2, COLOR_BLACK)
	for i in range(0,255):
		if exit_thread:
			return
		strip.setPixelColor(3, Color(0,0,i))
		strip.show()
		time.sleep(0.005)
	for i in range(255,0,-1):
		if exit_thread:
			return
		strip.setPixelColor(3, Color(0,0,i))
		strip.show()
		time.sleep(0.005)
	time.sleep(1)

# Charging from 25% to 50%
# led 1 green,led 2 flash, others black
def led_chargingto50():
	strip.setPixelColor(0, COLOR_BLACK)
	strip.setPixelColor(1, COLOR_BLACK)
	strip.setPixelColor(3, COLOR_BLUE)
	for i in range(0,255):
		if exit_thread:
			return
		strip.setPixelColor(2, Color(0,0,i))
		strip.show()
		time.sleep(0.005)
	for i in range(255,0,-1):
		if exit_thread:
			return
		strip.setPixelColor(2, Color(0,0,i))
		strip.show()
		time.sleep(0.005)
	time.sleep(1)
	
# Charging from 50% to 75%
# led 1,2 green,led 3 flash, led 4 black
def led_chargingto75():
	strip.setPixelColor(0, COLOR_BLACK)
	strip.setPixelColor(2, COLOR_BLUE)
	strip.setPixelColor(3, COLOR_BLUE)
	for i in range(0,255):
		if exit_thread:
			return
		strip.setPixelColor(1, Color(0,0,i))
		strip.show()
		time.sleep(0.005)
	for i in range(255,0,-1):
		if exit_thread:
			return
		strip.setPixelColor(1, Color(0,0,i))
		strip.show()
		time.sleep(0.005)
	time.sleep(1)
	
# Charging from 75% to 100%
# led 1,2,3 green,led 4 flash
def led_chargingto100():
	strip.setPixelColor(1, COLOR_BLUE)
	strip.setPixelColor(2, COLOR_BLUE)
	strip.setPixelColor(3, COLOR_BLUE)
	for i in range(0,255):
		if exit_thread:
			return
		strip.setPixelColor(0, Color(0,0,i))
		strip.show()
		time.sleep(0.005)
	for i in range(255,0,-1):
		if exit_thread:
			return
		strip.setPixelColor(0, Color(0,0,i))
		strip.show()
		time.sleep(0.005)
	time.sleep(1)
	
# Dischargeing to 75%
def led_dischargeto75():
	strip.setPixelColor(0, COLOR_BLACK)
	strip.setPixelColor(1, COLOR_GREEN)
	strip.setPixelColor(2, COLOR_GREEN)
	strip.setPixelColor(3, COLOR_GREEN)
	strip.show()
	
# Discharging to 50%
def led_dischargeto50():
	strip.setPixelColor(0, COLOR_BLACK)
	strip.setPixelColor(1, COLOR_BLACK)
	strip.setPixelColor(2, COLOR_GREEN)
	strip.setPixelColor(3, COLOR_GREEN)
	strip.show()
	
# Discharging to 25%
def led_dischargeto25():
	strip.setPixelColor(0, COLOR_BLACK)
	strip.setPixelColor(1, COLOR_BLACK)
	strip.setPixelColor(2, COLOR_BLACK)
	strip.setPixelColor(3, COLOR_GREEN)
	strip.show()

# Discharging to 10%
def led_dischargeto10():
	strip.setPixelColor(0, COLOR_BLACK)
	strip.setPixelColor(1, COLOR_BLACK)
	strip.setPixelColor(2, COLOR_BLACK)
	strip.setPixelColor(3, COLOR_YELLOW)
	strip.show()
	
# Discharging to 0%
def led_dischargeto0():
	strip.setPixelColor(0, COLOR_BLACK)
	strip.setPixelColor(1, COLOR_BLACK)
	strip.setPixelColor(2, COLOR_BLACK)
	for i in range(0,255):
		if exit_thread:
			return
		strip.setPixelColor(3, Color(i,i,0))
		strip.show()
		time.sleep(0.005)
	for i in range(255,0,-1):
		if exit_thread:
			return
		strip.setPixelColor(3, Color(i,i,0))
		strip.show()
		time.sleep(0.005)
	time.sleep(1)
	
def led_show():
	while exit_thread is False:
		if bq25895_status['Input'] == 'Connected': # Power connected
			if bq25895_status['ChargeStatus'] == 'Charging done':
				led_full()
			elif bq25895_status['ChargeStatus'] == 'Charging':
				if max17048_soc > 75:
					led_chargingto100()
				elif ((max17048_soc > 50) and (max17048_soc <= 75)):
					led_chargingto75()
				elif ((max17048_soc > 25) and (max17048_soc <= 50)):
					led_chargingto50()
				else:
					led_charginto25()
			elif bq25895_status['ChargeStatus'] == 'Pre-Charge':
				led_precharge()
			elif bq25895_status['ChargeStatus'] == 'Discharging':
				led_full()
			else:
				led_off()
		else:	# Power Disconnected
			if max17048_soc > 90:
				led_full()
			elif ((max17048_soc > 75) and (max17048_soc <= 90)):
				led_dischargeto75()
			elif ((max17048_soc > 50) and (max17048_soc <= 75)):
				led_dischargeto50()
			elif ((max17048_soc > 25) and (max17048_soc <= 50)):
				led_dischargeto25()
			elif ((max17048_soc > 10) and (max17048_soc <= 25)):
				led_dischargeto10()
			else:
				led_dischargeto0()
	led_off()
	
def stop(sig, frame):
	led_off()
	exit_thread = True

def ignore(sig, frsma):
	led_off()
	exit_thread = True
	
def handler(signum, frame):
    print ("Signal is received:" + str(signum))
    exit_thread=True
    thread_led.join()
    exit
	
def handle_signal():
	signal.signal(signal.SIGUSR1, handler)
	signal.signal(signal.SIGUSR2, handler)
	signal.signal(signal.SIGALRM, handler)
	signal.signal(signal.SIGINT, handler)
	signal.signal(signal.SIGQUIT, handler)

def logging_status():
	info = ' Input:' + bq25895_status['Input'] + ' , ChargeStatus: ' + bq25895_status['ChargeStatus'] + ' , SOC:' + str(max17048_soc) + "%"
	app_log.info(info)
	
# Main Loop
if __name__ == '__main__':
	log_formatter = logging.Formatter('%(asctime)s  %(filename)s : %(levelname)s  %(message)s')
	log_filename = '/var/log/smartups.log'
	log_handler = RotatingFileHandler(log_filename, mode='a', maxBytes=5 * 1024 * 1024, 
                                 backupCount=2, encoding=None, delay=0)
	log_handler.setFormatter(log_formatter)
	log_handler.setLevel(logging.INFO)
	app_log = logging.getLogger('root')
	app_log.setLevel(logging.DEBUG)
	app_log.addHandler(log_handler)

	init_i2c()
	max17048_init()
	bq25895_init()
	bq25895_read_status()
	led_init()
	led_precharge()
	thread_led = threading.Thread(target=led_show)
	thread_led.start() 
	try:
		while (True):
			max17048_getstatus()
			bq25895_read_status()
			logging_status()
			if ((bq25895_status['Input'] != 'Connected') and (max17048_soc < POWEROFF_POWER)):
				count = count + 1
				#print bq25895_status['Input']
				if count > 10:
					logging.warning("Shutdown")
					os.system("sudo halt -h")
			#print bq25895_status['Input']
			#print " Charge status:" , bq25895_status['ChargeStatus'], " soc: ", max17048_soc
	except:
		exit_thread=True
		thread_led.join()
		exit
