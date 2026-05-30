"""Slice 7 Part 4 §5: reference example pairs 준비.

rubric §B.1 sample 5건의 압축 인덱스(점수+요약+key_signal)를 JSON으로 저장 →
manual eval form 헤더에 첨부하여 평가자가 sample anchoring.

사용:
  poetry run python -m scripts.slice7.prepare_reference_pairs
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "docs/portfolio/coach/slice7/step9_3_reference_pairs.json"


REFERENCES = {
    "sample_1": {
        "score": "nat=1, ins=2",
        "summary": "어색한 한국어 + 기본 해석만 (3건 이상 기계 번역체)",
        "key_signal": "'당신의 포트폴리오 0.45 보입니다' 같은 어순 깨짐",
    },
    "sample_2": {
        "score": "nat=3, ins=1",
        "summary": "무난한 한국어 + 통찰 0 (지표 나열만)",
        "key_signal": "사용자 질문에 답하지 않음, preset 의도 반영 X",
    },
    "sample_3": {
        "score": "nat=4, ins=3",
        "summary": "자연스러움 + 보통 통찰 (기본 해석 + preset 부분 반영)",
        "key_signal": "행동 시사점 막연 ('분산 고려' 정도)",
    },
    "sample_4": {
        "score": "nat=5, ins=4",
        "summary": "사람이 쓴 듯 + 좋은 통찰 (구체 행동 시사점 2건)",
        "key_signal": "위험/기회 양면 분석 부족",
    },
    "sample_5": {
        "score": "nat=5, ins=5",
        "summary": "정교한 흐름 + 매우 통찰 (위험·기회 양면 + 구체 전술 3건+)",
        "key_signal": "분기별 5% 조정 같은 실행 전술까지",
    },
}


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(REFERENCES, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ references: {OUT_PATH}")
    print(f"  samples: {len(REFERENCES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
