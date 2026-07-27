import threading
import weakref
from collections import defaultdict


class Observer:
    def update(self, event_type, event_data):
        raise NotImplementedError


class EventBus:
    def __init__(self):
        # Map event_type → list of weak references to observers
        self._observers = defaultdict(list)

    def subscribe(self, event_type, observer: Observer):
        self._observers[event_type].append(weakref.ref(observer))

    def publish(self, event_type, event_data):
        # Notify in parallel threads for scalability
        threads = []
        for ref in self._observers[event_type]:
            obs = ref()
            if obs:
                t = threading.Thread(target=obs.update, args=(event_type, event_data))
                t.start()
                threads.append(t)
        for t in threads:
            t.join()


# Example Observers
class LoggingObserver(Observer):
    def update(self, event_type, event_data):
        print(f"[LOG] {event_type}: {event_data}")


class MetricsObserver(Observer):
    def update(self, event_type, event_data):
        print(f"[METRIC] {event_type} processed")


# Usage
bus = EventBus()
bus.subscribe("file_upload", LoggingObserver())
bus.subscribe("file_upload", MetricsObserver())

bus.publish("file_upload", {"filename": "data.csv"})
