import sys
sys.path.append('/flash/res')
#sys.path.reverse() #revert search direction to load custom libs first

import usocket as socket
import uselect
from utime import ticks_add, ticks_ms, ticks_diff
#import simple2

class MQTTException(Exception):
    pass


def pid_gen(pid=0):
    while True:
        pid = pid + 1 if pid < 65535 else 1
        yield pid


class MQTTClient:

    def __init__(self, client_id, server, port=0, user=None, password=None, keepalive=0,
                 ssl=False, ssl_params=None, socket_timeout=5, message_timeout=10):
        """
        Default constructor, initializes MQTTClient object.

        :param client_id:  Unique MQTT ID attached to client.
        :type client_id: str
        :param server: MQTT host address.
        :type server str
        :param port: MQTT Port, typically 1883. If unset, the port number will default to 1883 of 8883 base on ssl.
        :type port: int
        :param user: Username if your server requires it.
        :type user: str
        :param password: Password if your server requires it.
        :type password: str
        :param keepalive: The Keep Alive is a time interval measured in seconds since the last
                          correct control packet was received.
        :type keepalive: int
        :param ssl: Require SSL for the connection.
        :type ssl: bool
        :param ssl_params: Required SSL parameters.
        :type ssl_params: dict
        :param socket_timeout: The time in seconds after which the socket interrupts the connection to the server when
                               no data exchange takes place. None - socket blocking, positive number - seconds to wait.
        :type socket_timeout: int
        :param message_timeout: The time in seconds after which the library recognizes that a message with QoS=1
                                or topic subscription has not been received by the server.
        :type message_timeout: dict
        """
        if port == 0:
            port = 8883 if ssl else 1883
        self.client_id = client_id
        self.sock = None
        self.poller = None
        self.server = server
        self.port = port
        self.ssl = ssl
        self.ssl_params = ssl_params if ssl_params else {}
        self.newpid = pid_gen()
        if not getattr(self, 'cb', None):
            self.cb = None
        if not getattr(self, 'cbstat', None):
            self.cbstat = lambda p, s: None
        self.user = user
        self.pswd = password
        self.keepalive = keepalive
        self.lw_topic = None
        self.lw_msg = None
        self.lw_qos = 0
        self.lw_retain = False
        self.rcv_pids = {}  # PUBACK and SUBACK pids awaiting ACK response

        self.last_ping = ticks_ms()  # Time of the last PING sent
        self.last_cpacket = ticks_ms()  # Time of last Control Packet

        self.socket_timeout = socket_timeout
        self.message_timeout = message_timeout

    def _read(self, n):
        """
        Private class method.

        :param n: Expected length of read bytes
        :type n: int
        :return:
        """
        # in non-blocking mode, may not download enough data
        try:
            msg = b''
            for i in range(n):
                self._sock_timeout(self.poller_r, self.socket_timeout)
                msg += self.sock.read(1)
        except AttributeError:
            raise MQTTException(8)
        if msg == b'':  # Connection closed by host (?)
            raise MQTTException(1)
        if len(msg) != n:
            raise MQTTException(2)
        return msg

    def _write(self, bytes_wr, length=-1):
        """
        Private class method.

        :param bytes_wr: Bytes sequence for writing
        :type bytes_wr: bytes
        :param length: Expected length of write bytes
        :type length: int
        :return:
        """
        # In non-blocking socket mode, the entire block of data may not be sent.
        try:
            self._sock_timeout(self.poller_w, self.socket_timeout)
            out = self.sock.write(bytes_wr, length)
        except AttributeError:
            raise MQTTException(8)
        if length < 0:
            if out != len(bytes_wr):
                raise MQTTException(3)
        else:
            if out != length:
                raise MQTTException(3)
        return out

    def _send_str(self, s):
        """
        Private class method.
        :param s:
        :type s: byte
        :return: None
        """
        assert len(s) < 65536
        self._write(len(s).to_bytes(2, 'big'))
        self._write(s)

    def _recv_len(self):
        """
        Private class method.
        :return:
        :rtype int
        """
        n = 0
        sh = 0
        while 1:
            b = self._read(1)[0]
            n |= (b & 0x7f) << sh
            if not b & 0x80:
                return n
            sh += 7

    def _varlen_encode(self, value, buf, offset=0):
        assert value < 268435456  # 2**28, i.e. max. four 7-bit bytes
        while value > 0x7f:
            buf[offset] = (value & 0x7f) | 0x80
            value >>= 7
            offset += 1
        buf[offset] = value
        return offset + 1

    def _sock_timeout(self, poller, socket_timeout):
        if self.sock:
            res = poller.poll(-1 if socket_timeout is None else int(socket_timeout * 1000))
            if not res:
                raise MQTTException(30)
        else:
            raise MQTTException(28)

    def set_callback(self, f):
        """
        Set callback for received subscription messages.

        :param f: callable(topic, msg, retained, duplicate)
        """
        self.cb = f

    def set_callback_status(self, f):
        """
        Set the callback for information about whether the sent packet (QoS=1)
        or subscription was received or not by the server.

        :param f: callable(pid, status)

        Where:
            status = 0 - timeout
            status = 1 - successfully delivered
            status = 2 - Unknown PID. It is also possible that the PID is outdated,
                         i.e. it came out of the message timeout.
        """
        self.cbstat = f

    def set_last_will(self, topic, msg, retain=False, qos=0):
        """
        Sets the last will and testament of the client. This is used to perform an action by the broker
        in the event that the client "dies".
        Learn more at https://www.hivemq.com/blog/mqtt-essentials-part-9-last-will-and-testament/

        :param topic: Topic of LWT. Takes the from "path/to/topic"
        :type topic: byte
        :param msg: Message to be published to LWT topic.
        :type msg: byte
        :param retain: Have the MQTT broker retain the message.
        :type retain: bool
        :param qos: Sets quality of service level. Accepts values 0 to 2. PLEASE NOTE qos=2 is not actually supported.
        :type qos: int
        :return: None
        """
        assert 0 <= qos <= 2
        assert topic
        self.lw_topic = topic
        self.lw_msg = msg
        self.lw_qos = qos
        self.lw_retain = retain

    def connect(self, clean_session=True):
        """
        Establishes connection with the MQTT server.

        :param clean_session: Starts new session on true, resumes past session if false.
        :type clean_session: bool
        :return: Existing persistent session of the client from previous interactions.
        :rtype: bool
        """
        self.sock = socket.socket()
        self.poller_r = uselect.poll()
        self.poller_r.register(self.sock, uselect.POLLIN)
        self.poller_w = uselect.poll()
        self.poller_w.register(self.sock, uselect.POLLOUT)
        addr = socket.getaddrinfo(self.server, self.port)[0][-1]
        self.sock.connect(addr)
        if self.ssl:
            import ussl
            self.sock = ussl.wrap_socket(self.sock, **self.ssl_params)

        # Byte nr - desc
        # 1 - \x10 0001 - Connect Command, 0000 - Reserved
        # 2 - Remaining Length
        # PROTOCOL NAME (3.1.2.1 Protocol Name)
        # 3,4 - protocol name length len('MQTT')
        # 5-8 = 'MQTT'
        # PROTOCOL LEVEL (3.1.2.2 Protocol Level)
        # 9 - mqtt version 0x04
        # CONNECT FLAGS
        # 10 - connection flags
        #  X... .... = User Name Flag
        #  .X.. .... = Password Flag
        #  ..X. .... = Will Retain
        #  ...X X... = QoS Level
        #  .... .X.. = Will Flag
        #  .... ..X. = Clean Session Flag
        #  .... ...0 = (Reserved) It must be 0!
        # KEEP ALIVE
        # 11,12 - keepalive
        # 13,14 - client ID length
        # 15-15+len(client_id) - byte(client_id)
        premsg = bytearray(b"\x10\0\0\0\0\0")
        msg = bytearray(b"\0\x04MQTT\x04\0\0\0")

        sz = 10 + 2 + len(self.client_id)

        msg[7] = bool(clean_session) << 1
        # Clean session = True, remove current session
        if bool(clean_session):
            self.rcv_pids.clear()
        if self.user is not None:
            sz += 2 + len(self.user)
            msg[7] |= 1 << 7  # User Name Flag
            if self.pswd is not None:
                sz += 2 + len(self.pswd)
                msg[7] |= 1 << 6  # # Password Flag
        if self.keepalive:
            assert self.keepalive < 65536
            msg[8] |= self.keepalive >> 8
            msg[9] |= self.keepalive & 0x00FF
        if self.lw_topic:
            sz += 2 + len(self.lw_topic) + 2 + len(self.lw_msg)
            msg[7] |= 0x4 | (self.lw_qos & 0x1) << 3 | (self.lw_qos & 0x2) << 3
            msg[7] |= self.lw_retain << 5

        plen = self._varlen_encode(sz, premsg, 1)
        self._write(premsg, plen)
        self._write(msg)
        self._send_str(self.client_id)
        if self.lw_topic:
            self._send_str(self.lw_topic)
            self._send_str(self.lw_msg)
        if self.user is not None:
            self._send_str(self.user)
            if self.pswd is not None:
                self._send_str(self.pswd)
        resp = self._read(4)
        if not (resp[0] == 0x20 and resp[1] == 0x02):  # control packet type, Remaining Length == 2
            raise MQTTException(29)
        if resp[3] != 0:
            if 1 <= resp[3] <= 5:
                raise MQTTException(20 + resp[3])
            else:
                raise MQTTException(20, resp[3])
        self.last_cpacket = ticks_ms()
        return resp[2] & 1  # Is existing persistent session of the client from previous interactions.

    def disconnect(self):
        """
        Disconnects from the MQTT server.
        :return: None
        """
        self._write(b"\xe0\0")
        self.poller_r.unregister(self.sock)
        self.poller_w.unregister(self.sock)
        self.sock.close()
        self.sock = None
        self.poller = None

    def ping(self):
        """
        Pings the MQTT server.
        :return: None
        """
        self._write(b"\xc0\0")
        self.last_ping = ticks_ms()

    def publish(self, topic, msg, retain=False, qos=0, dup=False):
        """
        Publishes a message to a specified topic.

        :param topic: Topic you wish to publish to. Takes the form "path/to/topic"
        :type topic: byte
        :param msg: Message to publish to topic.
        :type msg: byte
        :param retain: Have the MQTT broker retain the message.
        :type retain: bool
        :param qos: Sets quality of service level. Accepts values 0 to 2. PLEASE NOTE qos=2 is not actually supported.
        :type qos: int
        :param dup: Duplicate delivery of a PUBLISH Control Packet
        :type dup: bool
        :return: None
        """
        assert qos in (0, 1)
        pkt = bytearray(b"\x30\0\0\0\0")
        pkt[0] |= qos << 1 | retain | int(dup) << 3
        sz = 2 + len(topic) + len(msg)
        if qos > 0:
            sz += 2
        plen = self._varlen_encode(sz, pkt, 1)
        self._write(pkt, plen)
        self._send_str(topic)
        if qos > 0:
            pid = next(self.newpid)
            self._write(pid.to_bytes(2, 'big'))
        self._write(msg)
        if qos > 0:
            self.rcv_pids[pid] = ticks_add(ticks_ms(), self.message_timeout * 1000)
            return pid

    def subscribe(self, topic, qos=0):
        """
        Subscribes to a given topic.

        :param topic: Topic you wish to publish to. Takes the form "path/to/topic"
        :type topic: byte
        :param qos: Sets quality of service level. Accepts values 0 to 1. This gives the maximum QoS level at which
                    the Server can send Application Messages to the Client.
        :type qos: int
        :return: None
        """
        assert qos in (0, 1)
        assert self.cb is not None, "Subscribe callback is not set"
        pkt = bytearray(b"\x82\0\0\0\0\0\0")
        pid = next(self.newpid)
        sz = 2 + 2 + len(topic) + 1
        plen = self._varlen_encode(sz, pkt, 1)
        pkt[plen:plen + 2] = pid.to_bytes(2, 'big')
        self._write(pkt, plen + 2)
        self._send_str(topic)
        self._write(qos.to_bytes(1, "little"))  # maximum QOS value that can be given by the server to the client
        self.rcv_pids[pid] = ticks_add(ticks_ms(), self.message_timeout * 1000)
        return pid

    def _message_timeout(self):
        curr_tick = ticks_ms()
        for pid, timeout in self.rcv_pids.items():
            if ticks_diff(timeout, curr_tick) <= 0:
                self.rcv_pids.pop(pid)
                self.cbstat(pid, 0)

    def check_msg(self):
        """
        Checks whether a pending message from server is available.

        If socket_timeout=None, this is the socket lock mode. That is, it waits until the data can be read.

        Otherwise it will return None, after the time set in the socket_timeout.

        It processes such messages:
        - response to PING
        - messages from subscribed topics that are processed by functions set by the set_callback method.
        - reply from the server that he received a QoS=1 message or subscribed to a topic

        :return: None
        """
        if self.sock:
            if not self.poller_r.poll(-1 if self.socket_timeout is None else 1):
                self._message_timeout()
                return None
            try:
                res = self._read(1)  # Throws OSError on WiFi fail
                if not res:
                    self._message_timeout()
                    return None
            except OSError as e:
                if e.args[0] == 110:  # Occurs when no incomming data
                    self._message_timeout()
                    return None
                else:
                    raise e
        else:
            raise MQTTException(28)

        if res == b"\xd0":  # PINGRESP
            if self._read(1)[0] != 0:
                MQTTException(-1)
            self.last_cpacket = ticks_ms()
            return

        op = res[0]

        if op == 0x40:  # PUBACK
            sz = self._read(1)
            if sz != b"\x02":
                raise MQTTException(-1)
            rcv_pid = int.from_bytes(self._read(2), 'big')
            if rcv_pid in self.rcv_pids:
                self.last_cpacket = ticks_ms()
                self.rcv_pids.pop(rcv_pid)
                self.cbstat(rcv_pid, 1)
            else:
                self.cbstat(rcv_pid, 2)

        if op == 0x90:  # SUBACK Packet fixed header
            resp = self._read(4)
            # Byte - desc
            # 1 - Remaining Length 2(varible header) + len(payload)=1
            # 2,3 - PID
            # 4 - Payload
            if resp[0] != 0x03:
                raise MQTTException(40, resp)
            if resp[3] == 0x80:
                raise MQTTException(44)
            if resp[3] not in (0, 1, 2):
                raise MQTTException(40, resp)
            pid = resp[2] | (resp[1] << 8)
            if pid in self.rcv_pids:
                self.last_cpacket = ticks_ms()
                self.rcv_pids.pop(pid)
                self.cbstat(pid, 1)
            else:
                raise MQTTException(5)

        self._message_timeout()

        if op & 0xf0 != 0x30:  # 3.3 PUBLISH – Publish message
            return op
        sz = self._recv_len()
        topic_len = int.from_bytes(self._read(2), 'big')
        topic = self._read(topic_len)
        sz -= topic_len + 2
        if op & 6:  # QoS level > 0
            pid = int.from_bytes(self._read(2), 'big')
            sz -= 2
        msg = self._read(sz) if sz else b''
        retained = op & 0x01
        dup = op & 0x08
        self.cb(topic, msg, bool(retained), bool(dup))
        self.last_cpacket = ticks_ms()
        if op & 6 == 2:  # QoS==1
            self._write(b"\x40\x02")  # Send PUBACK
            self._write(pid.to_bytes(2, 'big'))
        elif op & 6 == 4:  # QoS==2
            raise NotImplementedError()
        elif op & 6 == 6:  # 3.3.1.2 QoS - Reserved – must not be used
            raise MQTTException(-1)

    def wait_msg(self):
        """
        This method waits for a message from the server.

        Compatibility with previous versions.

        It is recommended not to use this method. Set socket_time=None instead.
        """
        st_old = self.socket_timeout
        self.socket_timeout = None
        out = self.check_msg()
        self.socket_timeout = st_old
        return out
    pass

class MQTTClient2(MQTTClient):
    DEBUG = False

    # Information whether we store unsent messages with the flag QoS==0 in the queue.
    KEEP_QOS0 = True
    # Option, limits the possibility of only one unique message being queued.
    NO_QUEUE_DUPS = True
    # Limit the number of unsent messages in the queue.
    MSG_QUEUE_MAX = 5
    # When you reconnect, all existing subscriptions are renewed.
    RESUBSCRIBE = True

    def __init__(self, *args, **kwargs):
        """
        See documentation for `umqtt.MQTTClient.__init__()`
        """
        super().__init__(*args, **kwargs)
        self.subs = []  # List of stored subscriptions
        self.msg_to_send = []  # Queue with list of messages to send
        self.sub_to_send = []  # Queue with list of subscriptions to send
        self.msg_to_confirm = {}  # Queue with a list of messages waiting for the server to confirm of the message.
        self.sub_to_confirm = {}  # Queue with a subscription list waiting for the server to confirm of the subscription
        self.conn_issue = None  # We store here if there is a connection problem.

    def is_keepalive(self):
        """
        It checks if the connection is active. If the connection is not active at the specified time,
        saves an error message and returns False.

        :return: If the connection is not active at the specified time returns False otherwise True.
        """
        time_from__last_cpackage = ticks_diff(ticks_ms(), self.last_cpacket) // 1000
        if 0 < self.keepalive < time_from__last_cpackage:
            self.conn_issue = (MQTTException(7), 9)
            return False
        return True

    def set_callback_status(self, f):
        """
        See documentation for `umqtt.MQTTClient.set_callback_status()`
        """
        self._cbstat = f

    def cbstat(self, pid, stat):
        """
        Captured message statuses affect the queue here.

        stat == 0 - the message goes back to the message queue to be sent
        stat == 1 or 2 - the message is removed from the queue
        """
        try:
            self._cbstat(pid, stat)
        except AttributeError:
            pass

        for data, pids in self.msg_to_confirm.items():
            if pid in pids:
                if stat == 0:
                    self.msg_to_send.insert(0, data)
                pids.remove(pid)
                if not pids:
                    self.msg_to_confirm.pop(data)
                return

        for data, pids in self.sub_to_confirm.items():
            if pid in pids:
                if stat == 0:
                    self.sub_to_send.append(data)
                pids.remove(pid)
                if not pids:
                    self.sub_to_confirm.pop(data)

    def connect(self, clean_session=True):
        """
        See documentation for `umqtt.MQTTClient.connect()`.

        If clean_session==True, then the queues are cleared.

        Connection problems are captured and handled by `is_conn_issue()`
        """
        if clean_session:
            self.msg_to_send[:] = []
            self.msg_to_confirm.clear()
        try:
            out = super().connect(clean_session)
            self.conn_issue = None
            return out
        except (OSError, MQTTException) as e:
            self.conn_issue = (e, 1)

    def log(self):
        if self.DEBUG:
            if type(self.conn_issue) is tuple:
                conn_issue, issue_place = self.conn_issue
            else:
                conn_issue = self.conn_issue
                issue_place = 0
            place_str = ('?', 'connect', 'publish', 'subscribe',
                         'reconnect', 'sendqueue', 'disconnect', 'ping', 'wait_msg', 'keepalive', 'check_msg')
            print("MQTT (%s): %r" % (place_str[issue_place], conn_issue))

    def reconnect(self):
        """
        The function tries to resume the connection.

        Connection problems are captured and handled by `is_conn_issue()`
        """
        try:
            out = super().connect(False)
            self.conn_issue = None
            return out
        except (OSError, MQTTException) as e:
            self.conn_issue = (e, 4)
            if self.sock:
                self.sock.close()
                self.sock = None

    def resubscribe(self):
        """
        Function from previously registered subscriptions, sends them again to the server.

        :return:
        """
        for topic, qos in self.subs:
            self.subscribe(topic, qos, False)

    def add_msg_to_send(self, data):
        """
        By overwriting this method, you can control the amount of stored data in the queue.
        This is important because we do not have an infinite amount of memory in the devices.

        Currently, this method limits the queue length to MSG_QUEUE_MAX messages.

        The number of active messages is the sum of messages to be sent with messages awaiting confirmation.

        :param data:
        :return:
        """
        # Before we add data to the queue, it is necessary to release the memory first.
        # Otherwise, we may fall into an infinite loop due to a lack of available memory.
        messages_count = len(self.msg_to_send)
        messages_count += sum(map(len, self.msg_to_confirm.values()))

        while messages_count >= self.MSG_QUEUE_MAX:
            min_msg_to_confirm = min(map(lambda x: x[0] if x else 65535, self.msg_to_confirm.values()), default=0)
            if 0 < min_msg_to_confirm < 65535:
                key_to_check = None
                for k, v in self.msg_to_confirm.items():
                    if v and v[0] == min_msg_to_confirm:
                        del v[0]
                        key_to_check = k
                        break
                if key_to_check and key_to_check in self.msg_to_confirm and not self.msg_to_confirm[key_to_check]:
                    self.msg_to_confirm.pop(key_to_check)
            else:
                self.msg_to_send.pop(0)
            messages_count -= 1

        self.msg_to_send.append(data)

    def disconnect(self):
        """
        See documentation for `umqtt.MQTTClient.disconnect()`

        Connection problems are captured and handled by `is_conn_issue()`
        """
        try:
            return super().disconnect()
        except (OSError, MQTTException) as e:
            self.conn_issue = (e, 6)

    def ping(self):
        """
        See documentation for `umqtt.MQTTClient.ping()`

        Connection problems are captured and handled by `is_conn_issue()`
        """
        if not self.is_keepalive():
            return
        try:
            return super().ping()
        except (OSError, MQTTException) as e:
            self.conn_issue = (e, 7)

    def publish(self, topic, msg, retain=False, qos=0):
        """
        See documentation for `umqtt.MQTTClient.publish()`

        The function tries to send a message. If it fails, the message goes to the message queue for sending.

        The function does not support the `dup` parameter!

        When we have messages with the retain flag set, only one last message with that flag is sent!

        Connection problems are captured and handled by `is_conn_issue()`

        :return: None od PID for QoS==1 (only if the message is sent immediately, otherwise it returns None)
        """
        data = (topic, msg, retain, qos)
        if retain:
            # We delete all previous messages for this topic with the retain flag set to True.
            # Only the last message with this flag is relevant.
            self.msg_to_send[:] = [m for m in self.msg_to_send if not (topic == m[0] and retain == m[2])]
        try:
            out = super().publish(topic, msg, retain, qos, False)
            if qos == 1:
                # We postpone the message in case it is not delivered to the server.
                # We will delete it when we receive a receipt.
                self.msg_to_confirm.setdefault(data, []).append(out)
            return out
        except (OSError, MQTTException) as e:
            self.conn_issue = (e, 2)
            # If the message cannot be sent, we put it in the queue to try to resend it.
            if self.NO_QUEUE_DUPS:
                if data in self.msg_to_send:
                    return
            if self.KEEP_QOS0 and qos == 0:
                self.add_msg_to_send(data)
            elif qos == 1:
                self.add_msg_to_send(data)

    def subscribe(self, topic, qos=0, resubscribe=True):
        """
        See documentation for `umqtt.MQTTClient.subscribe()`

        The function tries to subscribe to the topic. If it fails,
        the topic subscription goes into the subscription queue.

        Connection problems are captured and handled by `is_conn_issue()`

        """
        data = (topic, qos)

        if self.RESUBSCRIBE and resubscribe:
            if topic not in dict(self.subs):
                self.subs.append(data)

        # We delete all previous subscriptions for the same topic from the queue.
        # The most important is the last subscription.
        self.sub_to_send[:] = [s for s in self.sub_to_send if topic != s[0]]
        try:
            out = super().subscribe(topic, qos)
            self.sub_to_confirm.setdefault(data, []).append(out)
            return out
        except (OSError, MQTTException) as e:
            self.conn_issue = (e, 3)
            if self.NO_QUEUE_DUPS:
                if data in self.sub_to_send:
                    return
            self.sub_to_send.append(data)

    def send_queue(self):
        """
        The function tries to send all messages and subscribe to all topics that are in the queue to send.

        :return: True if the queue's empty.
        :rtype: bool
        """
        msg_to_del = []
        for data in self.msg_to_send:
            topic, msg, retain, qos = data
            try:
                out = super().publish(topic, msg, retain, qos, False)
                if qos == 1:
                    # We postpone the message in case it is not delivered to the server.
                    # We will delete it when we receive a receipt.
                    self.msg_to_confirm.setdefault(data, []).append(out)
                msg_to_del.append(data)
            except (OSError, MQTTException) as e:
                self.conn_issue = (e, 5)
                return False
        self.msg_to_send[:] = [m for m in self.msg_to_send if m not in msg_to_del]
        del msg_to_del

        sub_to_del = []
        for data in self.sub_to_send:
            topic, qos = data
            try:
                out = super().subscribe(topic, qos)
                self.sub_to_confirm.setdefault(data, []).append(out)
                sub_to_del.append(data)
            except (OSError, MQTTException) as e:
                self.conn_issue = (e, 5)
                return False
        self.sub_to_send[:] = [s for s in self.sub_to_send if s not in sub_to_del]

        return True

    def is_conn_issue(self):
        """
        With this function we can check if there is any connection problem.

        It is best to use this function with the reconnect() method to resume the connection when it is broken.

        You can also check the result of methods such as this:
        `connect()`, `publish()`, `subscribe()`, `reconnect()`, `send_queue()`, `disconnect()`, `ping()`, `wait_msg()`,
        `check_msg()`, `is_keepalive()`.

        The value of the last error is stored in self.conn_issue.

        :return: Connection problem
        :rtype: bool
        """
        self.is_keepalive()

        if self.conn_issue:
            self.log()
        return bool(self.conn_issue)

    def wait_msg(self):
        """
        See documentation for `umqtt.MQTTClient.wait_msg()`

        Connection problems are captured and handled by `is_conn_issue()`
        """
        self.is_keepalive()
        try:
            return super().wait_msg()
        except (OSError, MQTTException) as e:
            self.conn_issue = (e, 8)

    def check_msg(self):
        """
        See documentation for `umqtt.MQTTClient.check_msg()`

        Connection problems are captured and handled by `is_conn_issue()`
        """
        self.is_keepalive()
        try:
            return super().check_msg()
        except (OSError, MQTTException) as e:
            self.conn_issue = (e, 10)
