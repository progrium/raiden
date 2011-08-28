http_port = 8088
backend_port = 9989

def service():
    from raiden.gateways.httpstream import HttpStreamGateway
    from raiden.pubsub import MessagingBackend
    from gevent_tools.service import Service
    import gevent, random, json
    
    class HttpStreamer(Service):
        def __init__(self):
            self.backend = MessagingBackend()
            self.frontend = HttpStreamGateway(self.backend)
            
            self.add_service(self.backend)
            self.add_service(self.frontend)
        
        def do_start(self):
            print "Gateway listening on %s..." % self.frontend.port
            self.backend.cluster.add('127.0.0.1')
            self.spawn(self.message_publisher)
        
        def message_publisher(self):
            while True:
                self.backend.publish('localhost:8088/test', 
                    dict(foo='bar', baz=random.choice(['one', 'two', 'three'])))
                print self.backend.router.subscriber_counts
                gevent.sleep(2)
    
    return HttpStreamer()
