import shutil

import pytest

from vitalflow.config import PROJECT_ROOT, Project

st = pytest.importorskip("streamlit")
pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

from streamlit.testing.v1 import AppTest  # noqa: E402

from vitalflow.dashboard.analysis import filter_recording, observed_stats  # noqa: E402
from vitalflow.dashboard.charts import raw_trend  # noqa: E402
from vitalflow.dashboard.replay import Replay, schedule_for  # noqa: E402


def test_filtered_statistics_and_chart_preserve_gaps():
    frame = pd.DataFrame({"time_s": [0.0, 1.0, 3.0, 4.0], "pulse": [72.0, None, 71.0, 73.0]})
    selected = filter_recording(frame, 0, 3)
    assert observed_stats(selected, ("pulse",)) == [
        {
            "Kanal": "PULSE",
            "Unit": "denyut/menit",
            "Total": 3,
            "Valid": 2,
            "Hilang": 1,
            "Minimum": 71.0,
            "Maksimum": 72.0,
            "Rata-rata": 71.5,
        }
    ]
    for visible in (True, False):
        fig = raw_trend(selected, ("pulse",), 1, markers=visible)
        assert tuple(fig.data[0].x) == (0, 1, 2, 3)
        assert tuple(fig.data[0].y) == (72, None, None, 71)
        assert fig.data[0].connectgaps is False
        assert len(fig.data) == (2 if visible else 1)
        if visible:
            assert fig.data[1].yaxis == "y2"
            assert fig.layout.yaxis2.domain[1] < fig.layout.yaxis.domain[0]
            assert tuple(fig.data[1].x) == (1,)
    with pytest.raises(ValueError, match="same unit"):
        raw_trend(selected, ("pulse", "spo2"), 1)


def test_replay_state_pause_resume_step_finish_reset():
    schedule = schedule_for([{"arrival_interval_ms": gap} for gap in (None, 1000, 2500)])
    assert schedule == (0, 1, 3.5)
    initial = Replay()
    running = initial.start(schedule, 10)
    assert running.running and running.visible == 1
    paused = running.pause(schedule, 11.4)
    assert not paused.running and paused.visible == 2
    assert paused.tick(schedule, 50) == paused
    resumed = paused.start(schedule, 51)
    assert resumed.tick(schedule, 52).visible == 2
    done = resumed.tick(schedule, 54)
    assert not done.running and done.visible == 3
    assert done.start(schedule, 55) == done
    assert initial.step(schedule, 10).step(schedule, 11).visible == 2
    assert Replay().visible == 0


def start(project, monkeypatch):
    monkeypatch.setenv("VITALFLOW_PROJECT_ROOT", str(project.root))
    return AppTest.from_file(str(PROJECT_ROOT / "dashboard/app.py"), default_timeout=20).run()


def test_streamlit_navigation_modes_filters_and_lab(dashboard_project, monkeypatch):
    app = start(dashboard_project, monkeypatch)
    assert not app.exception and len(app.get("plotly_chart")) == 2
    assert app.metric[0].value == "53"
    app.selectbox(key="vf_mode").set_value("fast").run()
    assert app.metric[0].value == "3"
    app.selectbox(key="vf_mode").set_value("default").run()
    assert app.metric[0].value == "10"
    app.selectbox(key="vf_mode").set_value("complete").run()
    app.radio(key="vf_page").set_value("Recording Explorer").run()
    app.selectbox(key="explorer_complete_recording").set_value("bidmc_13").run()
    app.selectbox(key="explorer_complete_channel").set_value("resp").run()
    assert not app.exception and app.dataframe[0].value.iloc[0]["Hilang"] == 1
    app.slider[0].set_value((0.0, 1.0)).run()
    assert app.dataframe[0].value.iloc[0]["Hilang"] == 0
    app.toggle(key="explorer_complete_gaps").set_value(False).run()
    app.button(key="reset_explorer").click().run()
    assert app.selectbox(key="explorer_complete_reset_1_recording").value == "bidmc_01"
    assert app.selectbox(key="explorer_complete_reset_1_channel").value == "hr"
    app.toggle(key="explorer_complete_reset_1_compare_hr").set_value(True).run()
    assert not app.exception and len(app.dataframe[0].value) == 2
    app.radio(key="vf_page").set_value("Big Data 5Vs Lab").run()
    assert app.radio(key="vf_lab").value == "Volume"
    app.radio(key="volume_view").set_value("Per percobaan").run()
    assert not app.exception and len(app.get("plotly_chart")) == 1
    for name in ("Variety", "Veracity", "Value", "Velocity"):
        app.radio(key="vf_lab").set_value(name).run()
        assert not app.exception, name
        if name == "Veracity":
            assert app.metric[1].label == "Timestamp negatif"
            app.radio(key="quality_scenario").set_value("fixture").run()
            assert app.metric[0].label == "Baris fixture"
            assert app.metric[0].value == "8"
        if name == "Velocity":
            app.button(key="replay_step").click().run()
            assert not app.exception and app.session_state["vf_replay"].visible == 1
            app.button(key="replay_reset").click().run()
            assert app.session_state["vf_replay"].visible == 0
    app.radio(key="vf_page").set_value("System Architecture").run()
    app.selectbox(key="architecture_stage").set_value("Penyimpanan Parquet").run()
    assert not app.exception and "Apache Parquet" in app.dataframe[0].value["Rincian"].tolist()
    app.radio(key="vf_page").set_value("Evidence & Methodology").run()
    assert not app.exception and "Volume" in app.dataframe[0].value["Persyaratan"].tolist()


def test_streamlit_missing_run_and_missing_detail(dashboard_project, tmp_path, monkeypatch):
    project = Project(tmp_path)
    shutil.copytree(
        dashboard_project.result(3), project.result(3), ignore=shutil.ignore_patterns("*.parquet")
    )
    app = start(project, monkeypatch)
    assert not app.exception and "run.json" in app.error[0].value
    assert "vitalflow run --mode complete" in app.code[0].value
    app.selectbox(key="vf_mode").set_value("fast").run()
    assert not app.error and app.metric[0].value == "3"
    app.radio(key="vf_page").set_value("Recording Explorer").run()
    assert not app.exception and "Parquet" in app.error[0].value
