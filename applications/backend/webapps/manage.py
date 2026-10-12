#!/usr/bin/env python
import multiprocessing
import os
import sys

if __name__ == "__main__":
    # Django 5.2 does not support Python 3.14's default 'forkserver' multiprocessing start method.
    # (https://code.djangoproject.com/ticket/36531)
    # Set to the older 'fork' method. This line may be removed after Django is >=6.0.
    multiprocessing.set_start_method("fork", force=True)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapps.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django

            # To get rid of the flake8-error "./manage.py:14:13: F401 'django' imported but unused"
            assert django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)
