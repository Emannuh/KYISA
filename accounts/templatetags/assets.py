"""
{% asset 'css/portal.css' %} -> static URL that changes whenever the file changes.

Production uses CompressedManifestStaticFilesStorage, which already puts a
content hash in the filename, so the URL is returned unchanged there.

In development (DEBUG) static files are served without a hash and without
Cache-Control, so browsers keep re-using stale CSS/JS. Appending the file's
modification time (?v=…) makes the browser fetch the new file after each edit.
"""
import os

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def asset(path):
    url = static(path)
    if not settings.DEBUG:
        return url
    found = finders.find(path)
    if not found:
        return url
    version = int(os.path.getmtime(found))
    return f"{url}{'&' if '?' in url else '?'}v={version}"
