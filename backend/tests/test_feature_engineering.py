from datetime import timedelta

import pytest

from app.ml.feature_engineering import FEATURE_NAMES, build_window_features
from app.ml.preprocessing import LogRow, prepare_frame
from tests.helpers import T0, traffic_rows


def test_prepare_frame_drops_rows_without_timestamp_and_counts_them() -> None:
    rows = [LogRow(T0, "INFO", "a", "t"), LogRow(None, "ERROR", "a", "t")]
    frame, dropped = prepare_frame(rows)
    assert len(frame) == 1 and dropped == 1


def test_counts_ratios_and_templates_in_one_window() -> None:
    rows = [
        LogRow(T0 + timedelta(seconds=1), "INFO", "api", "a"),
        LogRow(T0 + timedelta(seconds=2), "INFO", "api", "a"),
        LogRow(T0 + timedelta(seconds=3), "WARNING", "db", "w"),
        LogRow(T0 + timedelta(seconds=10), "ERROR", "db", "e"),
        LogRow(T0 + timedelta(seconds=20), "CRITICAL", "db", "c"),
    ]
    feats = build_window_features(prepare_frame(rows)[0], 60)
    row = feats.iloc[0]
    assert len(feats) == 1
    assert (row.info_count, row.warning_count, row.error_count, row.critical_count) == (2, 1, 1, 1)
    assert row.log_volume == 5 and row.error_ratio == pytest.approx(2 / 5)
    assert row.warning_ratio == pytest.approx(1 / 5)
    assert row.unique_templates == 4 and row.repeated_templates == 1
    assert row.max_service_events == 3 and row.service_count == 2
    assert row.mean_seconds_between_errors == pytest.approx(10.0)
    assert row.affected_service == "db"  # service with the errors


def test_feature_columns_are_complete_and_numeric() -> None:
    feats = build_window_features(prepare_frame(traffic_rows())[0], 60)
    assert list(feats.columns[: len(FEATURE_NAMES)]) == FEATURE_NAMES
    assert not feats[FEATURE_NAMES].isna().any().any()


def test_error_change_uses_previous_window_and_gaps_count_as_zero() -> None:
    rows = [LogRow(T0 + timedelta(seconds=5), "ERROR", "a", "e")] * 3 + [
        LogRow(T0 + timedelta(minutes=2, seconds=5), "ERROR", "a", "e")
    ]
    feats = build_window_features(prepare_frame(rows)[0], 60)
    assert feats["error_change"].tolist() == [0.0, 1.0]  # window 2 vs the empty window 1 (gaps count as zero)


def test_window_size_changes_number_of_windows() -> None:
    frame = prepare_frame(traffic_rows(minutes=30, burst_minute=None))[0]
    assert len(build_window_features(frame, 60)) == 30
    assert len(build_window_features(frame, 300)) == 6


def test_features_are_causal_future_rows_do_not_change_past_windows() -> None:
    all_rows = traffic_rows(minutes=60, burst_minute=50)
    cutoff = T0 + timedelta(minutes=30)
    past_only = [r for r in all_rows if r.timestamp < cutoff]
    f_past = build_window_features(prepare_frame(past_only)[0], 60)
    f_all = build_window_features(prepare_frame(all_rows)[0], 60)
    shared = f_past.iloc[:-1]  # last past window may be cut mid-way by the cutoff itself
    cols = [*FEATURE_NAMES]
    assert shared[cols].equals(f_all.loc[shared.index, cols])


def test_empty_input_gives_empty_frame() -> None:
    assert build_window_features(prepare_frame([])[0]).empty


def test_absurdly_wide_range_is_rejected() -> None:
    rows = [LogRow(T0, "INFO", "a", "t"), LogRow(T0 + timedelta(days=3650), "INFO", "a", "t")]
    with pytest.raises(ValueError):
        build_window_features(prepare_frame(rows)[0], 1)
