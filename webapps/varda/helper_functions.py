import re

from varda.constants import HETU_REGEX


def hide_hetu(string, hide_date=True):
    replace_regex = r'DDMMYY\2' if hide_date else r'\1XXXXX'
    if string:
        if not isinstance(string, str):
            string = str(string)
        if re.search(HETU_REGEX, string):
            return re.sub(HETU_REGEX, replace_regex, string)
    return string
