from functools import wraps


def is_local_url_decorator(original_function):
    """
    Decorator that is used to override django_cas_ng.views.is_local_url. next-parameter can be used to redirect user to
    a third party website when three or more forward slashes are used (e.g. ?next=///google.com), so we need to check
    that it is not the case.
    :param original_function: django_cas_ng.views.is_local_url
    :return: decorator function
    """
    @wraps(original_function)
    def is_local_url_wrapper(*args, **kwargs):
        url = args[1]
        if url.startswith('///'):
            return False
        return original_function(*args, **kwargs)
    return is_local_url_wrapper
