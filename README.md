# ups3
This repository is a fork from the original 
[Raspberry Pi UPS HAT V3](https://github.com/geekworm-com/ups3) 
repository with the focus of making it compatible with python3.

Owners email contact: sp@geekworm.com
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

View Status:

sudo python status.py or sudo python status.py -t

View logs:

cat /var/log/smartups.log

