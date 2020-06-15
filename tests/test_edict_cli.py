import pathlib
import subprocess
import tempfile

TEST_DIR = pathlib.Path(__file__).parent
FILES_DIR = TEST_DIR / "files"


def test_edict_csv_identity_stdio():
    csv_in = FILES_DIR / "accounting.in.csv"
    with open(csv_in, "r") as fin:
        result = subprocess.run(
            ["edict", "-r", "csv", "-w", "csv"], stdin=fin, capture_output=True
        )
    assert result.returncode == 0
    with open(csv_in, "r") as fout_target:
        target = fout_target.read()
    assert result.stdout.decode() == target


def test_edict_csv_identity_fileio():
    csv_in = FILES_DIR / "accounting.in.csv"
    with tempfile.TemporaryDirectory() as tmpdir:
        actual_csv_out = pathlib.Path(tmpdir) / "output.csv"
        result = subprocess.run(
            ["edict", "-i", csv_in, "-r", "csv", "-o", actual_csv_out, "-w", "csv"]
        )
        assert result.returncode == 0
        with open(csv_in, "r") as fout_target:
            target = fout_target.read()
        with open(actual_csv_out, "r") as fout_actual:
            actual = fout_actual.read()
        assert actual == target


def test_edict_csv():
    csv_in = FILES_DIR / "accounting.in.csv"
    target_csv_out = FILES_DIR / "accounting.out.csv"
    edict_file = FILES_DIR / "accounting.edt"
    result = subprocess.run(
        ["edict", "-i", csv_in, "-r", "csv", "-w", "csv", edict_file],
        capture_output=True,
    )
    assert result.returncode == 0
    with open(target_csv_out, "r") as fout_target:
        target = fout_target.read()
    assert result.stdout.decode() == target


def test_edict_csv_chained():
    csv_in = FILES_DIR / "accounting.in.csv"
    target_csv_out = FILES_DIR / "cli-test" / "accounting.2.out.csv"
    edict_file = FILES_DIR / "accounting.edt"
    edict_file2 = FILES_DIR / "cli-test" / "accounting.2.edt"
    result = subprocess.run(
        ["edict", "-i", csv_in, "-r", "csv", "-w", "csv", edict_file, edict_file2],
        capture_output=True,
    )
    assert result.returncode == 0
    with open(target_csv_out, "r") as fout_target:
        target = fout_target.read()
    assert result.stdout.decode() == target
