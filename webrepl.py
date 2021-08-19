import sys
# add module search path
sys.path.append('/flash/res')
sys.path.reverse() #revert search direction to load custom libs first

# This module should be imported from REPL, not run from command line.
import socket
import uos
import network
import websocket
import websocket_helper
import _webrepl
import wifiCfg

listen_s = None
client_s = None

def setup_conn(port, accept_handler):
    global listen_s
    listen_s = socket.socket()
    listen_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    ai = socket.getaddrinfo("0.0.0.0", port)
    addr = ai[0][4]

    listen_s.bind(addr)
    listen_s.listen(1)
    if accept_handler:
        listen_s.setsockopt(socket.SOL_SOCKET, 20, accept_handler)
    for i in (network.AP_IF, network.STA_IF):
        iface = network.WLAN(i)
        if iface.active():
            print("WebREPL daemon started on ws://%s:%d" % (iface.ifconfig()[0], port))
    return listen_s


def accept_conn(listen_sock):
    global client_s
    cl, remote_addr = listen_sock.accept()
    print("\nWebREPL connection from:", remote_addr)
    client_s = cl
    websocket_helper.server_handshake(cl)
    ws = websocket.websocket(cl, True)
    ws = _webrepl._webrepl(ws)
    cl.setblocking(False)
    # notify REPL on socket incoming data
    cl.setsockopt(socket.SOL_SOCKET, 20, uos.dupterm_notify)
    uos.dupterm(ws)


def stop():
    global listen_s, client_s
    uos.dupterm(None)
    if client_s:
        client_s.close()
    if listen_s:
        listen_s.close()


def start(port=8266, password=None):
    stop()
    if password is None:
        try:
            import port_config
            _webrepl.password(port_config.WEBREPL_PASS)
            setup_conn(port, accept_conn)
            print("Started webrepl in normal mode")
        except:
            import webrepl_setup
            setup_conn(port, webrepl_setup.handle_conn)
            print("Started webrepl in setup mode")
    else:
        _webrepl.password(password)
        setup_conn(port, accept_conn)
        print("Started webrepl in normal mode")


def start_foreground(port=8266):
    stop()
    s = setup_conn(port, None)
    accept_conn(s)

#connect to wifi
wifiCfg.autoConnect(lcdShow=True)
wifiCfg.doConnect('Horst1', '1234567890123')
print("Wifi connected: ", str(wifiCfg.is_connected()))
print(wifiCfg.wlan_sta.ifconfig())

stop()

#start_foreground(8266)
#start()
_webrepl.password('chopper')
setup_conn(8266, accept_conn)
print("Started webrepl in normal mode")

while True:
    try:
        time.sleep_ms(500)
    except (KeyboardInterrupt) as e:
        print('program interrupted')
        stop()
        time.sleep(2000)
        sys.exit()
        
    pass    

stop()
