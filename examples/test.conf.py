backend_port = 9989

def service():
    from gevent_tools.service import Service
    from raiden.pubsub import MessagingBackend
    
    class MyService(Service):
        def __init__(self):
            self.backend = MessagingBackend()
            self.add_service(self.backend)
        
        def do_start(self):
            print "adding self to cluster"
            self.backend.cluster.add('127.0.0.1')
            self.backend.subscribe('test', self.sub)
            self.spawn_later(1, self.pub)
        
        def pub(self):
            print "pubing twice"
            self.backend.publish('test', 'message')
            self.backend.publish('test', 'message')
            self.backend.publish('test2', 'message')
        
        def sub(self, messages):
            for message in messages:
                print message
    
    return MyService()