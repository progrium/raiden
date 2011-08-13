import json
import errno
import socket

import gevent.pywsgi
import gevent.queue
import webob

from gevent_tools.config import Option
from gevent_tools.service import Service

from raiden.pubsub import MessagingBackend
from raiden.pubsub import Subscription

class HttpStreamGateway(Service):
    port = Option('http_port')
    
    def __init__(self, backend):
        self.backend = backend
        self.wsgi_server = _WSGIServer(self)
        
        self.add_service(self.wsgi_server)
        
        # This is to catch errno.ECONNRESET error created
        # by WSGIServer when it tries to read after writing
        # to a broken pipe, which is already caught and used 
        # for handling disconnects.
        self.catch(IOError, lambda e,g: None)
    
    def handle(self, env, start_response):
        if env['REQUEST_METHOD'] == 'POST':
            return self.handle_publish(env, start_response)
        elif env['REQUEST_METHOD'] == 'GET':
            return self.handle_stream(env, start_response)
        else:
            start_response('405 Method not allowed', [])
            return ["Method not allowed\n"]
    
    def handle_publish(self, env, start_response):
        request = webob.Request(env)
        self.backend.publish(
            '%s%s' % (request.host, request.path), dict(request.POST))
        start_response('200 OK', [
            ('Content-Type', 'text/plain')])
        return ["OK\n"]
    
    def handle_stream(self, env, start_response):
        request = webob.Request(env)
        filters = request.str_GET.items()
        subscription = self.backend.subscribe(
            '%s%s' % (request.host, request.path), filters=filters)
        yield subscription # send to container to include on disconnect
        
        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Connection', 'keep-alive'),
            ('Cache-Control', 'no-cache, must-revalidate'),
            ('Expires', 'Tue, 11 Sep 1985 19:00:00 GMT'),])
        for msgs in subscription:
            if msgs is None:
                yield '\n'
            else:
                yield '%s\n' % '\n'.join(msgs)
    
    def handle_disconnect(self, socket, subscription):
        subscription.cancel()

class _WSGIServer(gevent.pywsgi.WSGIServer):
    """
    Custom WSGI container that is made to work with HttpStreamGateway, but more
    importantly catches disconnects and passes the event as `handle_disconnect`
    to the gateway. The only weird thing is that we modify the protocol of WSGI
    in that the application's first yield (or first element of returned list,
    but we're streaming, so we use yield) will be some kind of object that will
    be passed to the disconnect handler to identify the request.
    """
    
    class handler_class(gevent.pywsgi.WSGIHandler):
        def process_result(self):
            if hasattr(self.result, 'next'):
                request_obj = self.result.next()
                try:
                    super(self.__class__, self).process_result()
                except socket.error, ex:
                    # Broken pipe, connection reset by peer
                    if ex[0] in (errno.EPIPE, errno.ECONNRESET):
                        if hasattr(self.server.gateway, 'handle_disconnect'):
                            self.server.gateway.handle_disconnect(self.socket, request_obj)
                    else:
                        raise
            else:
                super(self.__class__, self).process_result()
    
    def __init__(self, gateway):
        self.gateway = gateway
        super(_WSGIServer, self).__init__(
            listener=('127.0.0.1', gateway.port),
            application=gateway.handle,
            spawn=gateway.spawn,
            log=None)