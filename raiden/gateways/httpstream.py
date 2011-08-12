import gevent.pywsgi
import gevent.queue

from gevent_tools.config import Option
from gevent_tools.service import Service

from raiden.pubsub import MessagingBackend

class HttpStreamGateway(Service):
    port = Option('http_port')
    
    def __init__(self):
        self.wsgi_server = gevent.pywsgi.WSGIServer(('127.0.0.1', self.port), self.app)
        self.backend = MessagingBackend()
        self.subscription = gevent.queue.Queue()
        self.add_service(self.backend)
        self.add_service(self.wsgi_server)
    
    def do_start(self):
        print "Gateway listening on %s..." % self.port
        self.backend.cluster.add('127.0.0.1')
        self.backend.subscribe('test', self.subscription)
        self.pub()
    
    def pub(self):
        self.backend.publish('test', 'hello')
        self.spawn_later(3, self.pub)
    
    def app(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/html')])
        for msgs in self.subscription:
            print "Writing %s messages" % len(msgs)
            yield '\n'.join(msgs)
            yield '\n'
    
class Streamer(object):
    def __init__(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/html')])
    
    def __iter__(self):
        return self
    
    def next(self):
        gevent.sleep(2)
        return "hello\n"