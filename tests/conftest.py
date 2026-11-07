import shutil

import pytest

from vitalflow.config import PROJECT_ROOT, Project
from vitalflow.spark import session

FIX_TEMPLATE = """{rid}
Signals: RESP; PLETH; II
Signals sampling frequency: 125 Hz
Numerics: HR; PULSE; RESP; SpO2
Numerics sampling frequency: 1 Hz
Location: micu
MIMIC II matched wdb ID: synthetic private reference
Age: synthetic
"""


@pytest.fixture(scope="session")
def spark():
    spark = session()
    yield spark
    spark.stop()


@pytest.fixture
def project(tmp_path):
    fixture = tmp_path / "data" / "scenarios"
    fixture.mkdir(parents=True)
    shutil.copyfile(
        PROJECT_ROOT / "data" / "scenarios" / "controlled_quality.csv",
        fixture / "controlled_quality.csv",
    )
    return Project(tmp_path)


@pytest.fixture
def responses():
    """Explicitly synthetic, local stand-ins for the immutable download cache."""
    from vitalflow.acquisition import CHECKSUM_FILE, sha256
    from vitalflow.config import SOURCE_BASE

    header = "Time [s], HR, PULSE, RESP, SpO2\n"
    source = {
        "bidmc_01": header + "0,70,71,16,98\n1,72,NaN,17,\n",
        "bidmc_02": header + "-1,81,81,18,97\n0,80,81,18,97\n120,86,85,19,97\n",
        "bidmc_03": "SpO2, Time [s], HR, RESP, PULSE\n96,0,90,20,89\n95,240,91,21,90\n",
    }
    files = {}
    for rid, numeric_text in source.items():
        files[f"bidmc_csv/{rid}_Numerics.csv"] = numeric_text.encode()
        files[f"bidmc_csv/{rid}_Fix.txt"] = FIX_TEMPLATE.format(rid=rid).encode()
    files[CHECKSUM_FILE] = "".join(
        f"{sha256(data)} {name}\n" for name, data in files.items()
    ).encode()
    return {f"{SOURCE_BASE}{name}": data for name, data in files.items()}
