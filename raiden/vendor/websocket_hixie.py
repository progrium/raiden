import re
import struct
from hashlib import md5
from socket import error

from gevent.pywsgi import WSGIHandler
from gevent.event import Event
from gevent.coros import Semaphore

# This class implements the Websocket protocol draft version as of May 23, 2010
# The version as of August 6, 2010 will be implementend once Firefox or
# Webkit-trunk support this version.

class WebSocketError(error):
    pass

class WebSocket(object):
    def __init__(self, sock, environ):
        self.rfile = sock.makefile('rb', -1)
        self.socket = sock
        self.origin = environ.get('HTTP_ORIGIN')
        self.protocol = environ.get('HTTP_SEC_WEBSOCKET_PROTOCOL', 'unknown')
        self.path = environ.get('PATH_INFO')
        self._writelock = Semaphore(1)
        self.finished = Event()

    def send(self, message):
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        elif isinstance(message, str):
            message = unicode(message).encode('utf-8')
        else:
            raise Exception("Invalid message encoding")

        with self._writelock:
            self.socket.sendall("\x00" + message + "\xFF")

    def detach(self):
        self.socket = None
        self.rfile = None
        self.handler = None

    def close(self):
        # TODO implement graceful close with 0xFF frame
        if self.socket is not None:
            try:
                self.socket.close()
            except Exception:
                pass
            self.detach()
        self.finished.set()


    def _message_length(self):
        # TODO: buildin security agains lengths greater than 2**31 or 2**32
        length = 0

        while True:
            byte_str = self.rfile.read(1)

            if not byte_str:
                return 0
            else:
                byte = ord(byte_str)

            if byte != 0x00:
                length = length * 128 + (byte & 0x7f)
                if (byte & 0x80) != 0x80:
                    break

        return length

    def _read_until(self):
        bytes = []

        while True:
            byte = self.rfile.read(1)
            if ord(byte) != 0xff:
                bytes.append(byte)
            else:
                break

        return ''.join(bytes)

    def receive(self):
        while self.socket is not None:
            frame_str = self.rfile.read(1)
            if not frame_str:
                # Connection lost?
                self.close()
                break
            else:
                frame_type = ord(frame_str)


            if (frame_type & 0x80) == 0x00: # most significant byte is not set
                if frame_type == 0x00:
                    bytes = self._read_until()
                    return bytes.decode("utf-8", "replace")
                else:
                    self.close()
            elif (frame_type & 0x80) == 0x80: # most significant byte is set
                # Read binary data (forward-compatibility)
                if frame_type != 0xff:
                    self.close()
                    break
                else:
                    length = self._message_length()
                    if length == 0:
                        self.close()
                        break
                    else:
                        self.rfile.read(length) # discard the bytes
            else:
                raise IOError("Reveiced an invalid message")

class WebSocketUpgradeMiddleware(object):
    """ Automatically upgrades the connection to websockets. """
    def __init__(self, handler):
        self.handler = handler

    def __call__(self, environ, start_response):
        self.socket = socket
        self.environ = environ
        self.websocket = WebSocket(socket, environ)

        headers = [
            ("Upgrade", "WebSocket"),
            ("Connection", "Upgrade"),
        ]

        # Detect the Websocket protocol
        if "HTTP_SEC_WEBSOCKET_KEY1" in environ:
            version = 76
        else:
            version = 75

        if version == 75:
            headers.extend([
                ("WebSocket-Origin", self.websocket.origin),
                ("WebSocket-Protocol", self.websocket.protocol),
                ("WebSocket-Location", "ws://%s%s" % (self.environ.get('HTTP_HOST'), self.websocket.path)),
            ])
            start_response("101 Web Socket Hixie Handshake", headers)
        elif version == 76:
            challenge = self._get_challenge()
            headers.extend([
                ("Sec-WebSocket-Origin", self.websocket.origin),
                ("Sec-WebSocket-Protocol", self.websocket.protocol),
                ("Sec-WebSocket-Location", "ws://%s%s" % (self.environ.get('HTTP_HOST'), self.websocket.path)),
            ])

            start_response("101 Web Socket Hixie Handshake", headers)
            self.socket.sendall(challenge)
        else:
            raise WebSocketError("WebSocket version not supported")

        self.handler(self.websocket)
        #self.websocket.finished.wait()


    def _get_key_value(self, key_value):
        key_number = int(re.sub("\\D", "", key_value))
        spaces = re.subn(" ", "", key_value)[1]

        if key_number % spaces != 0:
            raise WebSocketError("key_number %d is not an intergral multiple of"
                                 " spaces %d" % (key_number, spaces))

        return key_number / spaces

    def _get_challenge(self):
        key1 = self.environ.get('HTTP_SEC_WEBSOCKET_KEY1')
        key2 = self.environ.get('HTTP_SEC_WEBSOCKET_KEY2')

        if not key1:
            raise WebSocketError("SEC-WEBSOCKET-KEY1 header is missing")
        if not key2:
            raise WebSocketError("SEC-WEBSOCKET-KEY2 header is missing")

        part1 = self._get_key_value(self.environ['HTTP_SEC_WEBSOCKET_KEY1'])
        part2 = self._get_key_value(self.environ['HTTP_SEC_WEBSOCKET_KEY2'])

        # This request should have 8 bytes of data in the body
        key3 = self.environ.get('wsgi.input').rfile.read(8)

        return md5(struct.pack("!II", part1, part2) + key3).digest()

