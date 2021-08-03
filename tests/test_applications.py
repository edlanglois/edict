import io
import json
import pathlib
from typing import Dict, NamedTuple

import pytest

import edict

files_dir = pathlib.Path(__file__).parent / "files"
edict_files = files_dir.glob("*.edt")


class Application(NamedTuple):
    name: str
    in_file: pathlib.Path
    out_file: pathlib.Path
    edict_file: pathlib.Path
    read_protocol: str
    write_protocol: str
    protocol_args: Dict


PROTOCOLS = {".csv": "csv", ".journal": "hledger", ".pattern": "pattern"}

applications = []
for edict_file in edict_files:
    name = edict_file.stem
    (in_file,) = files_dir.glob(name + ".in.*")
    (out_file,) = files_dir.glob(name + ".out.*")
    try:
        f = open(files_dir / (name + ".args.json"))
    except FileNotFoundError:
        protocol_args = {}
    else:
        protocol_args = json.load(f)

    applications.append(
        Application(
            name=name,
            in_file=in_file,
            out_file=out_file,
            edict_file=edict_file,
            read_protocol=PROTOCOLS[in_file.suffix],
            write_protocol=PROTOCOLS[out_file.suffix],
            protocol_args=protocol_args,
        )
    )


@pytest.fixture(params=applications, ids=[a.name for a in applications])
def application(request):
    return request.param


def test_application(application):
    e = edict.load(application.edict_file)
    out = io.StringIO()
    with open(application.in_file, "r") as fin:
        e.apply(
            fin,
            out,
            read_protocol=application.read_protocol,
            write_protocol=application.write_protocol,
            protocol_args=application.protocol_args,
        )

    with open(application.out_file, "r") as fout:
        fout_target = fout.read()

    assert out.getvalue() == fout_target
