import io
from email.message import Message
from http.client import IncompleteRead
from urllib.error import URLError

import pytest

from vitalflow import acquisition
from vitalflow.acquisition import acquire, fetch
from vitalflow.config import SOURCE_BASE, VitalFlowError
from vitalflow.source import inspect_csv


class Response(io.BytesIO):
    def __init__(self, data: bytes, content_type: str):
        super().__init__(data)
        self.headers = Message()
        self.headers["Content-Type"] = content_type


@pytest.mark.parametrize("transient", [URLError("temporary failure"), IncompleteRead(b"partial")])
def test_fetch_retries_transient_and_html_responses(monkeypatch, transient):
    data = b"Time [s],HR,PULSE,RESP,SpO2\n0,70,72,17,98\n"
    responses = iter(
        [
            transient,
            Response(b"<html>temporary proxy page</html>", "text/html"),
            Response(data, "text/plain"),
        ]
    )

    def urlopen(*args, **kwargs):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(acquisition, "urlopen", urlopen)
    monkeypatch.setattr(acquisition.time, "sleep", lambda _: None)
    assert fetch(SOURCE_BASE + "test", lambda value: inspect_csv(value, "test")) == data


def test_partial_download_recovers_and_verified_cache_is_never_overwritten(
    project, responses, monkeypatch
):
    failed_url = SOURCE_BASE + "bidmc_csv/bidmc_02_Fix.txt"
    requested = []

    def fake_fetch(url, validate):
        requested.append(url)
        if url == failed_url and fail:
            raise VitalFlowError("test interruption")
        data = responses[url]
        validate(data)
        return data

    fail = True
    monkeypatch.setattr(acquisition, "fetch", fake_fetch)
    with pytest.raises(VitalFlowError, match="test interruption"):
        acquire(project, 2, offline=False)
    first = project.raw / "bidmc_csv" / "bidmc_01_Numerics.csv"
    before = (first.read_bytes(), first.stat().st_mtime_ns)
    fail = False
    requested.clear()
    records, manifest = acquire(project, 2, offline=False)
    assert requested == [failed_url]
    assert [f["status"] for f in manifest["files"]].count("cached") == 3
    requested.clear()
    assert acquire(project, 2, offline=True)[0] == records
    assert requested == []
    assert (first.read_bytes(), first.stat().st_mtime_ns) == before

    first.write_bytes(b"<html>tampered cache</html>")
    with pytest.raises(VitalFlowError, match="SHA-256 differs"):
        acquire(project, 2, offline=False)
    assert requested == []
    assert first.read_bytes() == b"<html>tampered cache</html>"
