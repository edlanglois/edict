"""Pattern-string output protocol"""

from __future__ import annotations

from typing import Dict, TextIO

from ..types import RecordStream


def write_pattern(f: TextIO, data: RecordStream, args: Dict) -> None:
    pattern = args["pattern"]
    for record in data.records:
        f.write(pattern.format(**record))
        f.write("\n")
