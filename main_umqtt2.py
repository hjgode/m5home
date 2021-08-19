import sys
# add module search path
sys.path.append('/flash/res')
sys.path.reverse() #revert search direction to load custom libs first

from m5stack import *
import m5stack
from m5stack_ui import *
from uiflow import *
import wifiCfg
#from m5mqtt import M5mqtt
import ntptime
import time
from numbers import Number
import utime
import _thread

#from umqtt.simple import MQTTClient 
from robust2 import MQTTClient2 as _MQTTClient, MQTTException, pid_gen

sversion='1.2u2'

#screen stuff
screen = M5Screen()
screen.clean_screen()
screen.set_screen_bg_color(0xadefeb)
screen.set_screen_brightness(60)
current_screen=0

# idle timer
idle_counter=0
bThreadsRun=True

#an array to store screens
screens=[]

mydict={} #dict used to access InfoItems via the topic name

# We create a semaphore (A.K.A lock), avoid race conditions
lock_obj = _thread.allocate_lock()
lockIdle = _thread.allocate_lock()

class InfoItem:
  InfoItemList=[] #shared class variable, shared between the same instance, but beween new instances
  # example InfoItem.leftOffset access to shared instance
  #         but infoitem=InfoItem(...) and then infoitem.leftOffset only changes infoitem var only
  leftOffset=10
  topOffset=10 # 25 66 115 166 219
  midOffset=165
  line=0
  line_spacing=50
  last_posy=0
  def __init__(self, x=0, label='label', value='value'):
#    assert isinstance(x, int) and isinstance(y, int)
    # self. starts a instance variable
    self.posx = x
    self.posy = self.line*(self.line_spacing) #automatically add y pos
    InfoItem.last_posy=self.posy
    myfont=FONT_MONT_32
    mycolor=0x000000
    print('InfoTime ',InfoItem.line) #access the shared var
    self.label=label
    self.value=value
    self.label=M5Label(self.label,x=self.posx+self.leftOffset,y=self.posy+self.topOffset, color=mycolor, font=myfont, parent=None)
    self.value=M5Label(self.value,x=self.posx+self.midOffset,y=self.posy+self.topOffset, color=mycolor, font=myfont, parent=None)
    InfoItem.InfoItemList.append(self)
    InfoItem.line+=1
  def setTemp(self, tmp):
    self.value.set_text(tmp + '°C')
  def setHumi(self, tmp):
    self.value.set_text(tmp + '%')
  def setValue(self, tmp):
    self.value.set_text(tmp)
  def setState(self, tmp):
    self.value.set_text(tmp)
    if tmp=='open':
        self.value.set_text_color(0xff0000)
    else:
        self.value.set_text_color(0x00ff00)
  def reset_line():
    InfoItem.line=0
  def get_next_ypos(self):
    self.posy = self.line*(self.line_spacing) #automatically add y pos
    InfoItem.last_posy=self.posy
    next_y=self.posy+self.topOffset
    print('next_y='+str(next_y))
    return next_y
  def add_infoline():
    InfoItem.InfoItem.line+=1
    print('InfoItem.line='+str(InfoItem.line))
    return self.InfoItem.line 
  pass

class infoLine():
    def __init__(self):
        screenX=screen.get_act_screen()
        self.labelClock = M5Label('Text', x=10, y=219, color=0x000, font=FONT_MONT_14, parent=None)
        self.labelBattery = M5Label('batt', x=160, y=219, color=0x000, font=FONT_MONT_14, parent=None)
        self.labelVersion = M5Label(sversion, x=264, y=219, color=0x000, font=FONT_MONT_14, parent=None)
    pass

#this will publish msg to topic
# i.e. str('cmnd/sonoff2/power'),str('on'))
def publish(t,m):
    global c
    topic=t.encode('utf-8')
    msg=m.encode('utf-8')
    c.publish(topic=topic, msg=msg, retain=False, qos=1, dup=False)
    pass

def switchOn2():
    publish('cmnd/sonoff2/power','on')
    pass
def switchOff2():
    publish('cmnd/sonoff2/power','off')
    pass

def do_beep():
  #speaker.setVolume(1) ## not supported on Core2
  speaker.playTone(220, 1)
#  _thread.start_new_thread(do_vibrate(), ())

def do_vibrate():
  power.setVibrationIntensity(10)
  power.setVibrationEnable(True)
  wait_ms(250)
  power.setVibrationEnable(False)

def reset_idle_counter():
  global idle_counter
  lockIdle.acquire()  
  idle_counter=0
  lockIdle.release()
  screen.set_screen_brightness(60)
  pass

def padInt(n,z):
  s=str(n)
  l=len(s)
  if l<z:
    for y in range(0, l):
      s='0'+s
  return s  
  pass

def getPrevScreen():
  global current_screen, screens
  lock_obj.acquire()
  print('getPrevScreen called')
  current_screen-=1  
  if current_screen < 0 :
    current_screen=0
  else:
    screen.load_screen(screens[current_screen])
  lock_obj.release()
  pass
def getNextScreen():
  global current_screen, screens
  lock_obj.acquire()
  print('getNextScreen called')
  current_screen+=1
  if current_screen > len(screens)-1 :
    current_screen=len(screens)-1
  else:
    screen.load_screen(screens[current_screen])
  lock_obj.release()
  pass

def buttonA_wasPressed():
  # global params
  do_beep()
  reset_idle_counter()
  print('ButtonA pressed')
  _thread.start_new_thread(getPrevScreen, ())
  pass
btnA.wasPressed(buttonA_wasPressed)

#used to wakeup 
def buttonB_wasPressed():
  do_beep()
  reset_idle_counter()
  print('ButtonB pressed')
  pass
btnB.wasPressed(buttonB_wasPressed)

def buttonC_wasPressed():
  do_beep()
  reset_idle_counter()
  print('ButtonC pressed')
#  screen.clean_screen()
#  screen.load_screen(screen2)
#  getNextScreen()
  _thread.start_new_thread(getNextScreen, ())
#  screen.clean_screen()
#  screen.load_screen(screen1)
#  screen.load_screen(screens[2])
  pass
btnC.wasPressed(buttonC_wasPressed)

def getRSSI():
    horst1=wifiCfg.wlan_sta.scan()
    for ap in horst1:
        if ap[0].decode('utf-8')=='Horst1':
            print("RSSI: " + str(ap[3]))
            return ap[3]
        
########################## start screen0 #########################
screen0=screen.get_new_screen()
screen0.set_size(320,218)
infoAussenTemp=InfoItem(x=0,label='Aussen:',value='')
mydict['Hideki_30_1']=infoAussenTemp
#label0 = M5Label('-', x=179, y=25, color=0x000, font=FONT_MONT_32, parent=None)
#label1 = M5Label('Aussen:', x=9, y=25, color=0x000, font=FONT_MONT_32, parent=None)
infoSchlafzimmerTemp=InfoItem(x=0,label='Schlafz.:',value='')
mydict['Hideki_30_2']=infoSchlafzimmerTemp
#label2 = M5Label('Schlafz.:', x=9, y=66, color=0x000, font=FONT_MONT_32, parent=None)
#label3 = M5Label('-', x=179, y=66, color=0x000, font=FONT_MONT_32, parent=None)
infoTerrasse=InfoItem(x=0,label='Terrasse: ',value='')
mydict['SD_WS07_TH_2']=infoTerrasse
#label4 = M5Label('Terrasse:', x=10, y=164, color=0x000, font=FONT_MONT_28, parent=None)
infoFenster=InfoItem(x=0,label='Fenster:',value='')
mydict['HM_5F5A68']=infoFenster # look for status topic
mydict['duSchlafFenster']=infoFenster

#infoline0=infoLine()
labelClock = M5Label('Text', x=10, y=219, color=0x000, font=FONT_MONT_14, parent=None)
labelBattery = M5Label('batt', x=160, y=219, color=0x000, font=FONT_MONT_14, parent=None)
labelVersion = M5Label(sversion, x=264, y=219, color=0x000, font=FONT_MONT_14, parent=None)
#label_fenster = M5Label('Fenster:', x=9, y=116, color=0x000, font=FONT_MONT_32, parent=None)
#fenster_state = M5Label('-', x=179, y=115, color=0x000, font=FONT_MONT_32, parent=None)
#switch0 = M5Switch(x=172, y=161, w=70, h=30, bg_c=0xCCCCCC, color=0x0288FB, parent=None)


# save screen with all current content
screen0 = screen.get_act_screen()
screens.append(screen0)
########################## end screen0 #########################

###### info screen line
screen1 = screen.get_new_screen()
screen.load_screen(screen1)
#infoLine1=infoLine()

#start a new screen
InfoItem.reset_line()
infoBadTemp=InfoItem(x=0,label='Bad:',value='')
mydict['duBadTemp']=infoBadTemp
infoBadTempSoll=InfoItem(x=0,label='Bad Soll:',value='')
mydict['duBadTemp']=infoBadTempSoll

infoWohnTemp=InfoItem(x=0,label='Wohnz.:',value='')
mydict['SD_WS07_TH_3']=infoWohnTemp

ynext=infoWohnTemp.get_next_ypos()
switch2text=M5Label('Terrasse:', x=10,y=ynext, color=0x000000, font=FONT_MONT_32, parent=None)
switch2 = M5Switch(x=165, y=ynext, w=70, h=30, bg_c=0xCCCCCC, color=0x0288FB, parent=None)
switch2.on(switchOn2)

switch2.off(switchOff2)
mydict['sonoff2']=switch2

labelLocalIp = M5Label('ip', x=10, y=219, color=0x000, font=FONT_MONT_14, parent=None)
labelRSSI=M5Label('rssi', x=160, y=219, color=0x000, font=FONT_MONT_14, parent=None)
labelRSSI.set_text(str(getRSSI()))

screen1 = screen.get_act_screen()
screens.append(screen1)

########################## end screen1 #########################

########################## start screen1 #########################
#wetter
screen1 = screen.get_new_screen()
screen.load_screen(screen1)

#start a new screen
InfoItem.reset_line()

infoWeatherTempMin=InfoItem(x=0,label='Min:',value='')
mydict['Proplanta']=infoWeatherTempMin #but fc0_tempMin
infoWeatherTempMax=InfoItem(x=0,label='Max:',value='')
mydict['Proplanta']=infoWeatherTempMax # fc0_tempMax
infoWeatherText=InfoItem(x=0,label='Wetter:',value='')
infoWeatherText.value.set_text_font(FONT_MONT_18) #use a smaller font here
mydict['Proplanta']=infoWeatherText # fc0_weatherDay
infoWeatherRain=InfoItem(x=0,label='Regen:',value='')
mydict['Proplanta']=infoWeatherRain # fc0_chOfRainDay


screen2 = screen.get_act_screen()
screens.append(screen2)
########################## end screen1 #########################

screen.load_screen(screens[0])
                   
##############################################################
def getBatCapacity():
  volt = power.getBatVoltage()
  if volt < 3.20: return -1
  if volt < 3.27: return 0
  if volt < 3.61: return 5
  if volt < 3.69: return 10
  if volt < 3.71: return 15
  if volt < 3.73: return 20
  if volt < 3.75: return 25
  if volt < 3.77: return 30
  if volt < 3.79: return 35
  if volt < 3.80: return 40
  if volt < 3.82: return 45
  if volt < 3.84: return 50
  if volt < 3.85: return 55
  if volt < 3.87: return 60
  if volt < 3.91: return 65
  if volt < 3.95: return 70
  if volt < 3.98: return 75
  if volt < 4.02: return 80
  if volt < 4.08: return 85
  if volt < 4.11: return 90
  if volt < 4.15: return 95
  if volt < 4.20: return 100
  if volt >= 4.20: return 101
  pass

################ MAIN

#connect to wifi
wifiCfg.autoConnect(lcdShow=True)
wifiCfg.doConnect('Horst1', '1234567890123')
print("Wifi connected: ", str(wifiCfg.is_connected()))
print(wifiCfg.wlan_sta.ifconfig())
local_ip=wifiCfg.wlan_sta.ifconfig()[0]
labelLocalIp.set_text(str(local_ip))

ntp = ntptime.client(host='cn.pool.ntp.org', timezone=8)
rtc.settime('ntp', host='cn.pool.ntp.org', tzone=2)

#def fun_mqtt_callback(f):
def fun_mqtt_callback(topic, msg, retained, dup):
#    print('callback ',str(topic),":",str(msg))
    global mydict
    t=topic.decode('utf-8')
    m=msg.decode('utf-8')
    print('mqtt_callback ' + t + ':' + m+ ", ret="+str(retained) + ", dup=" + str(dup))
    try:
        s=t.split('/')
        if mydict.get(s[1], '-')=='-':
            print('mydict missing key: '+s[1])
            return
        t=mydict[s[1]] # find the label assigned for the topic
        if s[2] == 'temperature':
            print('update for >',s[1],'<')
            t.setTemp(msg.decode('utf-8'))
            return
#            t.value.set_text(msg.decode('utf-8')) #need to difference between Temp, Humi etc.
        if s[1]=='duBadTemp':
            if s[2] == 'measured':
                print('update for >','infoBadTemp','<')
                infoBadTemp.setTemp(msg.decode('utf-8'))
            if s[2] == 'desired':
                print('update for >','infoBadTempSoll','<')
                infoBadTempSoll.setTemp(msg.decode('utf-8'))
            return
        if s[1]=='Proplanta':
            if s[2] == 'fc0_tempMin':
                print('update for >','fc0_tempMin','<')
                infoWeatherTempMin.setTemp(msg.decode('utf-8'))
            if s[2] == 'fc0_tempMax':
                print('update for >','fc0_tempMax','<')
                infoWeatherTempMax.setTemp(msg.decode('utf-8'))
            if s[2] == 'fc0_weatherDay':
                print('update for >','fc0_weatherDay','<')
                infoWeatherText.setValue(msg.decode('utf-8'))
            if s[2] == 'fc0_chOfRainDay':
                print('update for >','fc0_chOfRainDay','<')
                infoWeatherRain.setHumi(msg.decode('utf-8'))
            return
        if s[1]=='HM_5F5A68' or s[1]=='duSchlafFenster':
            
            if s[2] == 'state' or s[2] == 'status':
                print('update for >',s[1],'<')
                t.setState(msg.decode('utf-8'))
            return
        #set switch2 state
        if s[1]=='sonoff2':
            print('found sonoff2')
            if s[2]=='power':
                print('found power, msg='+m)
                if m=='on':
                    t.set_on()
                else:
                    t.set_off()
            return
    except KeyError:
        pass
#    print('mqtt_callback ' + f.topic.decode('utf-8') + '/' + f.msg.decode('utf-8'))

def fun_mqtt_status_callback(pid,status):
    print('mqtt_status_callback: status=',str(status),", pid=",str(pid))
"""
    status = 0 - timeout
            status = 1 - successfully delivered
            status = 2 - Unknown PID. It is also possible that the PID is outdated,
                         i.e. it came out of the message timeout.
"""

#topic subscription
t='mqttGenericBridge/#' # can only subscribe to one topic tree and only one MQTTClient allowed?
t2='cmnd/#'
c=_MQTTClient('m5core2','192.168.0.40',1883,'','',300)
c.connect()
c.set_callback(fun_mqtt_callback)
c.set_callback_status(fun_mqtt_status_callback)

pid1=c.subscribe(topic=t,qos=1)
pid2=c.subscribe(topic=t2,qos=1)

print('subscriptions added: '+str(pid1)+", "+ str(pid2))
screen.load_screen(screens[0])

#as a second timerSch did not work for me, here is a thread
#ONLY TWO threads allowed!?
def idle_counter_thread():
  global idle_counter, lockIdle, screen, bThreadsRun, labelClock, labelBattery
  while bThreadsRun:
      try:      
          t=rtc.datetime()
          txt=padInt(t[4],2)+":"+padInt(t[5],2)+":"+padInt(t[6],2)
          dtxt=padInt(t[2],2)+":"+padInt(t[1],2)+":"+padInt(t[0],4)
          lockIdle.acquire()
          idle_counter+=1
          labelClock.set_text(dtxt + " " + txt)
    #      print(dtxt + " " + txt)
          labelBattery.set_text(str(getBatCapacity())+"%")
          if idle_counter>15 :
            screen.set_screen_brightness(30)
            labelRSSI.set_text(str(getRSSI()))
      except Exception as e:
          print('idle_counter_thread Exception: ',str(e))
          lockIdle.release()
          return
      lockIdle.release()
      wait_ms(1000)
#  _thread.start_new_thread(idle_counter_thread, ())
  pass
_thread.start_new_thread(idle_counter_thread, ())

def updateThread():
    global c, bThreadsRun
    while bThreadsRun:
        try:
            time.sleep_ms(100)
            c.wait_msg() #blocking call
        except (KeyboardInterrupt) as e:
            print('program interrupted')
            bThreadsRun=False
            time.sleep(2000)
            sys.exit()
_thread.start_new_thread(updateThread, ())

while True:
    try:
        time.sleep_ms(500)
    except (KeyboardInterrupt) as e:
        print('program interrupted')
        bThreadsRun=False
        time.sleep(2000)
        sys.exit()
        
    pass    

"""
Wifi connected:  True
mqtt_status_callback: status= 1 , pid= 1
mqtt_callback mqttGenericBridge/Hideki_30_1/humidity:70, ret=True, dup=False
mqtt_callback mqttGenericBridge/Hideki_30_1/temperature:16.6, ret=True, dup=False
mqtt_callback mqttGenericBridge/Hideki_30_2/temperature:21.7, ret=True, dup=False
mqtt_callback mqttGenericBridge/Hideki_30_2/humidity:62, ret=True, dup=False
mqtt_callback mqttGenericBridge/HM_5F5A68/state:open, ret=True, dup=False
mqtt_callback mqttGenericBridge/temperature/SD_WS07_TH_3:22.2, ret=True, dup=False
mqtt_callback mqttGenericBridge/SD_WS07_TH_3/temperature:23.2, ret=True, dup=False
mqtt_callback mqttGenericBridge/SD_WS07_TH_3/humidity:67, ret=True, dup=False
mqtt_callback mqttGenericBridge/duSchlafFenster/status:open, ret=True, dup=False
mqtt_callback mqttGenericBridge/Hideki_30_4/humidity:66, ret=True, dup=False
mqtt_callback mqttGenericBridge/Hideki_30_4/temperature:23, ret=True, dup=False
mqtt_callback mqttGenericBridge/duBadTemp/desired:18.0, ret=True, dup=False
mqtt_callback mqttGenericBridge/duBadTemp/measured:23.3, ret=True, dup=False
mqtt_callback mqttGenericBridge/duBadTemp/controlMode:auto, ret=True, dup=False
mqtt_callback mqttGenericBridge/SD_WS07_TH_2/humidity:57, ret=True, dup=False
mqtt_callback mqttGenericBridge/SD_WS07_TH_2/temperature:5.5, ret=True, dup=False
mqtt_callback mqttGenericBridge/Proplanta/fc0_chOfRainDay:80, ret=True, dup=False
mqtt_callback mqttGenericBridge/Proplanta/fc0_date:16.08.2021, ret=True, dup=False
mqtt_callback mqttGenericBridge/Proplanta/fc0_tempMin:12, ret=True, dup=False
mqtt_callback mqttGenericBridge/Proplanta/fc0_chOfRainNight:40, ret=True, dup=False
mqtt_callback mqttGenericBridge/Proplanta/fc0_weatherDay:Regen, ret=True, dup=False
mqtt_callback mqttGenericBridge/Proplanta/fc0_tempMax:19, ret=True, dup=False
mqtt_callback mqttGenericBridge/Proplanta/fc0_rain:6.1, ret=True, dup=False
mqtt_callback mqttGenericBridge/SD_WS07_TH_2/humidity:58, ret=False, dup=False
mqtt_callback mqttGenericBridge/Hideki_30_2/humidity:62, ret=False, dup=False
mqtt_callback mqttGenericBridge/Hideki_30_1/humidity:70, ret=False, dup=False
"""
