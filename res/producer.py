try:
    import _thread
except ModuleNotFoundError:
    _thread = None


class Producer:
    """
    Uses a list instead of a set to ensure correct ordering of subscriptions.
    Does not allow lambda functions to be used.

    :params name: name of producer
    :params validation: a function which will accept arguments passed into emit and check values / types raising a ValueError if incorrect type
    :params as_threads: option to run handlers as threads
    :raises NotImplementedError if micro-python version does not implement _thread and as_threads keyword set to True.
    """

    def __init__(self, *args, name=None, validation=None, as_threads=False):
        if as_threads and not _thread:
            raise NotImplementedError(
                'threading is not available in this distribution')

        self.__handlers = []
        self.__name = name
        self.__validation = validation
        self.__as_threads = as_threads

    # private methods

    def _add_handler(self, handler_func):
        if handler_func in self.__handlers:
            raise ValueError('handler is already subscribed.')
        self.__handlers.append(handler_func)
        return self

    def _remove_handler(self, handler_func):
        if not handler_func in self.__handlers:
            raise ValueError('handler is not subscribed to producer')
        self.__handlers.remove(handler_func)
        return self

    # public methods

    def subscribe(self, handler_func):
        """
        Subscribe a function as a callback to the producer.
        :params handler_func: a callback function that will be invoked 
        when a value is sent to the emit method. Function cannot be a lambda.
        :raises ValueError if handler is a lambda or already subscribed.
        """
        print(handler_func)
        """
        if handler_func.__name__ == '<lambda>':
            raise ValueError('handler cannot be a lambda function')
        """
        return self._add_handler(handler_func)

    def unsubscribe(self, handler_func):
        """
        Unsubscribe a callback from the producer.
        :raises ValueError if handler is not already subscribed.
        """
        return self._remove_handler(handler_func)

    def emit(self, *args, **kwargs):
        """
        Send arguments and keyword arguments to subscribed functions.
        Arguments are first passed through the validation function and then
        passed sequentially to each subscribed callback.
        If as_threads is set to True callbacks are started as separate threads.
        """
        if self.__validation:
            self.__validation(*args, **kwargs)
        for handler in self.__handlers:
            if self.__as_threads and _thread:
                _thread.start_new_thread(handler, args, kwargs)
            else:
                handler(*args, **kwargs)

    # datamodel methods

    def __repr__(self):
        return "Producer(%s)" % self.__name

    def __len__(self):
        return len(self.__handlers)

    __call__ = emit
    __iadd__ = subscribe
    __isub__ = unsubscribe
