import sys
# add module search path
sys.path.append('/flash/res')
sys.path.reverse() #revert search direction to load custom libs first

import lvgl as lv
import lvesp32  # driver to create the event loop, see https://forum.lvgl.io/t/olvgl-using-asyncio/4370 if you want to use uasyncio
from machine import mpu6886, axp192, bm8563
from machine import ft6336u     # touch display driver
from axpili9342 import ili9342  # display driver
from m5stack import M5Stack     # required in order to initialize the display driver

from robust2 import MQTTClient2 as _MQTTClient, MQTTException, pid_gen

m5core = M5Stack()

display = ili9342(m5stack=m5core)
mpu = mpu6886()
clock = bm8563()
touch = ft6336u()
axp = axp192()


# lvgl must be initialized before any lvgl function is called or object/struct is constructed!

lv.init()

import display_driver #???
############# main test
"""
#in Linux shell: lv_font_conv --size 12 --format bin --bpp 1 --font segmono_boot.ttf -o segmono_boot-12.bin --range 0x20-0xff
#or use web: https://lvgl.io/tools/fontconverter
## then in micropython

# load the font file from filesystem
myfont = lv.font_load("/flash/res/segmono_boot-12.bin")  # Refer here to convert your font file: https://github.com/lvgl/lv_font_conv

or in Core2 M5Stack????

try
	M5Label("text",0,0,font=myfont,parent=None)
    label=M5Label('test äöpß-end',x=0,y=0, color=0x000000, font=myfont, parent=None)

    from m5stack import *
    import m5stack
    from m5stack_ui import *
    from uiflow import *
    import lvgl as lv
    myfont1=lv.font_load('/flash/res/segmono_boot-16.bin')
    label=M5Label('test p-end',x=0,y=0, color=0x000000, font=myfont1, parent=None)

    label=M5Label('aousz äöüßtest p-end',x=0,y=40, color=0x000000, font=myfont1, parent=None)

    myfont=lv.font_load('/flash/res/segmono_boot-16.bin')
    label=M5Label('test p-end',x=0,y=0, color=0x000000, font=myfont, parent=None)
    ##### above does not work on Core2 :-(

-OR-

import lvgl as lv
lv.init()
screen=lv.scr_act()
screen.clean()
myfont=lv.font_load('/flash/res/segmono_boot-16.bin')
style = lv.style_t()
style.init()
label = lv.label(screen)
style.set_text_font(lv.STATE.DEFAULT, myfont)
label.add_style(label.PART.MAIN, style)
label.set_text("Hi LVGL(Load fonts dynamically)")
label.align(None, lv.ALIGN.CENTER, 0, 0)
##### above does not work on Core2 :-(
"""

"""
#a LV Switch...
def event_handler(e):
    code = e.get_code()
    obj = e.get_target()
    if code == lv.EVENT.VALUE_CHANGED:
        if obj.has_state(lv.STATE.CHECKED):
            print("State: on")
        else:
            print("State: off")


lv.scr_act().set_flex_flow(lv.FLEX_FLOW.COLUMN)
lv.scr_act().set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)

"""
##### main script #####

class CounterBtn():
    def __init__(self):
        self.cnt = 0
        #
        # Create a button with a label and react on click event.
        #

        btn = lv.btn(lv.scr_act())                               # Add a button the current screen
        btn.set_pos(10, 10)                                      # Set its position
        btn.set_size(120, 50)                                    # Set its size
        btn.align(lv.ALIGN.CENTER,0,0)
        btn.add_event_cb(self.btn_event_cb, lv.EVENT.ALL, None)  # Assign a callback to the button
        label = lv.label(btn)                                    # Add a label to the button
        label.set_text("Button")                                 # Set the labels text
        label.center()

    def btn_event_cb(self,evt):
        code = evt.get_code()
        btn = evt.get_target()
        if code == lv.EVENT.CLICKED:
            self.cnt += 1

        # Get the first child of the button which is the label and change its text
        label = btn.get_child(0)
        label.set_text("Button: " + str(self.cnt))

class M5Label:
    def __init__(self, txt="", x=0, y=0, color=0xff0000, font=None, parent=lv.scr_act()):
        lbl=lv.label(parent)
        lbl.set_style_text_font(lv.font_montserrat_16, 0)
#        lv.set_style_text_font(lbl,lv.lv_font_montserrat_28)
#        lbl.set_style(lv.label.STYLE.MAIN, mystyle)
#        mystyle.text.font=lv_font_montserrat_28
        #lbl.set_style_text_font(lv_font_montserrat_28, 0)
        lbl.set_pos(x,y)
        #lbl.set_size(10,10)
        lbl.set_text(txt)

text=lv.label(lv.scr_act())
text.set_pos(10,10)
text.set_size(60,20)
text.set_text('Hallo')

mylabels=[]
for i in range (1,20):
    mylabels.append(M5Label(txt='m5label'+str(i),x=10,y=(i*30)))
