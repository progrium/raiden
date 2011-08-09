
from gevent_zeromq import zmq

from gevent_tools.config import Option
from gevent_tools.service import Service

context = zmq.Context()

class Observable:
    # TODO: move to a util module
    
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        if not observer in self._observers:
            self._observers.append(observer)

    def detach(self, observer):
        try:
            self._observers.remove(observer)
        except ValueError:
            pass

    def notify(self, *args, **kawrgs):
        for observer in self._observers:
            observer.update(*args, **kawrgs)

class ClusterRoster(Observable):
    def __init__(self):
        self._roster = set()
    
    def add(self, host):
        self._roster.add(host)
        self.notify(add=host)
    
    def remove(self, host):
        self._roster.discard(host)
        self.notify(remove=host)
    

class MessagingBackend(Service):
    port = Option('backend_port')
    
    def __init__(self):
        self.cluster = ClusterRoster()
        self.publisher = MessagePublisher('tcp://127.0.0.1:%s' % self.port)
        self.subscriber = MessageSubscriber()
        
        self.add_service(self.publisher)
        self.add_service(self.subscriber)

class MessagePublisher(Service):
    def __init__(self, address):
        self.address = address
        self.socket = context.socket(zmq.PUB)
    
    def do_start(self):
        self.socket.bind(self.address)
    
    def publish(self, message):
        self.socket.send(message)

class MessageSubscriber(Service):
    def __init__(self):
        self.socket = context.socket(zmq.SUB)
    
    def do_start(self):
        pass