http_port = 8088
backend_port = 9989

def service():
    from raiden.gateways.httpstream import HttpStreamGateway
    from raiden.gateways.websocket import WebSocketGateway
    from raiden.pubsub import MessagingBackend
    from gevent_tools.service import Service
    import gevent, random, json
    
    class HttpStreamer(Service):
        def __init__(self):
            self.backend = MessagingBackend()
            self.http_frontend = HttpStreamGateway(self.backend)
            self.ws_frontend = WebSocketGateway(self.backend, attach_to=self.http_frontend.wsgi_server)
            
            self.add_service(self.backend)
            self.add_service(self.http_frontend)
            self.add_service(self.ws_frontend)
        
        def do_start(self):
            print "Gateway listening on %s..." % self.http_frontend.port
            self.backend.cluster.add('127.0.0.1')
            self.spawn(self.message_publisher)
        
        def message_publisher(self):
            while True:
                self.backend.publish('localhost:%s/test' % self.http_frontend.port, 
                    dict(foo='bar', baz=random.choice(['one', 'two', 'three'])))
                print self.backend.router.subscriber_counts
                gevent.sleep(2)
    
    return HttpStreamer()
