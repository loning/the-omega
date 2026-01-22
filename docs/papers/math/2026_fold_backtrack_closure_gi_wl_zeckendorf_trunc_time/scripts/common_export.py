#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export helper: copy run artifacts into paper root with stable filenames."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def copy_atomic(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_file():
        try:
            if src.read_bytes() == dst.read_bytes():
                return
        except Exception:
            pass

    fd, tmp = tempfile.mkstemp(prefix=dst.name + ".", dir=str(dst.parent))
    try:
        os.close(fd)
        shutil.copyfile(src, tmp)
        os.replace(tmp, dst)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

