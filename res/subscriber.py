from .producer import Producer


def subscribe(producer: Producer):
    """
    Decorater that connects a handler function to a producer.

    Example::

        producer = Producer()

        @subscribe(producer)
        def simple_sub(*args, **kwargs):
            print('got', *args)

        producer('some slick string')

    """
    def connected_subscriber(handler_func):
        producer.subscribe(handler_func)
        return handler_func
    return connected_subscriber
