import pytest
from conftest import FIX_TEMPLATE

from vitalflow.config import VitalFlowError
from vitalflow.source import inspect_csv, normalize_header, parse_fix


def test_fix_allowlist_preserves_units_and_public_recording_key():
    result = parse_fix(FIX_TEMPLATE.format(rid="bidmc_01").encode(), "bidmc_01")
    assert result == {
        "recording_id": "bidmc_01",
        "location": "micu",
        "numeric_channels": ["HR", "PULSE", "RESP", "SpO2"],
        "dataset_version": "1.0.0",
        "source_fix_url": "https://physionet.org/files/bidmc/1.0.0/bidmc_csv/bidmc_01_Fix.txt",
        "signals_sampling_hz": 125.0,
        "numerics_sampling_hz": 1.0,
    }


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (lambda text: text.replace("bidmc_01", "bidmc_02"), "recording marker"),
        (lambda text: text.replace("125 Hz", "0 Hz"), "invalid signals_sampling_hz"),
        (lambda text: text.replace("Location: micu", "Ward: micu"), "missing fields"),
        (lambda text: text + "\nLocation: micu", "repeated field"),
    ],
)
def test_fix_rejects_mismatched_and_invalid_records(mutation, error):
    with pytest.raises(VitalFlowError, match=error):
        parse_fix(mutation(FIX_TEMPLATE.format(rid="bidmc_01")).encode(), "bidmc_01")


def test_schema_inspection_normalizes_reordered_headers_and_preserves_token_evidence():
    result = inspect_csv(b"SpO2, Time [s], HR, PULSE, RESP\n98,-0,8e1,NaN,\n", "sample.csv")
    assert result["fields"] == ("spo2", "time_s", "hr", "pulse", "resp")
    assert result["header"][1] == " Time [s]"
    assert result["lexical_types"]["time_s"] == {"integer": 1}
    assert result["lexical_types"]["hr"] == {"decimal_or_scientific": 1}
    assert result["lexical_types"]["pulse"] == {"nan": 1}
    assert result["lexical_types"]["resp"] == {"blank": 1}
    with pytest.raises(VitalFlowError, match="Unexpected BIDMC CSV header"):
        normalize_header(["Time [s]", " HR", " PULSE", " RESP", " RESP"])


@pytest.mark.parametrize(
    ("data", "error"),
    [
        (b"<!doctype html>no data", "HTML"),
        (b"Time [s],HR,PULSE,RESP,SpO2\n0,1,2,3\n", "Malformed row"),
        (b"Time [s],HR,PULSE,RESP,SpO2\n", "without observations"),
    ],
)
def test_csv_rejects_invalid_file_structure(data, error):
    with pytest.raises(VitalFlowError, match=error):
        inspect_csv(data, "sample.csv")
