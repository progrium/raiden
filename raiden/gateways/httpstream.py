import errno
import socket

import gevent.pywsgi
import gevent.queue

from gevent_tools.config import Option
from gevent_tools.service import Service

from raiden.pubsub import MessagingBackend

class _WSGIServer(gevent.pywsgi.WSGIServer):
    """
    Custom WSGI container that is made to work with HttpStreamGateway, but more
    importantly catches disconnects and passes the event as `handle_disconnect`
    on the gateway. The only weird thing is that we modify the protocol of WSGI
    in that the application's first yield (or first element of returned list,
    but we're streaming, so we use yield) will be some kind of object that will
    be passed to the disconnect handler to identify the request.
    """
    
    class handler_class(gevent.pywsgi.WSGIHandler):
        def process_result(self):
            request_key = self.result.next()
            try:
                super(self.__class__, self).process_result()
            except socket.error, ex:
                # Broken pipe, connection reset by peer
                if ex[0] in (errno.EPIPE, errno.ECONNRESET):
                    self.server.gateway.handle_disconnect(self.socket, request_key)
                else:
                    raise
    
    def __init__(self, gateway):
        self.gateway = gateway
        super(_WSGIServer, self).__init__(
            listener=('127.0.0.1', gateway.port),
            application=gateway.handle_stream,
            spawn=gateway.spawn,
            log=None)

class HttpStreamGateway(Service):
    port = Option('http_port')
    
    def __init__(self):
        self.wsgi_server = _WSGIServer(self)
        self.backend = MessagingBackend()
        
        self.add_service(self.backend)
        self.add_service(self.wsgi_server)
        
        # This is to catch errno.ECONNRESET error created
        # by WSGIServer when it tries to read after writing
        # to a broken pipe, which is already caught and used 
        # for handling disconnects.
        self.catch(IOError, lambda e,g: None)
    
    def do_start(self):
        print "Gateway listening on %s..." % self.port
        self.backend.cluster.add('127.0.0.1')
        self.pub()
    
    def pub(self):
        self.backend.publish('test', 'hello')
        print self.backend.router.subscriber_counts
        self.spawn_later(3, self.pub)
    
    def handle_disconnect(self, socket, request_key):
        self.backend.unsubscribe(request_key.channel, request_key)
    
    def handle_stream(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/html')])
        subscription = gevent.queue.Queue() # needs max size? 
        subscription.channel = 'test'
        yield subscription
        self.backend.subscribe(subscription.channel, subscription)
        for msgs in subscription:
            print "Writing %s messages" % len(msgs)
            yield '%s\n' % '\n'.join(msgs)