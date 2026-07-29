#!/usr/bin/env python3
"""cn_repair_status — C-N-REPAIR 무인 배치 상태 머신 (stdlib only, 경계-무관).

C-N-REPAIR 야간 재수집 래퍼(cn_repair_nightly.sh)의 순번 카운터·이상치 밴드를
담당한다. Django/apps 의존 0 (순수 json) — 경계(apps→shared) 위반 없음, 단위 테스트 가능.

왜 체크포인트 카운터인가 (STEP 0 실측 2026-07-29):
  지시서 STEP 2-1 문자 그대로 "경과일+1"은 오늘(day2) 실행 시 batch1(07-28 미실행)을
  영구 건너뛴다. → 캘린더 산술 대신 **성공 시에만 전진하는 next_batch 체크포인트**로
  누락 없이 순차 진행(멱등 --skip-covered 재실행도 안전).

이상치 밴드 (퀀트):
  성공 이력 net(=saved+updated)의 중앙값 대비 [0.3배, 3.0배]. 표본 <3 = 밴드 비활성
  (0건만 이상). 0건 = 대상일이 null(미수집)인데 무수집 = fetch 실패/전량 skip 의심 → 이상.

사용:
    python cn_repair_status.py next  --status-file F              # 다음 배치 번호(기본 1)
    python cn_repair_status.py band  --status-file F              # "median low high n"
    python cn_repair_status.py record --status-file F --batch N \\
        --target T --saved S --updated U --exit E \\
        --status ok|ok_review|zero|fail --advance 0|1 --ts ISO
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys

DEFAULT_TOTAL = 10
BAND_LOW = 0.3
BAND_HIGH = 3.0
MIN_SAMPLES = 3


def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {"next_batch": 1, "total_batches": DEFAULT_TOTAL, "history": [],
                "last_run_ts": None, "last_status": None}
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("next_batch", 1)
    data.setdefault("total_batches", DEFAULT_TOTAL)
    data.setdefault("history", [])
    return data


def _atomic_write(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _ok_net_values(history: list) -> list:
    """성공/성공-검토 이력의 net(>0)만 — 밴드 산정 표본."""
    return [h["net"] for h in history
            if h.get("status") in ("ok", "ok_review") and h.get("net", 0) > 0]


def cmd_next(args) -> int:
    print(_load(args.status_file)["next_batch"])
    return 0


def cmd_band(args) -> int:
    vals = _ok_net_values(_load(args.status_file)["history"])
    if len(vals) < MIN_SAMPLES:
        # 밴드 비활성 신호: median=low=high=0, n<MIN_SAMPLES
        print(f"0 0 0 {len(vals)}")
        return 0
    med = statistics.median(vals)
    print(f"{med:.1f} {med * BAND_LOW:.1f} {med * BAND_HIGH:.1f} {len(vals)}")
    return 0


def cmd_record(args) -> int:
    data = _load(args.status_file)
    net = args.saved + args.updated
    data["history"].append({
        "batch": args.batch, "ts": args.ts, "target_windows": args.target,
        "saved": args.saved, "updated": args.updated, "net": net,
        "exit": args.exit, "status": args.status,
    })
    data["last_run_ts"] = args.ts
    data["last_status"] = args.status
    if args.advance == 1:
        # 전진은 성공 시에만. max()로 동시/재실행에도 역행 방지.
        data["next_batch"] = max(data.get("next_batch", 1), args.batch + 1)
    _atomic_write(args.status_file, data)
    print(f"recorded batch={args.batch} net={net} status={args.status} "
          f"next_batch={data['next_batch']}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="C-N-REPAIR 배치 상태 머신")
    sub = p.add_subparsers(dest="cmd", required=True)

    pn = sub.add_parser("next"); pn.add_argument("--status-file", required=True)
    pn.set_defaults(func=cmd_next)

    pb = sub.add_parser("band"); pb.add_argument("--status-file", required=True)
    pb.set_defaults(func=cmd_band)

    pr = sub.add_parser("record")
    pr.add_argument("--status-file", required=True)
    pr.add_argument("--batch", type=int, required=True)
    pr.add_argument("--target", type=int, default=0)
    pr.add_argument("--saved", type=int, default=0)
    pr.add_argument("--updated", type=int, default=0)
    pr.add_argument("--exit", type=int, default=0)
    pr.add_argument("--status", required=True,
                    choices=["ok", "ok_review", "zero", "fail"])
    pr.add_argument("--advance", type=int, choices=[0, 1], required=True)
    pr.add_argument("--ts", required=True)
    pr.set_defaults(func=cmd_record)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
