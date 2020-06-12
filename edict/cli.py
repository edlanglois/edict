"""Edict command-line interface"""
from __future__ import annotations

import argparse
import contextlib
import pathlib
import sys
from typing import Generator, Optional, TextIO

from edict import Edict


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: A list of argument strings to use instead of sys.argv.

    Returns:
        An `argparse.Namespace` object containing the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("edict_file", type=pathlib.Path, help="Edict file to parse.")
    parser.add_argument(
        "input_file",
        nargs="?",
        type=pathlib.Path,
        help="Read data from this file instead of STDIN.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=pathlib.Path,
        help="Output to this file instead of STDOUT.",
    )
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
    transformer = Edict.load(args.edict_file)
    with open_(args.input_file, "r") as fin:
        with open_(args.output_file, "w") as fout:
            transformer.apply(fin, fout)
