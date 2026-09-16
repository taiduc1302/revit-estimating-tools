# -*- coding: utf-8 -*-
"""SHA-256 helpers used for traceable snapshot evidence."""
from __future__ import absolute_import, print_function

import hashlib

from .utils import to_text


def sha256_text(value):
    return hashlib.sha256(to_text(value).encode("utf-8")).hexdigest()


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
