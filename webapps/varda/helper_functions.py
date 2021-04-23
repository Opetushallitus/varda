import re


def hide_hetu(string, hide_date=True):
    hetu_regex = re.compile('(\\d{6})([A+\\-]\\d{3}[0-9A-FHJ-NPR-Y])')
    replace_regex = r'DDMMYY\2' if hide_date else r'\1XXXXX'
    if string:
        if not isinstance(string, str):
            string = str(string)
        if re.search(hetu_regex, string):
            return re.sub(hetu_regex, replace_regex, string)
    return string
