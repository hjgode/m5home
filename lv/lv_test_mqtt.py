import sys
# add module search path
sys.path.append('/flash/res')
sys.path.reverse() #revert search direction to load custom libs first

import lvgl as lv
import m5stack
import network
import ntptime
import time
import utime
import _thread
from machine import Timer
import m5stack_ui
import hardware #for rtc

#from umqtt.simple import MQTTClient 
from robust2 import MQTTClient2 as _MQTTClient, MQTTException, pid_gen

sta_if=network.WLAN(network.STA_IF)

def do_connect():
    global sta_if, labelClock
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect('Horst1', '1234567890123')
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())
    if labelClock!=None:
        labelIP.set_text(sta_if.ifconfig()[0])
    pass

myfont_segmono20 = lv.font_load("/flash/res/segmono_boot20.fon") #does not work

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
  def __init__(self, x=0, txtlabel='label', txtvalue='value'):
#    assert isinstance(x, int) and isinstance(y, int)
    # self. starts a instance variable
    self.posx = x
    self.posy = self.line*(self.line_spacing) #automatically add y pos
    InfoItem.last_posy=self.posy
    scrItem=lv.scr_act()
#lv.label.set_style_local_text_font(labelc, lv.label.PART.MAIN, lv.STATE.DEFAULT, lv.font_montserrat_12)  # set the font
    myfont=lv.font_montserrat_32 # myfont_segmono20 does not work
    mycolor=0x000000
    print('InfoTime ',InfoItem.line) #access the shared var
    self.txtlabel=txtlabel
    self.txtvalue=txtvalue
    self.label=lv.label(scrItem)
    self.label.set_text(self.txtlabel)

    lv.label.set_style_local_text_font(self.label, lv.label.PART.MAIN, lv.STATE.DEFAULT, myfont)  # set the font
#    self.label.set_size(160,150) #size is adjusted to text automatically, except for #label2.set_long_mode(lv.label.LONG.CROP)
    self.label.set_pos(self.posx+self.leftOffset,self.posy+self.topOffset)
#    self.label.set_text_color(mycolor)
    lv.label.set_style_local_text_color(self.label, lv.label.PART.MAIN, lv.STATE.DEFAULT, lv.color_hex(mycolor))

#    self.value=M5Label(self.value,x=self.posx+self.midOffset,y=self.posy+self.topOffset, color=mycolor, font=myfont, parent=None)
    self.value=lv.label(scrItem)
    self.value.set_text(self.txtvalue)
    lv.label.set_style_local_text_font(self.value, lv.label.PART.MAIN, lv.STATE.DEFAULT, myfont)  # set the font
    self.value.set_pos(self.posx+self.midOffset,self.posy+self.topOffset)
    lv.label.set_style_local_text_color(self.value, lv.label.PART.MAIN, lv.STATE.DEFAULT, lv.color_hex(mycolor))
    
    InfoItem.InfoItemList.append(self)
    InfoItem.line+=1
  def setTemp(self, tmp):
    self.value.set_text(tmp + '°C')
  def setHumi(self, tmp):
    self.value.set_text(tmp + '%')
  def setValue(self,tmp):
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

def fun_mqtt_callback(topic, msg, retained, dup):
#    print('callback ',str(topic),":",str(msg))
    global infoAussenTemp
    t=topic.decode('utf-8')
    m=msg.decode('utf-8')
    print('mqtt_callback ' + t + ':' + m+ ", ret="+str(retained) + ", dup=" + str(dup))
    try:
        s=t.split('/')
        infoAussenTemp.setValue(str(m))
    except KeyError:
        pass
#    print('mqtt_callback ' + f.topic.decode('utf-8') + '/' + f.msg.decode('utf-8'))

def fun_mqtt_status_callback(pid,status):
    print('mqtt_status_callback: status=',str(status),", pid=",str(pid))
    pass
"""
    status = 0 - timeout
            status = 1 - successfully delivered
            status = 2 - Unknown PID. It is also possible that the PID is outdated,
                         i.e. it came out of the message timeout.
"""


#########################################################################
lv.init()

m5stack_ui.M5Screen().set_screen_brightness(30)

################## top layer #############
top=lv.layer_top()

labelIP=lv.label(top)
labelIP.align(top, lv.ALIGN.IN_BOTTOM_LEFT, 5, 0)
#lt.set_pos(10,219)
labelIP.set_text(sta_if.ifconfig()[0])

labelClock=lv.label(top)
labelClock.set_text('01.01.2021 11:59:55')
#labelClock.get_width()
labelClock.align(top, lv.ALIGN.IN_BOTTOM_RIGHT, -5, 0)
#lt.set_pos(10,219)

################# end top layer ##########
#scr2=lv.obj()
#scr2.clean()
#lv.scr_load(scr2)

scr0=lv.obj()
scr0.clean()
labelc = lv.label(scr0)
lv.label.set_style_local_text_font(labelc, lv.label.PART.MAIN, lv.STATE.DEFAULT, lv.font_montserrat_12)  # set the font
labelc.set_size(160,150)
labelc.set_pos(10,180)
#label2.set_long_mode(lv.label.LONG.CROP)
labelc.set_align(lv.label.ALIGN.RIGHT)
labelc.set_text_fmt("Value: %i", 15)
labelc.set_text('Connecting')
lv.scr_load(scr0)
scr0=lv.scr_act()
while not sta_if.isconnected():
    pass
scr0.clean()
######################## end scr0 #################

do_connect()

#myfont_cn = lv.font_load("/flash/res/font-PHT-en-20.bin") #does not work
myfont_cn = lv.font_montserrat_42

################### screen 1 ###################
scr = lv.obj()
scr.clean()
m5stack_ui.M5Screen().set_screen_brightness(60)

mystyle=lv.style_t()
lv.style_t.set_text_font(mystyle, lv.label.PART.MAIN, lv.font_montserrat_28)
scr.add_style(0,mystyle)

btn = lv.btn(scr)
#btn.set_size(160,80)
btn.align(lv.scr_act(), lv.ALIGN.IN_TOP_MID, 0, 0)

label = lv.label(btn) #btn
label.add_style(0,mystyle)

#lv.label.set_style_local_text_font(label, lv.label.PART.MAIN, lv.STATE.DEFAULT, lv.font_montserrat_32)  # set the font
label.set_text("mystyle")

label2 = lv.label(scr)
lv.label.set_style_local_text_font(label2, lv.label.PART.MAIN, lv.STATE.DEFAULT, lv.font_montserrat_12)  # set the font
label2.set_size(160,150)
label2.set_pos(10,180)
#label2.set_long_mode(lv.label.LONG.CROP)
label2.set_align(lv.label.ALIGN.RIGHT)
label2.set_text_fmt("Value: %i", 15)

label3 = lv.label(scr)
lv.label.set_style_local_text_font(label3, lv.label.PART.MAIN, lv.STATE.DEFAULT, myfont_cn)  # set the font
label3.set_size(160,40)
#either use align or set_pos
label3.align(scr, lv.ALIGN.IN_TOP_LEFT,10,120)
#label3.set_pos(10,120)
#label3.set_long_mode(lv.label.LONG.CROP)
#label2.set_align(lv.label.ALIGN.RIGHT)
label3.set_text("label3")

def event_handler(obj,evt):
    if evt == lv.EVENT.VALUE_CHANGED:
        state = obj.get_state()
        if state:
            print("State: On")
        else:
            print("State: Off")            

#Create a switch and apply the styles
sw1 = lv.switch(scr)
#sw1.set_pos(100,40)
sw1.set_size(80,40)
#align to right and top and move from there with x and y
sw1.align(None, lv.ALIGN.IN_TOP_RIGHT, -20, 40) #either use align to po or set_pos
sw1.set_event_cb(event_handler)

labelsw1=lv.label(scr)
lv.label.set_style_local_text_font(labelsw1, lv.label.PART.MAIN, lv.STATE.DEFAULT, lv.font_montserrat_28)  # set the font
labelsw1.set_text('Switch Label:')
labelsw1.align(sw1, lv.ALIGN.IN_TOP_MID, -(labelsw1.get_width()), 0)#int(sw1.get_height()/2))
sw1.on(lv.ANIM.ON)

def buttonA_wasPressed():
  # global params
  print('ButtonA pressed')
  if lv.switch.get_state(sw1):
      sw1.off(lv.ANIM.OFF)
  else:
      sw1.on(lv.ANIM.ON)
  pass
m5stack.btnA.wasPressed(buttonA_wasPressed)

scr=lv.scr_act()
###################### end screen 1 ######################

#######################start screen 2 ####################
scr2=lv.obj()
scr2.clean()
infoAussenTemp=InfoItem(x=0,txtlabel='Aussen:',txtvalue='21.0°C')
scr2=lv.scr_act()

####################### end screen 2 ####################

#lv.scr_load(scr)

lv.scr_load(scr2)

print('ntp time update for RTC')
rtc=hardware.RTC()
rtc.settime('ntp', host='cn.pool.ntp.org', tzone=2)
t=rtc.datetime()
datetimetxt = '{:02d}.{:02d}.{:04d} {:02d}:{:02d}:{:02d}'.format(t[2], t[1], t[0], t[4], t[5], t[6])
print(datetimetxt)

######################
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
#######################
def idle_counter_thread(timer):
    try:      
        print('timer called')
    except Exception as e:
        print('idle_counter_thread Exception: ',str(e))
        return
    except (KeyboardInterrupt) as e:
        print('program interrupted')
        bThreadsRun=False
        time.sleep(2000)
        sys.exit()
#  finally:
#      lockIdle.release()
#      wait_ms(1000)
#  _thread.start_new_thread(idle_counter_thread, ())

    pass
timer0 = Timer(0)
timer0.init(period=1000, mode=Timer.PERIODIC, callback=idle_counter_thread)

#######################
bThreadsRun=True
def updateThread():
    print('updateThread called')
    global c, bThreadsRun
    while bThreadsRun:
        try:
            m5stack.lv.task_handler()
            time.sleep_ms(100)
            c.wait_msg() #blocking call
        except (KeyboardInterrupt) as e:
            print('program interrupted')
            bThreadsRun=False
            time.sleep(2000)
            sys.exit()
_thread.start_new_thread(updateThread, ())

#######################

while True:
    try:
        print('press Ctrl+C to stop app')
        m5stack.lv.task_handler()
        time.sleep_ms(500)
    except (KeyboardInterrupt) as e:
        print('program interrupted')
        bThreadsRun=False
        timer0.deinit()
        time.sleep(2000)
        sys.exit()
        
    pass    
