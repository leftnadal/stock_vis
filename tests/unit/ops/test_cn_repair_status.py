"""cn_repair_status 상태 머신 단위 테스트 — 순번 카운터·이상치 밴드 회귀.

경계-무관 stdlib 헬퍼. Django 불요 → 파일 경로 importlib 로드(sys.path 독립).
"""
import importlib.util
import json
from pathlib import Path

import pytest

_MOD_PATH = Path(__file__).resolve().parents[3] / "scripts" / "cn_repair_status.py"
_spec = importlib.util.spec_from_file_location("cn_repair_status", _MOD_PATH)
cn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cn)


@pytest.fixture
def status_file(tmp_path):
    return str(tmp_path / "status.json")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _record(path, batch, saved, updated, status, advance, exit_=0, target=20):
    cn.main(["record", "--status-file", path, "--batch", str(batch),
             "--target", str(target), "--saved", str(saved), "--updated", str(updated),
             "--exit", str(exit_), "--status", status, "--advance", str(advance),
             "--ts", "2026-07-29T22:10:00+09:00"])


# ── next(순번) ──
def test_next_default_1_when_no_file(status_file, capsys):
    cn.main(["next", "--status-file", status_file])
    assert capsys.readouterr().out.strip() == "1"


def test_record_advance_increments_next(status_file, capsys):
    _record(status_file, 1, 100, 5, "ok", 1)
    capsys.readouterr()
    cn.main(["next", "--status-file", status_file])
    assert capsys.readouterr().out.strip() == "2"


def test_record_no_advance_keeps_next(status_file, capsys):
    _record(status_file, 1, 0, 0, "zero", 0)
    capsys.readouterr()
    cn.main(["next", "--status-file", status_file])
    # 전진 보류 → batch1 재시도 (누락 방지 핵심)
    assert capsys.readouterr().out.strip() == "1"


def test_advance_uses_max_no_regression(status_file, capsys):
    _record(status_file, 1, 10, 0, "ok", 1)   # next=2
    _record(status_file, 2, 10, 0, "ok", 1)   # next=3
    _record(status_file, 1, 10, 0, "ok", 1)   # 재실행 batch1 → max(3, 2)=3, 역행 없음
    capsys.readouterr()
    cn.main(["next", "--status-file", status_file])
    assert capsys.readouterr().out.strip() == "3"


# ── band(이상치) ──
def test_band_disabled_under_3_samples(status_file, capsys):
    _record(status_file, 1, 100, 0, "ok", 1)
    _record(status_file, 2, 200, 0, "ok", 1)
    capsys.readouterr()
    cn.main(["band", "--status-file", status_file])
    med, low, high, n = capsys.readouterr().out.split()
    assert (med, low, high, n) == ("0", "0", "0", "2")


def test_band_computes_median_and_bounds(status_file, capsys):
    for b, net in enumerate([100, 200, 300], start=1):
        _record(status_file, b, net, 0, "ok", 1)
    capsys.readouterr()
    cn.main(["band", "--status-file", status_file])
    med, low, high, n = capsys.readouterr().out.split()
    assert float(med) == 200.0
    assert float(low) == 60.0    # 0.3 × 200
    assert float(high) == 600.0  # 3.0 × 200
    assert n == "3"


def test_band_excludes_zero_and_fail_from_samples(status_file, capsys):
    _record(status_file, 1, 100, 0, "ok", 1)
    _record(status_file, 2, 0, 0, "zero", 0)     # 제외
    _record(status_file, 3, 0, 0, "fail", 0)     # 제외
    _record(status_file, 4, 200, 0, "ok", 1)
    capsys.readouterr()
    cn.main(["band", "--status-file", status_file])
    _, _, _, n = capsys.readouterr().out.split()
    assert n == "2"  # ok 2건만


# ── 영속/원자성 ──
def test_history_and_net_persisted(status_file):
    _record(status_file, 1, 123, 4, "ok", 1)
    data = _read(status_file)
    h = data["history"][-1]
    assert h["net"] == 127 and h["saved"] == 123 and h["updated"] == 4
    assert data["last_status"] == "ok" and data["next_batch"] == 2


def test_ok_review_counts_as_sample_and_advances(status_file, capsys):
    _record(status_file, 1, 100, 0, "ok_review", 1)
    data = _read(status_file)
    assert data["next_batch"] == 2  # ok_review 도 전진
    capsys.readouterr()
    cn.main(["band", "--status-file", status_file])
    _, _, _, n = capsys.readouterr().out.split()
    assert n == "1"  # ok_review 도 밴드 표본
