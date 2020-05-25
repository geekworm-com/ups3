#!/bin/bash
#
# Smart UPS V3 setup script.
#

TITLE="UPS V3 Setting"
BACKTITLE="https://geekworm.com/"
INSTALLED=0
BRIGHTNESS=127
GPIO=18
FILENAME="smartups.py"
LIBNEO="neopixel.py"
FILEPATH="/usr/local/bin/"
SERVICENAME="smartups"
SERVICEFILE="smartups.service"
SERVICEPATH="/etc/systemd/system/"
SERVCIEPOWEROFF="/smartups_poweroff.service"
SOFTWARE_LIST="scons"
POWEROFF_POWER=15
SERVICEENABLED="disabled"
SAFESHUTDOWN="disabled"
ICL=104
MENU_INSTALLED="Remove"
CONFIG="/boot/config.txt"

function enable_i2c(){
	sed -i '/^dtparam=i2c_arm=/d' $CONFIG
	echo "dtparam=i2c_arm=on" >> $CONFIG
	if ! grep -q "^i2c[-_]dev" /etc/modules; then
		printf "i2c-dev\n" >> /etc/modules
	fi
}

function brightness_to_percent(){
	case $1 in
		0)
		return 0
		;;
		12)
		return 5
		;;
		26)
		return 10
		;;
		51)
		return 20
		;;
		77)
		return 30
		;;
		102)
		return 40
		;;
		127)
		return 50
		;;
		153)
		return 60
		;;
		179)
		return 70
		;;
		204)
		return 80
		;;
		230)
		return 90
		;;
		255)
		return 100
		;;
		*)
		return 50
		;;
	esac
}

function percnet_to_brightness() {
	case $1 in
		0)
		return 0
		;;
		5)
		return 12
		;;
		10)
		return 26
		;;
		20)
		return 51
		;;
		30)
		return 77
		;;
		40)
		return 102
		;;
		50)
		return 127
		;;
		60)
		return 153
		;;
		70)
		return 179
		;;
		80)
		return 204
		;;
		90)
		return 230
		;;
		100)
		return 255
		;;
		*)
		return 127
		;;
	esac
}

# install system required
function install_sysreq(){
	SOFT=$(dpkg -l $SOFTWARE_LIST | grep "<none>")
	if [ -n "$SOFT" ]; then
		apt update
		apt -y install $SOFTWARE_LIST
	fi
	SOFT=$(pip search rpi-ws281x | grep "INSTALLED")
	if [ -z "$SOFT" ]; then
		pip install rpi-ws281x
		echo "rpi-ws281x install complete!"
	else
		echo "rpi-ws281x already exists."
	fi
}

function check_safeshutdown(){
	RESULT=$(cat /boot/config.txt | grep 'dtoverlay=gpio-poweroff' | awk -F= '{print $1}'
)
	if [ "$RESULT" != "dtoverlay" ]; then
		SAFESHUTDOWN="disabled"
	else
		SAFESHUTDOWN="enabled"
	fi
}

# get current gpio
function get_gpio(){
	if [ -f $FILEPATH$FILENAME ] ; then
		GPIO=$(grep -n '^LED_PIN' $FILEPATH$FILENAME | awk -F " " '{print $3}')
	else
		GPIO=$(grep -n '^LED_PIN' $FILENAME | awk -F " " '{print $3}')
	fi
}

# get current brightness
function get_brightness(){
	if [ -f $FILEPATH$FILENAME ]; then
		BRIGHTNESS=$(grep -n '^LED_BRIGHTNESS' $FILEPATH$FILENAME | awk -F " " '{print $3}')
	else
		BRIGHTNESS=$(grep -n '^LED_BRIGHTNESS' $FILENAME | awk -F " " '{print $3}')
	fi
	return $BRIGHTNESS
}

# get poweroff power
function get_poweroff_power(){
	if [ -f $FILEPATH$FILENAME ]; then
		POWEROFF_POWER=$(grep -n '^POWEROFF_POWER' $FILEPATH$FILENAME | awk -F " " '{print $3}')
	else
		POWEROFF_POWER=$(grep -n '^POWEROFF_POWER' $FILENAME | awk -F " " '{print $3}')
	fi
}

# get service is enabled
function get_service_isenabled(){
	SERVICEENABLED=$(systemctl is-enabled smartups)
	if [ "$SERVICEENABLED" == "enabled" ]; then
		return 1
	else
		return 0
	fi
}

# check the script is installed
function check_installed(){
	if [ -f $FILEPATH$FILENAME -a -f $SERVICEPATH$SERVICEFILE ]; then
		return 1
	else
		return 0
	fi
}

function enable_service(){
	get_service_isenabled
	if [ $? -eq 1 ]; then
		echo "Service has been enabled."
		return
	fi
	if [ -f $FILEPATH$FILENAME -a -f $SERVICEPATH$SERVICEFILE ]; then
		systemctl enable $SERVICENAME
	else
		echo "Service does not exists."
	fi
}

function disable_service(){
	get_service_isenabled
	if [ $? -eq 1 ]; then
		systemctl disable $SERVICENAME
	else
		echo "Service does not exists or has been stopped."
	fi
}

function enable_safeshutdown(){
	check_safeshutdown
	if [ "$SAFESHUTDOWN" == "disabled" ]; then
		echo "dtoverlay=gpio-poweroff,gpiopin=6" >> $CONFIG
	fi
	check_safeshutdown
}

function disable_safeshutdown(){
	sed -i '/dtoverlay=gpio-poweroff/d' $CONFIG
	check_safeshutdown
}

function stop_service(){
	check_installed
	if [ $? -eq 1 ]; then
		RESULT=$(systemctl is-failed smartups)
		if [ $RESULT == "active" ]; then
			systemctl stop $SERVICENAME
			echo "Service stopped."
		else
			echo "Service already stopped."
		fi
	else
		echo "Service not installed, do not need to stop."
	fi

}

function start_service(){
	check_installed
	if [ $? -eq 1 ]; then
		echo "Start service now."
		systemctl start $SERVICENAME
	else
		echo "Service not installed."
	fi
}

# enable ups
function install_ups(){
	echo "Install Smart UPS Service."
	enable_i2c
	install_sysreq

	if [ -f $FILENAME ]; then
		cp $FILENAME $FILEPATH$FILENAME
	fi
	if [ -f $LIBNEO ]; then
		cp $LIBNEO $FILEPATH$LIBNEO
	fi
	if [ -f $SERVICEFILE ]; then
		cp $SERVICEFILE $SERVICEPATH$SERVICEFILE
	fi
	enable_service
	start_service
	RESULT=$(systemctl is-failed smartups)
	if [ $RESULT == "active" ]; then
		echo "Service successfully installed."
	else
		echo "Service install failed, clean now."
		remove_ups
	fi
}

# disable ups
function remove_ups(){
	echo "Remove Smart UPS Service."
	RESULT=$(systemctl is-failed smartups)
	if [ $RESULT == "active" ]; then
		echo "Service is running,stop it now."
		stop_service
	fi
	disable_service
	if [ -f $FILEPATH$FILENAME ]; then
		rm $FILEPATH$FILENAME
	fi
	if [ -f $FILEPATH$LIBNEO ]; then
		rm $FILEPATH$LIBNEO
	fi
	if [ -f $FILEPATH$LIBNEOc ]; then
		rm $FILEPATH$LIBNEOc
	fi
	if [ -f $SERVICEPATH$SERVICEFILE ]; then
		rm $SERVICEPATH$SERVICEFILE
	fi
	echo "Service remove complete."
}

function install_poweroff(){
	if [ ! -f $SERVICEPATH$SERVCIEPOWEROFF ]; then
		echo << EOF > $SERVICEPATH$SERVCIEPOWEROFF
[Unit]
Description=...

[Service]
Type=oneshot
RemainAfterExit=true
ExecStop=<your script/program>

[Install]
WantedBy=multi-user.target
EOF
	fi
}

# menu gpio
function menu_gpio(){
	OPTION=$(whiptail --title "$TITLE" \
	--menu "Select the GPIO:" \
	--backtitle "$BACKTITLE" \
	--nocancel \
	14 60 6 \
	"1" "GPIO18" \
	"2" "GPIO12" 3>&1 1>&2 2>&3)
	return $OPTION
}

# menu brightness
function menu_brightness(){
	OPTION=$(whiptail --title "$TITLE" \
	--menu "Select the brightness:" \
	--backtitle "$BACKTITLE" \
	--nocancel \
	14 60 6 \
	"0" "Off." \
	"5" "5%" \
	"10" "10%" \
	"20" "20%" \
	"30" "30%" \
	"40" "40%" \
	"50" "50%" \
	"60" "60%" \
	"70" "70%" \
	"80" "80%" \
	"90" "90%" \
	"100" "100%" 3>&1 1>&2 2>&3)
	return $OPTION
}

# menu poweroff power
function menu_poweroff_power(){
	OPTION=$(whiptail --title "$TITLE" \
	--menu "Select the poweroff power" \
	--backtitle "$BACKTITLE" \
	--nocancel \
	--notags \
	--default-item "15" \
	16 60 8 \
	"0" "0%" \
	"1" "1%" \
	"2" "2%" \
	"3" "3%" \
	"4" "4%" \
	"5" "5%" \
	"6" "6%" \
	"7" "7%" \
	"8" "8%" \
	"9" "9%" \
	"10" "10%" \
	"11" "11%" \
	"12" "12%" \
	"13" "13%" \
	"14" "14%" \
	"15" "15%" \
	"16" "16%" \
	"17" "17%" \
	"18" "18%" \
	"19" "19%" \
	"20" "20%" \
	"21" "21%" \
	"22" "22%" \
	"23" "23%" \
	"24" "24%" \
	"25" "25%" \
	"26" "26%" \
	"27" "27%" \
	"28" "28%" \
	"29" "29%" \
	"30" "30%" \
	3>&1 1>&2 2>&3)
	return $OPTION
}

# menu reboot
function menu_reboot(){
	if (whiptail --title "$TITLE" \
		--yes-button "Reboot" \
		--no-button "Exit" \
		--yesno "Reboot system to apply new settings?" 10 60) then
		reboot
	else
		exit 1
	fi
}

# menu install
function menu_install(){
	OPTION=$(whiptail --title "$TITLE" \
	--yesno "This will install SMART UPS V3 service to your PI,Are you sure to continue?" \
	--backtitle "$BACKTITLE" \
	14 60 6 \
	3>&1 1>&2 2>&3)
	return $OPTION
}

#menu input current limit
function menu_icl(){
	OPTION=$(whiptail --title "$TITLE" \
	--menu "Select the appropriate options:" \
	--backtitle "$BACKTITLE" \
	--nocancel \
	17 60 9 \
	"1" "2A" \
	"2" "3A" \
	"3" "3.25A" \
	"R" "Return"
	>&1 1>&2 2>&3)
	return $OPTION
}

# main menu
function menu_advanced(){
	OPTION=$(whiptail --title "$TITLE" \
	--menu "Select the appropriate options:" \
	--backtitle "$BACKTITLE" \
	--nocancel \
	17 60 9 \
	"1" "Input Curernt Limit [ ]" \
	"R" "Return"  3>&1 1>&2 2>&3)
	return $OPTION
}

# main menu
function menu_main(){
	OPTION=$(whiptail --title "$TITLE" \
	--menu "Select the appropriate options:" \
	--backtitle "$BACKTITLE" \
	--nocancel \
	17 60 9 \
	"1" "UPS GPIO [ $GPIO ]" \
	"2" "LED Brightness [ $BRIGHTNESS_MENU ]" \
	"3" "Poweoff power [ <$POWEROFF_POWER% ]" \
	"4" "Auto run script [ $SERVICEENABLED ]" \
	"5" "Safe shutdown [ $SAFESHUTDOWN ]" \
	"6" "Apply Settings" \
	"7" "$MENU_INSTALLED" \
	"8" "Exit"  3>&1 1>&2 2>&3)
	return $OPTION
}

# Superuser privileges
if [ $UID -ne 0 ]; then
	whiptail --title "$TITLE" \
	--msgbox "Superuser privileges are required to run this script.\ne.g. \"sudo $0\"" 10 60
    exit 1
fi

#brightness_to_percent 230
#echo $?

# main
get_gpio
get_brightness
BRIGHTNESS=$?
brightness_to_percent $BRIGHTNESS
PERCENT=$?
BRIGHTNESS_MENU=$PERCENT"%"
get_poweroff_power

check_installed
check_safeshutdown

if [ $? -eq 0 ]; then
	menu_install
	if [ $? -eq 1 ]; then
		exit
	fi
	install_ups
fi

while [ True ]
do
	#get_brightness
	check_installed
	if [ $? -eq 0 ]; then
		MENU_INSTALLED="Install"
	else
		MENU_INSTALLED="Remove"
	fi
	get_service_isenabled
	check_safeshutdown
	menu_main
	case $? in
		1)
		menu_gpio
		case $? in
			1)
			GPIO=18
			;;
			2)
			GPIO=12
			;;
		esac
		;;
		2)
		menu_brightness
		PERCENT=$?
		percnet_to_brightness $PERCENT
		BRIGHTNESS=$?
		BRIGHTNESS_MENU=$PERCENT"%"
		;;
		3)
		menu_poweroff_power
		POWEROFF_POWER=$?
		;;
		4)
		if [ $SERVICEENABLED == "enabled" ]; then
			disable_service
		else
			enable_service
		fi
		;;
		5)
		if [ "$SAFESHUTDOWN" == "enabled" ]; then
			disable_safeshutdown
		else
			enable_safeshutdown
		fi
		;;
		6)
		stop_service
		echo "GPIO:"$GPIO" Brightness:"$BRIGHTNESS" Shutdown power:"$POWEROFF_POWER
		if [ -f $FILENAME ]; then
			sed -i 's/^LED_PIN.*/LED_PIN = '$GPIO'/' $FILENAME
		fi
		if [ -f $FILEPATH$FILENAME ]; then
			sed -i 's/^LED_PIN.*/LED_PIN = '$GPIO'/' $FILEPATH$FILENAME
		fi
		if [ -f $FILENAME ]; then
			sed -i 's/^LED_BRIGHTNESS.*/LED_BRIGHTNESS = '$BRIGHTNESS'/' $FILENAME
		fi
		if [ -f $FILEPATH$FILENAME ]; then
			sed -i 's/^LED_BRIGHTNESS.*/LED_BRIGHTNESS = '$BRIGHTNESS'/' $FILEPATH$FILENAME
		fi
		if [ -f $FILENAME ]; then
			sed -i 's/^POWEROFF_POWER.*/POWEROFF_POWER = '$POWEROFF_POWER'/' $FILENAME
		fi
		if [ -f $FILEPATH$FILENAME ]; then
			sed -i 's/^POWEROFF_POWER.*/POWEROFF_POWER = '$POWEROFF_POWER'/' $FILEPATH$FILENAME
		fi
		start_service
		;;
		7)
		if [ "$MENU_INSTALLED" == "Install" ]; then
			install_ups
		else
			remove_ups
		fi
		;;
		8)
		exit
		;;
		*)
		;;
	esac
done

