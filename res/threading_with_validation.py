from micropython_event_bus import Producer, subscribe

try:
    import utime as time
except ModuleNotFoundError:
    import time


def is_int_or_float(*args, **kwargs):
    for arg in args:
        if type(arg) == int or type(arg) == float:
            pass
        else:
            raise ValueError('arg is not a float or int')


message_bus = Producer(
    name="my message bus", as_threads=True, validation=is_int_or_float)


def simple_logger(func):
    def with_logger(*args, **kwargs):
        print('%s got a message!' % func.__name__)
        result = func(*args, **kwargs)
        print('%s has finished!' % func.__name__)
        return result
    return with_logger


@subscribe(message_bus)
@simple_logger
def handler_1(*args, **kwargs):
    time.sleep(3)


@subscribe(message_bus)
@simple_logger
def handler_2(*args, **kwargs):
    time.sleep(2)


message_bus(123, some="me")
