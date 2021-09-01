#m5home

This is a project for the m5stack Core2 ESP32 with color touchscreen, Wifi, speaker and more.

The code connects to a MQTT broker and displays information of my house automation server implemented in FHEM. It also controls a sonoff (tasmota firmware) light switch via MQTT.

Unfortunately the m5stack micropython implementation is not documented very well. More worst is that the general LVGL micropython documentation just does not exist. Most internet findings are about C code for LVGL but not for the micropython lv_binding. I tried to implement the code in true Micropython with LV_Binding, but the current available firmware (thuelinger) only implements two small fonts. That did not satisfy the need for this project.

So the project is implemented in m5stack's micropython implementation with umqtt2 robust module for MQTT. The m5stack MQTT would need one subscription for every topic and payload. There is no way to have one callback with the topic information and payload for multiple topics.

The umqtt2 robust module only needs one subscription for a topic subtree and one callback. The callback then receives the topic and payload.

    #topic subscription
    t='mqttGenericBridge/#' # can only subscribe to one topic tree and only one MQTTClient allowed?
    t2='cmnd/#'
    c=_MQTTClient('m5core2','192.168.0.40',1883,'','',300)
    c.connect()
    c.set_callback(fun_mqtt_callback)
    c.set_callback_status(fun_mqtt_status_callback)
    
Inside the callback, the topic and paylod (message) is extracted and sets the different on-screen text elements.

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
    ...

I use a dictionary to make access to the text elements a bit dynamic. But due to the different topics and payloads, that can not be used for all to 'connect' some information to the gui.

There is also a switch that controls a sonoff tasmota device:

    #this will publish msg to topic
    # i.e. str('cmnd/sonoff2/power'),str('on'))
    def publish(t,m):
        global c
        topic=t.encode('utf-8')
        msg=m.encode('utf-8')
        c.publish(topic=topic, msg=msg, retain=False, qos=1)
        pass
    
    def switchOn2():
        publish('cmnd/sonoff2/power','on')
        pass
    def switchOff2():
        publish('cmnd/sonoff2/power','off')
        pass
    
    switch2 = M5Switch(x=165, y=ynext, w=70, h=30, bg_c=0xCCCCCC, color=0x0288FB, parent=None)
    switch2.on(switchOn2)
    
    switch2.off(switchOff2)
    ...

As most of the information has the same structure (a text and a value), they are instances of a simple class. So the ui is more consistent and can be changed from a single point.

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
    
Although I started using UIFlow to program the Core2, it was very limited a) for more complex code b) does not offer all features of m5stack

I use thonny for programming, upload and download the code and get some insights of the micropython on the Core2. As a remote console I also used mpfshell/repl and to manage files ampy. The command terminal is very helpful to find modules. Unfortunately the function arguments are not clear.
You can do a 'import m5stack_ui' and the a 'dir(m5stack_ui)' to get a list of all objects of the m5stack_ui module. The command 

    help('modules') 

gives a list of all modules available. But as said, it is frustrating to see all these but cannot use without a documentation.

I looked for a way to show one information on all screens (ie the time, battery and RSSI) and did not find it for m5stack although LVGL has top_layer and sys_layer.

Currently the project shows 5 screens that can be switched with the left and right sensor button of the Core2. There is a idle timer that dims the backlight after 15 seconds. and there is one thread driving the MQTT message pump. I was unable to use a second thread (limitation of ESP32 micropython or m5stack) and so implemented a timer for the idle stuff.

The other project main.py shows how to use an image and shows temperature and humidity inside that. As Core2 loads images very slow, I abandoned that.

I also tried pure ESP32 M5CORE2 and M5CORE2_BOARD with ESP-IDF and Thuelinger's repo patches (https://github.com/thuehlinger/micropython-core2) to compile, but this always fails od shows unreliable on the Core2. Although the pre-compiled binary worked for the main_test.py supplied by Thuelinger, I was unable to compile myself to be able to add more fonts.