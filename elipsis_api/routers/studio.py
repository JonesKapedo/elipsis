"""Studio routes restored with theme support (embedded source)."""
from __future__ import annotations

import base64
import gzip
import pathlib

_PAYLOAD = open(pathlib.Path(__file__).with_name('studio.py.gz.b64')).read()
_source = gzip.decompress(base64.b64decode(_PAYLOAD)).decode('utf-8')
exec(compile(_source, str(pathlib.Path(__file__).resolve()), 'exec'), globals())
