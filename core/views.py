import logging
from django.shortcuts import render

logger = logging.getLogger(__name__)


def bad_request(request, exception=None):
    """ Custom 400 handler. """
    logger.warning("400 Bad Request at %s: %s", request.path, exception)
    return render(request, '400.html', {'error_message': str(exception) if exception else None}, status=400)


def permission_denied(request, exception=None):
    """ Custom 403 handler. """
    logger.warning("403 Forbidden at %s: %s", request.path, exception)
    return render(request, '403.html', {'error_message': str(exception) if exception else None}, status=403)


def page_not_found(request, exception=None):
    """ Custom 404 handler. """
    return render(request, '404.html', {'path': request.path}, status=404)


def server_error(request):
    """ Custom 500 handler. """
    logger.error("500 Internal Server Error at %s", request.path)
    return render(request, '500.html', status=500)
