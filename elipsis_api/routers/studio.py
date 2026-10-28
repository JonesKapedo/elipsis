"""Studio routes — load gzipped source from part files."""
from __future__ import annotations

import base64
import gzip
import pathlib

_dir = pathlib.Path(__file__).resolve().parent
_parts = []
for i in range(4):
    _parts.append((_dir / f"studio_part_{i}.b64").read_text().strip())
_PAYLOAD = "".join(_parts)
_source = gzip.decompress(base64.b64decode(_PAYLOAD)).decode("utf-8")
exec(compile(_source, str(pathlib.Path(__file__).resolve()), "exec"), globals())
