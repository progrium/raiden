import json

import gevent.pywsgi
from gevent_tools.config import Option
from gevent_tools.service import Service
from ws4py.server.wsgi.middleware import WebSocketUpgradeMiddleware as HybiUpgrader

import raiden.patched
from raiden.vendor.websocket_hixie import WebSocketUpgradeMiddleware as HixieUpgrader
from raiden.vendor.websocket_hixie import WebSocketError
    
class WebSocketGateway(Service):
    port = Option('websocket_port', default=8080)
    path = Option('websocket_path', default='/-/websocket')
    
    def __init__(self, backend, attach_to=None):
        self.backend = backend
        
        if attach_to is None:
            self.server = gevent.pywsgi.WSGIServer(('127.0.0.1', self.port), 
                            application=WebSocketMiddleware(self.path, self.handle),
                            handler_class=raiden.patched.WSGIHandler)
            self.add_service(self.server)
        else:
            self.server = attach_to
            self.server.application = WebSocketMiddleware(self.path, 
                                        self.handle, self.server.application)
    
    def handle(self, websocket, environ):
        while not websocket.terminated:
            ctl_message = websocket.receive()
            if ctl_message is not None:
                try:
                    ctl_message = json.loads(ctl_message)
                except ValueError:
                    continue # TODO: log error
                if 'cmd' in ctl_message:
                    cmd = ctl_message.pop('cmd')
                    self.spawn(getattr(self, 'handle_%s' % cmd), websocket, **ctl_message)
    
    def handle_subscribe(self, websocket, channel, filters=None):
        subscription = self.backend.subscribe(channel, filters)
        for msgs in subscription:
            if msgs is None:
                websocket.send('\n')
            else:
                websocket.send('%s\n' % '\n'.join(msgs))
        

class WebSocketMiddleware(object):
    def __init__(self, path, handler, fallback_app=None):
        self.path = path
        self.handler = handler
        self.fallback_app = fallback_app or self.default_fallback
        self.upgrader = HybiUpgrader(self.handler, HixieUpgrader(self.handler)) 
    
    def __call__(self, environ, start_response):
        if environ.get('PATH_INFO') == self.path:
            try:
                return self.upgrader(environ, start_response)
            except WebSocketError, e:
                return self.fallback_app(environ, start_response)
        else:
            return self.fallback_app(environ, start_response)

    def default_fallback(self, environ, start_response):
        start_response("404 Not Found", [])
        return ["Not Found"]