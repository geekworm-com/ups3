# ups3
Raspberry pi smart USP HAT V3

Contact email: sp@geekworm.com
# How to setup on Raspiban?

git clone https://github.com/geekworm-com/ups3.git
cd ups3
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

