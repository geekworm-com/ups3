# ups3
This repository is a fork from the original 
[Raspberry Pi UPS HAT V3](https://github.com/geekworm-com/ups3) 
repository with the focus of making it compatible with python3.

Owners email contact: info@geekworm.com
# Test
This project has been tested on a Raspberry Pi 4 (Buster) system.

# Setup (Raspberry Pi)

git clone https://github.com/geekworm-com/ups3.git

cd ups3

chmod +x *.sh *.py

sudo ./install.sh

               ┌────────────────────┤ UPS V3 Setting ├────────────────────┐
               │ Select the appropriate options:                          │
               │                                                          │
               │                 1 UPS GPIO [ 18 ]                        │
               │                 2 LED Brightness [ 10% ]                 │
               │                 3 Poweoff power [ <5% ]                  │
               │                 4 Auto run script [ enabled ]            │
               │                 5 Safe shutdown [ enabled ]              │
               │                 6 Apply Settings                         │
               │                 7 Remove                                 │
               │                 8 Exit                                   │
               │                                                          │
               │                                                          │
               │                                                          │
               │                                                          │
               │                          <Ok>                            │
               │                                                          │
               └──────────────────────────────────────────────────────────┘
               

Description of each option：

After you select an option, you must use option 6 to make it effective！！

1 UPS GPIO [ 18 ] :

Ups3 uses GPIO18 to manage LED lights by default, When you need to use GPIO 18 yourself, through this option, you can modify the GPIO PIN

2 LED Brightness [ 10% ]:

You can change the brightness of LED via this option, you need to reboot raspberry pi to take effect.

3 Poweoff power [ <5% ]：

This is a useful function, you can set the percentage of power to tell UPS3 to shut down automatically

4 Autorun [ enabled ] :

If you want this service to run automatically every time the Raspberry Pi restarts, please remember to enable it.

5 Safe shutdown [ enabled ] :

Please refer to here: https://wiki.geekworm.com/UPS3_power_off_guide

6 Apply Settings:

After you select an option, you must use this option to make it effective;

7 Remove:

Remove or uninstall this script / service;

8 Exit:

Exit this menu;

View Status:

sudo python status.py or sudo python status.py -t

View logs:

cat /var/log/smartups.log

