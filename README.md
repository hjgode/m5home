# m5home
simple use of MQTT to show some data of my FHEM on the Core2

Here are my experiments with the micropython implementation :-( by m5stack in the Core2. Bad documentation, incomplete Micropython modules, bad REPL.

The first (main.py) uses M5MQTT client and I needed to implement a new callback and subscription for every data I want to consume and show in the app. The app also shows the slow image processing, although the image page I designed is able to show 8 values on the small screen with a nice UI.

The second (main_umqtt2.py) used simple2.umqtt and now robust2.umqtt libs I found luckily. Here I only use simple UI elements like text and switch. Only two subscriptions and one callback function to be uesd :-)

So, the second one is easier to maintain. The data is 're-directed' inside the callback to the right UI.

Both apps use different screens that are loaded by pressing the left and right soft button on the Core2.

Both apps also have a idle timer to dim the display after 15 seconds.

You will find some special things like how to get the local IP, the RSSI of the AP and more.
