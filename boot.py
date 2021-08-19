import sys
# add module search path
sys.path.append('/flash/apps')
sys.path.reverse() #revert search direction to load custom libs first

from machine import SDCard
from machine import Pin 
import os
import time
#import webrepl

try:
    sd = SDCard(slot=3, miso=Pin(38), mosi=Pin(23), sck=Pin(18), cs=Pin(4))
    sd.info()
    os.mount(sd, '/sd')
    print('Ctrl+C to interrupt!')
    time.sleep_ms(2000)
    print("SD card mounted at \"/sd\"")

#    wifiCfg.autoConnect(lcdShow=True)
#    wifiCfg.doConnect('Horst1', '1234567890123')
#    print("Wifi connected: ", str(wifiCfg.is_connected()))
#    print(wifiCfg.wlan_sta.ifconfig())

#    _webrepl.password('chopper')
#    webrepl.setup_conn(8266, accept_conn)
#    print("Started webrepl in normal mode")

except (KeyboardInterrupt, Exception) as e:
    # print('SD mount caught exception {} {}'.format(type(e).__name__, e))
    pass