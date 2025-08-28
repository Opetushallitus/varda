from rest_framework import status
from rest_framework.renderers import BrowsableAPIRenderer


class ShowFiltersBrowsableAPIRenderer(BrowsableAPIRenderer):
    """
    Override for BrowsableAPIRenderer that always shows filter-form, even if response has not been a list
    (error, empty response...). However, if response status code is not in allowed list, use default handling
    to mitigate potential errors.
    """
    def get_filter_form_with_status(self, data, view, request, status_code):
        if (status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_204_NO_CONTENT,
                                status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND,)):
            return super().get_filter_form(data, view, request)
        # Pass data as a list to always show filter-form
        return super().get_filter_form([], view, request)

    def get_context(self, data, accepted_media_type, renderer_context):
        context = super().get_context(data, accepted_media_type, renderer_context)

        view = renderer_context['view']
        request = renderer_context['request']
        response = renderer_context['response']

        context['filter_form'] = self.get_filter_form_with_status(data, view, request, response.status_code)

        return context
