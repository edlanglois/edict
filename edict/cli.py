"""Edict command-line interface"""
from __future__ import annotations

import argparse
import contextlib
import pathlib
import sys
from typing import Generator, Optional, TextIO

from edict import __version__, load
from edict.protocols import READERS, WRITERS


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: A list of argument strings to use instead of sys.argv.

    Returns:
        An `argparse.Namespace` object containing the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None,
    )
    parser.add_argument(
        "-i",
        "--input-file",
        type=pathlib.Path,
        help="Read records from this file (default: STDIN)",
    )
    parser.add_argument(
        "-r",
        "--input-format",
        type=str,
        choices=READERS,
        default="csv",
        help="Input format to read (default: csv)",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=pathlib.Path,
        help="Write records to this file (default: STDOUT)",
    )
    parser.add_argument(
        "-w",
        "--output-format",
        type=str,
        choices=WRITERS,
        default="csv",
        help="Output format to write (default: csv)",
    )
    parser.add_argument("edict_file", type=pathlib.Path, nargs="*", help="Edict file")
    parser.add_argument("-v", "--version", action="version", version=__version__)

    return parser.parse_args(argv)


@contextlib.contextmanager
def open_(
    filename: Optional[pathlib.Path], mode="r", **kwargs
) -> Generator[TextIO, None, None]:
    if filename is None:
        if mode == "r":
            f = sys.stdin
        elif mode == "w":
            f = sys.stdout
        else:
            raise ValueError(f"No standard IO for mode {mode}")
        yield f
    else:
        with open(filename, mode=mode, **kwargs) as f:  # type: ignore
            yield f


def main(argv=None):
    """Run script.

    Args:
        argv: A list of argument strings to use instead of sys.argv.
    """
    args = parse_args(argv)
    transformers = [load(f) for f in args.edict_file]
    read = READERS[args.input_format]
    write = WRITERS[args.output_format]
    # CSV files somtimes (rarely) contain a byte order mark as the first character
    # Apparently Excel does this when exporting to CSV.
    # Encoding 'utf-8-sig' ignores this mark if it exists.
    with open_(args.input_file, "r", encoding="utf-8-sig") as fin:
        with open_(args.output_file, "w") as fout:
            data = read(fin)
            for transformer in transformers:
                data = transformer.transform(data)
            write(fout, data)
