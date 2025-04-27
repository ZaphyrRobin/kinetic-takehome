import time


def retry(exceptions, tries: int = 4, delay: int = 3, backoff: int = 2, logger=None):
    """
    Retry calling the decorated function using an exponential backoff.
    Args:
        exceptions: The exception to check. may be a tuple of
            exceptions to check.
        tries: Number of times to try (not retry) before giving up.
        delay: Initial delay between retries in seconds.
        backoff: Backoff multiplier (e.g. value of 2 will double the delay
            each retry).
        logger: Logger to use. If None, print.
    """
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            new_tries, new_delay = tries, delay
            while new_tries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    msg = f"{e}, retrying in {new_delay} seconds..."
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(new_delay)
                    new_tries -= 1
                    new_delay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return deco_retry
