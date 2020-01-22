from log_request_id import local


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        local.request_id = request.META.get('HTTP_X_REQUEST_ID', '')
        local.request_host = request.META.get('HTTP_HOST', '')
        response = self.get_response(request)
        return response
