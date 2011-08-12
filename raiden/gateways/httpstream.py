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
        self.backend.cluster.add('127.0.0.1')
        self.backend.subscribe('test', self.subscription)
        self.spawn_later(1, self.pub)
        self.spawn_later(3, self.pub)
    
    def pub(self):
        self.backend.publish('test', 'message1')
        self.backend.publish('test', 'message2')
        self.backend.publish('test2', 'message3 not really')
    
    def app(self, env, start_response):
        write = start_response('200 OK', [('Content-Type', 'text/html')])
        for msgs in self.subscription:
            msgs.append('')
            write('\n'.join(msgs))
        return []
    
class Streamer(object):
    def __init__(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/html')])
    
    def __iter__(self):
        return self
    
    def next(self):
        gevent.sleep(2)
        return "hello\n"