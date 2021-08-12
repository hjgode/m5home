import sys
# add module search path
sys.path.append('/res')

from m5stack import *
import m5stack
from m5stack_ui import *
from uiflow import *
import wifiCfg
from m5mqtt import M5mqtt
import ntptime
from numbers import Number
import utime
import _thread
#from umqtt.simple import MQTTClient # see https://mpython.readthedocs.io/en/master/library/mPython/umqtt.simple.html
# but umqtt.simple has issue with usocket timeout

#from builtins import dir # dir() is not supported in UIFlow
#import inspect # inspect is not part of micropython nor UIFlow

# testing based on https://docs.m5stack.com/en/mpy/display/m5stack_lvgl
# very strange site using // as cooment in a python context. BAH

# lvgl API at https://docs.lvgl.io/master/overview/display.html#screens

## written in vscode with extension from https://github.com/curdeveryday/vscode-m5stack-mpy

## You can get an interactive REPL with Thonny: https://github.com/thonny/thonny/wiki/MicroPython
## MU-Editor did not work for me
## Thonny 3.3.14 needs a patch
"""
see https://github.com/thonny/thonny/issues/1565
  thonny/plugins/micropython/bare_metal_backend.py

  around Line 954
    self._soft_reboot_without_running_main()
"""
## Then in Thonny you can use remote shell REPL to issue commands like
## help(<object>), dir(<object>) etc.
## or issue program functions interactively :-)

# Does not work on UIFlow device
#from TempHumiClass import TempHumi #load TempHumiClass.py

#lcd.ellipse(10, 10, 40, 20, color=0xc0c0c0) # no lcd

sversion='1.2'

screen = M5Screen()
screen.clean_screen()
screen.set_screen_bg_color(0xadefeb)
screen.set_screen_brightness(60)

# idle timer
idle_counter=0

#an array to store screens
screens=[]


# We create a semaphore (A.K.A lock), avoid race conditions
lock_obj = _thread.allocate_lock()
lockIdle = _thread.allocate_lock()

#need to define class inside code
class TempHumi:
  #shared vars
  TempHumiList=[]
  def __init__(self, x,y):
    assert isinstance(x, int) and isinstance(y, int)
    self.posx = x
    self.posy = y
    Img1 = M5Img("res/temp_humi_small.png", x=self.posx, y=self.posy, parent=None)
    self.name=M5Label('-', x=self.posx+10, y=self.posy+75, color=0xffffff, font=FONT_MONT_18, parent=None)
    self.temp=M5Label('00°C', x=self.posx+50, y=self.posy+15, color=0xffffff, font=FONT_MONT_18, parent=None)
    self.humi=M5Label('00%', x=self.posx+50, y=self.posy+50, color=0xffffff, font=FONT_MONT_18, parent=None)
    
    TempHumi.TempHumiList.append(self)
  #cannot use set_text method here, will hang app!
  def set_text(txt):
    self.name.set_text(str(txt))
  pass
"""
class InfoBottomLine:
  _screen=None
  def __init__(self):
    print('InfoBottomLine...')
    _screen=screen.get_act_screen()
    self.labelClock = M5Label('Text', x=10, y=219, color=0x000, font=FONT_MONT_14, parent=None)
    self.labelBattery = M5Label('batt', x=160, y=219, color=0x000, font=FONT_MONT_14, parent=None)
    self.labelVersion = M5Label(sversion, x=264, y=219, color=0x000, font=FONT_MONT_14, parent=None)
  def update():
    print('InfoBottomLine update...')
    t=rtc.datetime()
    txt=padInt(t[4],2)+":"+padInt(t[5],2)+":"+padInt(t[6],2)
    dtxt=padInt(t[2],2)+":"+padInt(t[1],2)+":"+padInt(t[0],4)
    self.labelClock.set_text(dtxt + " " + txt)
  pass
"""
class InfoItem:
  InfoItemList=[] #shared var
  leftOffset=5
  topOffset=5
  midOffset=165
  line=0
  def __init__(self, x=0,y=0, label='label', value='value'):
    assert isinstance(x, int) and isinstance(y, int)
    self.posx = x
    self.posy = self.line*(28) #automatically add y pos
    myfont=FONT_MONT_24
    mycolor=0x000000
    print('InfoTime ',InfoItem.line) #access the shared var
    self.label=label
    self.value=value
    self.label=M5Label(self.label,x=self.posx+self.leftOffset,y=self.posy+self.topOffset, color=mycolor, font=myfont, parent=None)
    self.value=M5Label(self.value,x=self.posx+self.midOffset,y=self.posy+self.topOffset, color=mycolor, font=myfont, parent=None)
    InfoItem.InfoItemList.append(self)
    InfoItem.line+=1
  def reset_line():
    InfoItem.line=0
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


""" currently not used
#default M5Tabview(x=0, y=0)
tab = M5Tabview(0,30)

#Create tab
tab.add_tab("tab1")
tab.add_tab("tab2")
tab.add_tab("tab3")
"""

#connect to wifi
wifiCfg.autoConnect(lcdShow=True)
wifiCfg.doConnect('Horst1', '1234567890123')
print("Wifi connected: ", str(wifiCfg.is_connected()))

########################## start screen0 #########################
label0 = M5Label('-', x=179, y=25, color=0x000, font=FONT_MONT_32, parent=None)
label1 = M5Label('Aussen:', x=9, y=25, color=0x000, font=FONT_MONT_32, parent=None)
label2 = M5Label('Schlafz.:', x=9, y=66, color=0x000, font=FONT_MONT_32, parent=None)
label3 = M5Label('-', x=179, y=66, color=0x000, font=FONT_MONT_32, parent=None)
label4 = M5Label('Terrasse:', x=10, y=164, color=0x000, font=FONT_MONT_28, parent=None)
label_fenster = M5Label('Fenster:', x=9, y=116, color=0x000, font=FONT_MONT_32, parent=None)
fenster_state = M5Label('-', x=179, y=115, color=0x000, font=FONT_MONT_32, parent=None)
switch0 = M5Switch(x=172, y=161, w=70, h=30, bg_c=0xCCCCCC, color=0x0288FB, parent=None)
clock = M5Label('Text', x=10, y=219, color=0x000, font=FONT_MONT_14, parent=None)
labelBattery = M5Label('batt', x=160, y=219, color=0x000, font=FONT_MONT_14, parent=None)
labelVersion = M5Label(sversion, x=264, y=219, color=0x000, font=FONT_MONT_14, parent=None)


# save screen with all current content
screen0 = screen.get_act_screen()
screens.append(screen0)
########################## end screen0 #########################

########################## start screen1 #########################
# get a new screen
screen1 = screen.get_new_screen()
screen.load_screen(screen1)
#bottom line?
#info1=InfoBottomLine()
clock1 = M5Label('Text', x=10, y=219, color=0x000, font=FONT_MONT_14, parent=None)
# load screenX, will clear the screen
# Unfortunately, this will change screen0 content to show initial fixed values
# and strangely makes changes to labels appear on screen1!
# so, better use new vars. With new vars, the objects will not show on other screen

#myBatSymbol=getBatSymbol()
#labelBattery1 = M5Label(myBatSymbol, x=142, y=219, color=0x000, font=FONT_MONT_14, parent=None)
labelBattery1 = M5Label(SYMBOL_BATTERY_2, x=142, y=219, color=0x000, font=FONT_MONT_14, parent=None)
labelVersion1 = M5Label(sversion, x=264, y=210, color=0x000, font=FONT_MONT_14, parent=None)

# x,y,w,h,border_color,fill_color
#rectangle1 = M5Rect(10, 10, 80, 80, 0x000000, 0xFFFFFF) # DNW on Core2

#M5Img(filename, x=0, y=0, w=None, h=None) 
Img1 = M5Img("res/temp_humi_small.png", x=10, y=10, parent=screen1)
temp1_name=M5Label('Schlaf', x=20, y=85, color=0xffffff, font=FONT_MONT_18, parent=None)
temp1_temp=M5Label('22°C', x=50, y=25, color=0xffffff, font=FONT_MONT_18, parent=None)
temp1_humi=M5Label('84%', x=50, y=60, color=0xffffff, font=FONT_MONT_18, parent=None)
Img2 = M5Img("res/temp_humi_small.png", x=10, y=120, parent=None)
temp2_name=M5Label('Aussen', x=20, y=195, color=0xffffff, font=FONT_MONT_18, parent=None)
temp2_temp=M5Label('22°C', x=50, y=135, color=0xffffff, font=FONT_MONT_18, parent=None)
temp2_humi=M5Label('84%', x=50, y=170, color=0xffffff, font=FONT_MONT_18, parent=None)
#Img1.set_img_src("res/temperature_small.png") #corrupted? img may hang the app :-(
#use 8Bit/Pixel RGB png images (8bpc)
#Img2 = M5Img("res/humidity_small.png", x=20, y=20, w=10, h=10, parent=None)
label1_1 = M5Label('-', x=179, y=25, color=0x000, font=FONT_MONT_14, parent=None)

#now using a custom class
tempHumiWohn=TempHumi(120,120)
#cannot use class code to change text, program will hang then, need to set text via class variable directly
tempHumiWohn.name.set_text("Wohn")
tempHumiWohn.temp.set_text(str(22)+"°C")
#can use class internal shared array
tempHumiWohn.TempHumiList[0].humi.set_text(str(44)+"%")
#tempHumiWohn.humi.set_text(str(44)+"%")

#add another temphumi class instance
tempHumiBad=TempHumi(120,10)
tempHumiBad.name.set_text("Bad")
tempHumiBad.temp.set_text(str(22)+"°C")
tempHumiBad.humi.set_text(str(44)+"%")

# print all class members
#label1_1.set_text(dir(TempHumi))

""" Cannot be used on separate screen DNW
#M5Msgbox(btns_list=None, x=0, y=0, w=None, h=None)
Msgbox1 = M5Msgbox()
btns_list1=(Btn1,Btn1)
Msgbox1.add_btns(btns_list1)
#Fill text
Msgbox1.set_text('text')
#print(Msgbox1.get_active_btn_text())
"""

#screen_top=screen.get_top_layer() #DNW

#save screen
screen1 = screen.get_act_screen()
screens.append(screen1)

########################## end screen1 #########################

########################## start screen2 #########################

screen2=screen.get_new_screen() # get_new_screen always retruns the same, second screen, not a new object
screen.load_screen(screen2) #now start drawing on third screen?

""" USAGE UNCLEAR
#default M5Tabview(x=0, y=0)
tab = M5Tabview(0,30)
#Create tab
tab.add_tab("tab1")
tab.add_tab("tab2")
tab.add_tab("tab3")
def tabview1_cb():
  print('tabview1_cb '+str(tab.get_state()))
  pass
tab.set_cb(tabview1_cb)
"""

#M5Textarea(text='', x=0, y=0, w=None, h=None)
Textarea = M5Textarea('', 30, 30, 100, 100)
#Fill text
Textarea.set_text("Hello World")
#Textarea.set_text(dir(TempHumi)) ## dir is not supported, although this part of the micropython builtins module

#M5Btn(text=``, x=0, y=0, w=70, h=30, bg_c=None, text_c=None, font=None)
Btn1 = M5Btn("button",50,150,80,50,0xff,0xffffff,FONT_MONT_12)
Btn1.set_bg_color(0x1f0000)
Btn1.set_btn_text('text')
#Btn1.set_btn_text_color(color)
#Btn1.set_btn_text_font(font)

def pressed_cb():
  print('button pressed')
  do_beep()
  pass

def released_cb():
  print('button released')
  do_beep()
  pass
Btn1.pressed(pressed_cb)
Btn1.released(released_cb)

#needs a 'import m5stack' at top and does not work well within m5stack
#m5stack.lcd.drawRect(160,120,20,20,0xff0000,0x100f10);

#save screen
screens.append(screen2)
########################## end screen2 #########################


########################## start screen3 #########################

screen3=screen.get_new_screen() # get_new_screen always retruns the same, second screen, not a new object
screen.load_screen(screen3) #now start drawing on third screen?

itemviewAussen=InfoItem(0,0,'Aussen:','-')
itemviewSchlaf=InfoItem(0,0,'Schlaf:','-')
itemviewBad=InfoItem(0,0,'Bad:','-')
itemviewBadSoll=InfoItem(0,0,'Bad Soll:','-')
itemviewBadMode=InfoItem(0,0,'Bad Mode:','-')
itemviewWohn=InfoItem(0,0,'Wohn:','-')
itemviewTerrasse=InfoItem(0,0,'Terrasse:','-')
#itemview6.label.set_align(ALIGN_IN_TOP_RIGHT) #moves label to top right position of screen!

wifiLabel3=M5Label(SYMBOL_WIFI, x=20, y=85, color=0xffffff, font=FONT_MONT_18, parent=None)
wifiLabel3.set_align(ALIGN_IN_BOTTOM_RIGHT) #set_align moves object to screen position

"""
#align text to right of label
itemviewAussen.value.set_long_mode(LABEL_LONG_CROP) # LABEL_LONG_BREAK)
itemviewAussen.value.set_size(140,30)
try:
  # right align to defined screen pos
  # pending on alignment, the value pair defines offset to left and top or right and top or
  # bottom/left etc.
  # BUT does not right alin text inside label!
  # m5stack.lv.label.set_align(itemviewSchlaf, LV_LABEL_ALIGN_CENTER)
  # set_align is supported but no LV_LABEL_ALIGN_CENTER
  M5Obj.set_align(itemviewAussen.value, ALIGN_IN_TOP_RIGHT, 60, 8)
except Exception as e:
  print('exception: ', str(e))
except:
  print('exception!')
"""

#save screen
screens.append(screen3)
########################## end screen3 #########################

########################################


#activate screen0
#screen.load_screen(screen0) # direct load
screen.load_screen(screens[0])

"""
#how sould this be used? It places clockTop only on top of current screen, no on all screens
screenTop=m5stack.lv.layer_sys
clockTop = M5Label('TextTop', x=10, y=219, color=0x000, font=FONT_MONT_14, parent=None)
"""

#########################
current_screen=0

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
#########################

def buttonA_wasPressed():
  # global params
  do_beep()
  reset_idle_counter()
  print('ButtonA pressed')
#  screen.clean_screen()
#  screen.load_screen(screen0)
#  screen.load_screen(screens[0])
#  getPrevScreen()
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

def switch0_on():
  m5mqtt.publish(str('cmnd/sonoff2/power'),str('on'))
  pass
switch0.on(switch0_on)

def switch0_off():
  m5mqtt.publish(str('cmnd/sonoff2/power'),str('off'))
  pass
switch0.off(switch0_off)



def fun_mqttGenericBridge_HM_5F5A68_state_(topic_data):
  fstatus=str(topic_data)
  print('fun_mqttGenericBridge_HM_5F5A68_state_='+str(topic_data))
#  label1_1.set_text(fstatus)
  fenster_state.set_text(str(topic_data))
  if fstatus == 'open':
    fenster_state.set_text_color(0xff0000)
  else:
    fenster_state.set_text_color(0x33cc00)
  pass

#schlaf
def fun_mqttGenericBridge_Hideki_30_2_temperature_(topic_data):
  temp1_temp.set_text(str((str(topic_data) + str('°C'))))
  label3.set_text(str((str(topic_data) + str('°C'))))
  itemviewSchlaf.value.set_text(str((str(topic_data) + str('°C'))))
def fun_mqttGenericBridge_Hideki_30_2_humidity_(topic_data):
  temp1_humi.set_text(str((str(topic_data) + str('%'))))

#aussen
def fun_mqttGenericBridge_Hideki_30_1_temperature_(topic_data):
  temp2_temp.set_text(str((str(topic_data) + str('°C'))))
  label0.set_text(str((str(topic_data) + str('°C'))))
  itemviewAussen.value.set_text(str((str(topic_data) + str('°C'))))
def fun_mqttGenericBridge_Hideki_30_1_humidity_(topic_data):
  temp2_humi.set_text(str((str(topic_data) + str('%'))))

#wohn
def fun_mqttGenericBridge_SD_WS07_TH_3_humidity_(topic_data):
#  temp2_humi.set_text(str((str(topic_data) + str('%'))))
  tempHumiWohn.humi.set_text(str(topic_data)+"°C")
  print('fun_mqttGenericBridge_SD_WS07_TH_3_humidity_ ',topic_data)
  pass
def fun_mqttGenericBridge_SD_WS07_TH_3_temperature_(topic_data):
  tempHumiWohn.temp.set_text(str(topic_data)+"°C")
#  temp2_humi.set_text(str((str(topic_data) + str('%'))))
  print('fun_mqttGenericBridge_SD_WS07_TH_3_temperature_ ',topic_data)
  itemviewWohn.value.set_text(str((str(topic_data) + str('°C'))))
  pass
#bad
def fun_mqttGenericBridge_Hideki_30_4_humidity_(topic_data):
#  temp2_humi.set_text(str((str(topic_data) + str('%'))))
  print('fun_mqttGenericBridge_Hideki_30_4_humidity_ ',topic_data)
  tempHumiBad.humi.set_text(str(topic_data)+"%")
  pass
def fun_mqttGenericBridge_Hideki_30_4_temperature_(topic_data):
#  temp2_humi.set_text(str((str(topic_data) + str('%'))))
  print('fun_mqttGenericBridge_Hideki_30_4_temperature_ ',topic_data)
  tempHumiBad.temp.set_text(str(topic_data)+"°C")
  itemviewBad.value.set_text(str((str(topic_data) + str('°C'))))

  pass

#bad duBadTemp
def fun_duBadTemp_temperature_desired_(topic_data):
  print('fun_duBadTemp_temperature_desired_ ',topic_data)
  itemviewBadSoll.value.set_text(str((str(topic_data) + str('°C'))))
  pass
def fun_duBadTemp_temperature_measured_(topic_data):
  print('fun_duBadTemp_temperature_measured_ ',topic_data)
#  tempHumiBad.temp.set_text(str(topic_data)+"°C")
  tempHumiBad.temp.set_text(str(topic_data)+"°C")
  itemviewBad.value.set_text(str((str(topic_data) + str('°C'))))
  pass
def fun_duBadTemp_temperature_controlmode_(topic_data):
  print('fun_duBadTemp_temperature_controlmode_ ',topic_data)
#  tempHumiBad.temp.set_text(str(topic_data)+"°C")
#  tempHumiBad.temp.set_text(str(topic_data)+"°C")
  itemviewBadMode.value.set_text(str(str(topic_data)))
  pass

#terrasse
def fun_mqttGenericBridge_SD_WS07_TH_2_humidity_(topic_data):
#  temp2_humi.set_text(str((str(topic_data) + str('%'))))
  #tempHumiTerrasse.humi.set_text(str(topic_data)+"°C")
  print('fun_mqttGenericBridge_SD_WS07_TH_2_humidity_ ',topic_data)
  pass
def fun_mqttGenericBridge_SD_WS07_TH_2_temperature_(topic_data):
  tempHumiWohn.temp.set_text(str(topic_data)+"°C")
#  temp2_humi.set_text(str((str(topic_data) + str('%'))))
  print('fun_mqttGenericBridge_SD_WS07_TH_2_temperature_ ',topic_data)
  itemviewTerrasse.value.set_text(str((str(topic_data) + str('°C'))))
  pass

def fun____stat_sonoff2_POWER_(topic_data):
  if topic_data == 'ON':
    switch0.set_on()
  else:
    switch0.set_off()
  pass
  print('fun____stat_sonoff2_POWER_'+topic_data)
  pass



# in = number, padding

def padInt(n,z):
  s=str(n)
  l=len(s)
  if l<z:
    for y in range(0, l):
      s='0'+s
  return s  
  pass

@timerSch.event('clocktimer1')
def tclocktimer1():
#  if isinstance(info1):
#    info1.update()
  t=rtc.datetime()
  txt=padInt(t[4],2)+":"+padInt(t[5],2)+":"+padInt(t[6],2)
  dtxt=padInt(t[2],2)+":"+padInt(t[1],2)+":"+padInt(t[0],4)
  clock.set_text(dtxt + " " + txt)
#  print("Date {}".format(utime.strftime("%Y-%m-%d", utime.localtime())))  ## utime does not support strftime on core2
  #txt.format(rtc.datetime()[2],rtc.datetime()[1],rtc.datetime()[0],rtc.datetime()[4],rtc.datetime()[5],rtc.datetime()[6])
  #clock.set_text(str((str((rtc.datetime()[2])) + str(((str('.') + str(((str((rtc.datetime()[1])) + str(((str('.') + str(((str((rtc.datetime()[0])) + str(((str(' ') + str(((str((rtc.datetime()[4])) + str(((str(':') + str(((str((rtc.datetime()[5])) + str(((str(':') + str((rtc.datetime()[6]))))))))))))))))))))))))))))))))
  labelBattery.set_text(str(getBatCapacity())+"%")
  labelBattery1.set_text(getBatSymbol())
  #act=M5Screen.get_inactive_time() #DoesNotWork!
  #labelVersion.set_text(str(act))
  #print("Wifi connected: ", str(wifiCfg.is_connected()))
  if wifiCfg.is_connected():
    wifiLabel3.set_text_color(0x00ff00)
  else:
    wifiLabel3.set_text_color(0xff0000)
  pass

"""
@timerSch.event('clocktimer2')
def tclocktimer2():
  global idle_counter
  idle_conter+=1
  labelVersion.set_text(str(idle_conter))
#  print('idle=',idle_counter)
  if idle_counter>3 :
    screen.set_screen_brightness(30)
  pass
"""
#as a second timerSch did not work for me, here is a thread
def idle_counter_thread():
  global idle_counter, lockIdle
  lockIdle.acquire()
  idle_counter+=1
  try:
      if idle_counter>3 :
        screen.set_screen_brightness(30)
  except Exception as e:
      print('idle_counter_thread Exception: ',str(e))
  lockIdle.release()
  wait_ms(5000)
  _thread.start_new_thread(idle_counter_thread, ())
  pass

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

def getBatSymbol():
  volt = power.getBatVoltage()
  if volt < 3.20: return SYMBOL_BATTERY_EMPTY
  if volt < 3.69: return SYMBOL_BATTERY_EMPTY
  if volt < 3.77: return SYMBOL_BATTERY_1
  if volt < 3.87: return SYMBOL_BATTERY_2
  if volt < 4.15: return SYMBOL_BATTERY_3
  if volt < 4.20: return SYMBOL_BATTERY_FULL
  return SYMBOL_BATTERY_FULL
  pass

m5mqtt = M5mqtt('m5core2_1', '192.168.0.40', 1883, '', '', 300)
#schlaf
m5mqtt.subscribe(str('mqttGenericBridge/Hideki_30_2/temperature'), fun_mqttGenericBridge_Hideki_30_2_temperature_)
m5mqtt.subscribe(str('mqttGenericBridge/Hideki_30_2/humidity'), fun_mqttGenericBridge_Hideki_30_2_humidity_)
#aussen
m5mqtt.subscribe(str('mqttGenericBridge/Hideki_30_1/temperature'), fun_mqttGenericBridge_Hideki_30_1_temperature_)
m5mqtt.subscribe(str('mqttGenericBridge/Hideki_30_1/humidity'), fun_mqttGenericBridge_Hideki_30_1_humidity_)

#bad
m5mqtt.subscribe(str('mqttGenericBridge/Hideki_30_4/humidity'), fun_mqttGenericBridge_Hideki_30_4_humidity_)
m5mqtt.subscribe(str('mqttGenericBridge/Hideki_30_4/temperature'), fun_mqttGenericBridge_Hideki_30_4_temperature_)
m5mqtt.subscribe(str('mqttGenericBridge/duBadTemp/desired'), fun_duBadTemp_temperature_desired_)
m5mqtt.subscribe(str('mqttGenericBridge/duBadTemp/measured'), fun_duBadTemp_temperature_measured_)
m5mqtt.subscribe(str('mqttGenericBridge/duBadTemp/controlMode'), fun_duBadTemp_temperature_controlmode_)
#wohn
m5mqtt.subscribe(str('mqttGenericBridge/SD_WS07_TH_3/humidity'), fun_mqttGenericBridge_SD_WS07_TH_3_humidity_)
m5mqtt.subscribe(str('mqttGenericBridge/SD_WS07_TH_3/temperature'), fun_mqttGenericBridge_SD_WS07_TH_3_temperature_)

#terrasse
m5mqtt.subscribe(str('mqttGenericBridge/SD_WS07_TH_2/humidity'), fun_mqttGenericBridge_SD_WS07_TH_2_humidity_)
m5mqtt.subscribe(str('mqttGenericBridge/SD_WS07_TH_2/temperature'), fun_mqttGenericBridge_SD_WS07_TH_2_temperature_)

m5mqtt.subscribe(str('mqttGenericBridge/duSchlafFenster/status'), fun_mqttGenericBridge_HM_5F5A68_state_)
m5mqtt.subscribe(str('stat/sonoff2/POWER'), fun____stat_sonoff2_POWER_)

#time stuff
ntp = ntptime.client(host='cn.pool.ntp.org', timezone=8)
rtc.settime('ntp', host='cn.pool.ntp.org', tzone=2)
timerSch.run('clocktimer1', 1000, 0x00)
#timerSch.run('clocktimer2', 5000, 0x00) #idle timer run every 5 seconds
m5mqtt.start()

_thread.start_new_thread(idle_counter_thread, ())

"""
## umqtt.simple example
def fun_mqtt_callback(f):
    print('mqtt_callback ' + f.topic.decode('utf-8') + '/' + f.msg.decode('utf-8'))
def mqtt_check():
    assert isinstance(mqttclient, MQTTClient)
    mqttclient.wait_msg() #blocks
#    mqttclient.check_msg()
    wait_ms(500)
    
mqttclient=MQTTClient('m5core2','192.168.0.40',1883,'','',300)
mqttclient.connect()
#gives error:
##Traceback (most recent call last):
##  File "main.py", line 442, in <module>
##  File "umqtt/simple.py", line 201, in subscribe
##  File "umqtt/simple.py", line 77, in _sock_block
##AttributeError: 'NoneType' object has no attribute 'settimeout'
##MicroPython 796b0519b-dirty on 2021-07-23; M5Stack with ESP32

mqttclient.set_callback(fun_mqtt_callback)
mqttclient.subscribe('mqttGenericBridge/HM_5F5A68/state')
#_thread.start_new_thread(mqtt_check, ())
"""
