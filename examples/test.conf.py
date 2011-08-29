http_port = 8088
backend_port = 9989

def service():
    from gevent_tools.service import Service
    from raiden.pubsub import MessagingBackend
    from raiden.gateways.httpstream import HttpStreamGateway
    from raiden.gateways.websocket import WebSocketGateway
    
    class MyService(Service):
        def __init__(self):
            self.backend = MessagingBackend()
            self.frontend = HttpStreamGateway(self.backend)
            
            self.add_service(self.backend)
            self.add_service(self.frontend)
            
            self.gateway = WebSocketGateway(attach_to=self.frontend.wsgi_server)
            self.add_service(self.gateway)
        
        def do_start(self):
            pass
    
    return MyService()