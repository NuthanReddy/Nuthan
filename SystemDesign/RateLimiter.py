from time import time, sleep


class SlidingWindow:

    def __init__(self, capacity, time_unit, forward_callback, drop_callback):
        self.capacity = capacity
        self.time_unit = time_unit
        self.forward_callback = forward_callback
        self.drop_callback = drop_callback

        self.cur_time = time()
        self.pre_count = capacity
        self.cur_count = 0

    def handle(self, packet):

        if (time() - self.cur_time) > self.time_unit:
            self.cur_time = time()
            self.pre_count = self.cur_count
            self.cur_count = 0

        estimated_capacity = (self.pre_count * (self.time_unit - (time() - self.cur_time)) / self.time_unit) + self.cur_count

        if estimated_capacity > self.capacity:
            return self.drop_callback(packet)

        self.cur_count += 1
        return self.forward_callback(packet)


def forward(packet):
    print("Packet Forwarded: " + str(packet))


def drop(packet):
    print("Packet Dropped: " + str(packet))


throttle = SlidingWindow(5, 1, forward, drop)

packet = 0

while packet < 15:
    sleep(0.14)
    throttle.handle(packet)
    packet += 1