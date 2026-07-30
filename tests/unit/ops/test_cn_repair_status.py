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


# ── G3: 10배치 소진 → 범위 종료 신호(next>total) ──
def test_next_exceeds_total_after_10_batches(status_file, capsys):
    for b in range(1, 11):
        _record(status_file, b, 100, 0, "ok", 1)
    capsys.readouterr()
    cn.main(["next", "--status-file", status_file])
    # next=11 > total(10) → 래퍼가 완료 감지·자동 unload (상시 수집기 변질 방지)
    assert int(capsys.readouterr().out.strip()) == 11


# ── G2: '안 돌았음' 감지 (check 리포터) ──
def test_check_never_run_when_no_file(status_file, capsys):
    rc = cn.main(["check", "--status-file", status_file])
    out = capsys.readouterr().out
    assert rc == 1 and "ATTENTION" in out  # 미착수 = 주의


def test_check_ok_when_recent(status_file, capsys):
    _record(status_file, 1, 100, 0, "ok", 1)
    capsys.readouterr()
    # 마지막 실행(22:10) 6시간 뒤 아침 확인 → OK
    rc = cn.main(["check", "--status-file", status_file,
                  "--now", "2026-07-30T04:10:00+09:00"])
    out = capsys.readouterr().out
    assert rc == 0 and "verdict=OK" in out


def test_check_stale_when_gap_exceeds_threshold(status_file, capsys):
    _record(status_file, 1, 100, 0, "ok", 1)
    capsys.readouterr()
    # 마지막 실행 3일 뒤 = STALE(무실행) → 주의(launchd 미발화 의심)
    rc = cn.main(["check", "--status-file", status_file,
                  "--now", "2026-08-01T22:10:00+09:00"])
    out = capsys.readouterr().out
    assert rc == 1 and "STALE" in out


def test_check_done_not_stale_after_completion(status_file, capsys):
    for b in range(1, 11):
        _record(status_file, b, 100, 0, "ok", 1)
    capsys.readouterr()
    # 완료(next=11>total) → 아무리 오래돼도 STALE 아님(DONE)
    rc = cn.main(["check", "--status-file", status_file,
                  "--now", "2026-09-01T00:00:00+09:00"])
    out = capsys.readouterr().out
    assert rc == 0 and "DONE" in out
