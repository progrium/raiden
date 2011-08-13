import collections
import time
import json

import msgpack
import gevent.queue
from gevent_zeromq import zmq

from gevent_tools.config import Option
from gevent_tools.service import Service
from gevent_tools.service import require_ready

context = zmq.Context()

class MessagingException(Exception): pass

class Subscription(gevent.queue.Queue):
    keepalive_secs = Option('keepalive', default=30)
    
    def __init__(self, router, channel, filters=None):
        super(Subscription, self).__init__(maxsize=64)
        self.channel = channel
        self.router = router
        self.filters = filters
        router.subscribe(channel, self)
        router.spawn(self._keepalive)
    
    def _keepalive(self):
        while self.router:
            self.put(None)
            gevent.sleep(self.keepalive_secs)
    
    def cancel(self):
        self.router.unsubscribe(self.channel, self)
        self.router = None
    
    def put(self, messages):
        if messages is not None: 
            # Perform any filtering
            if self.filters and len(messages):
                def _filter(message):
                    # Make sure all keys in filter are in message
                    required_keys = set([k for k,v in self.filters])
                    if not required_keys.issubset(message.keys()): 
                        return False
                    # OR across filters with same key, AND across keys
                    matches = []
                    for key in message:
                        values = [v for k,v in self.filters if k == key]
                        if len(values):
                            matches.append(message[key] in values)
                    return all(matches)
                messages = filter(_filter, messages)
                if not len(messages): return
            # Serialize to JSON strings
            messages = map(json.dumps, messages)
        super(Subscription, self).put(messages)
    
    def __del__(self):
        if self.router:
            self.cancel()
        

class Observable(object):
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

    def notify(self, *args, **kwargs):
        for observer in self._observers:
            if hasattr(observer, '__call__'):
                observer(*args, **kwargs)
            else:
                observer.update(*args, **kawrgs)

class ClusterRoster(Observable):
    def __init__(self):
        super(ClusterRoster, self).__init__()
        self._roster = set()
    
    def add(self, host):
        self._roster.add(host)
        self.notify(add=host)
    
    def remove(self, host):
        self._roster.discard(host)
        self.notify(remove=host)
    
    def __iter__(self):
        return self._roster.__iter__()
    

class MessagingBackend(Service):
    port = Option('backend_port')
    
    def __init__(self):
        self.cluster = ClusterRoster()
        self.publisher = MessagePublisher(self.cluster, self.port)
        self.router = MessageRouter('tcp://127.0.0.1:%s' % self.port)
        
        self.add_service(self.publisher)
        self.add_service(self.router)
    
    def publish(self, channel, message):
        self.publisher.publish(channel, message)
    
    def subscribe(self, channel, filters=None):
        return Subscription(self.router, channel, filters)

class MessagePublisher(Service):
    # TODO: batching socket sends based on publish frequency
    
    def __init__(self, cluster, port):
        self.cluster = cluster
        self.port = port
        self.socket = context.socket(zmq.PUB)
    
    def do_start(self):
        for host in self.cluster:
            self.connect(host)
        def connector(add=None, remove=None):
            if add: self.connect(add)
        self.cluster.attach(connector)
    
    def connect(self, host):
        self.socket.connect('tcp://%s:%s' % (host, self.port))
    
    @require_ready
    def publish(self, channel, message):
        self.socket.send_multipart([channel.lower(), msgpack.packb(message)])

class MessageRouter(Service):
    max_channels = Option('max_channels', default=65536)
    max_subscribers = Option('max_subscribers', default=65536)
    
    def __init__(self, address):
        self.address = address
        self.socket = context.socket(zmq.SUB)
        
        self.channels = dict()
        self.subscriber_counts = collections.Counter()
    
    def do_start(self):
        self.socket.bind(self.address)
        self.spawn(self._listen)
    
    def subscribe(self, channel, subscriber):
        channel = channel.lower()
        
        # Initialize channel if necessary
        if not self.channels.get(channel):
            if len(self.channels) >= self.max_channels:
                raise MessagingException(
                        "Unable to init channel. Max channels reached: %s" % 
                            self.max_channels)
            self.channels[channel] = ChannelDispatcher(self)
        
        # Create subscription unless max reached
        if sum(self.subscriber_counts.values()) >= self.max_subscribers:
            raise MessagingException(
                    "Unable to subscribe. Max subscribers reached: %s" % 
                        self.max_subscribers)
        self.socket.setsockopt(zmq.SUBSCRIBE, channel)
        self.subscriber_counts[channel] += 1
        self.channels[channel].add(subscriber)
    
    def unsubscribe(self, channel, subscriber):
        channel = channel.lower()
        
        self.socket.setsockopt(zmq.UNSUBSCRIBE, channel)
        self.subscriber_counts[channel] -= 1
        self.channels[channel].remove(subscriber)
        
        # Clean up counts and ChannelDispatchers with no subscribers
        self.subscriber_counts += collections.Counter()
        if not self.subscriber_counts[channel]:
            del self.channels[channel]
    
    def _listen(self):
        while True:
            channel, message = self.socket.recv_multipart()
            if self.subscriber_counts[channel]:
                self.channels[channel].send(msgpack.unpackb(message))

class ChannelDispatcher(object):
    def __init__(self, router):
        self.router = router
        self.purge()
    
    def purge(self):
        self.buffer = []
        self.subscribers = set()
        self.draining = False
    
    def send(self, message):
        self.buffer.append(message)
        self.drain()
    
    def add(self, subscriber):
        self.subscribers.add(subscriber)
    
    def remove(self, subscriber):
        self.subscribers.remove(subscriber)
        if not len(self.subscribers):
            self.purge()
    
    def drain(self):
        """
        Unless already draining, this creates a greenlet that will flush the 
        buffer to subscribers then delay the next flush depending on how many 
        subscribers there are. This continues until the buffer remains empty.
        It will start again with the next call to send(). Since the buffer is 
        flushed to a subscriber and a subscriber is ultimately an open socket, 
        this helps reduce the number of socket operations when there are a 
        large number of open sockets.
        """
        if self.draining:
            return
        def _drain():
            self.draining = True
            while self.draining and self.buffer:
                start_time = time.time()
                batch = self.buffer[:]
                if batch:
                    del self.buffer[:]
                    for subscriber in self.subscribers:
                        if hasattr(subscriber, 'put'):
                            subscriber.put(batch)
                        else:
                            subscriber(batch)
                delta_time = time.time() - start_time
                interval = self._batch_interval()
                if delta_time > interval:
                    gevent.sleep(0.0) # yield
                else:
                    gevent.sleep(interval - delta_time)
            self.draining = False
        self.router.spawn(_drain)
    
    def _batch_interval(self):
        if len(self.subscribers) <= 10:
            return 0.0
        elif len(self.subscribers) <= 100:
            return 0.25
        elif len(self.subscribers) <= 1000:
            return 0.5
        else:
            return 1.0