"""
This example is from: https://github.com/celery/celery/tree/master/examples/django/
"""

import django
import os
import sys
import threading

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapps.settings')
django.setup()

from varda.tasks import add  # noqa


def check_celery():
    res = add.delay(2, 3)
    value = res.get()

    if value == 5:
        print("Celery is running OK.")
    else:
        print("Error: Celery is not running.")
        os._exit(55)  # Should never come here. Due to threading cannot use sys.exit().


def main(argv):
    t = threading.Thread(name='check_celery', target=check_celery)

    t.setDaemon(True)
    t.start()

    t.join(3)
    if t.isAlive():
        print("Error: Celery is not running.")
        return sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
