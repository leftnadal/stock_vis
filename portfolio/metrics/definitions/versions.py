"""
Stock-Vis Version Bundle (코드 상수)
======================================

AnalysisRun 생성 시 자동 주입되는 현재 버전.
변경 시 git commit으로 이력 관리.

버전 정책 (pre-MVP):
  - v1.x 동안은 pre-release 상태. minor 변경에 breaking change 포함 가능
  - 첫 MVP 출시 시점에 v2.0으로 major 재베이스 (semver 엄격 적용 시작)
  - Saved Analysis가 아직 0개인 현 단계에서는 retroactive migration 불필요
"""

CURRENT_VERSIONS = {
    "preset_version": "1.0",
    "metric_version": "1.2",  # 2026-04-18: Dict ↔ 코드 완전 동기화. metric_id 6 rename/재구성, 12 신규 추가, 총 57개
    "scoring_version": "1.0",
    "prompt_version": "1.0",
    "universe_version": "sp500_v1",
}


def get_current_versions() -> dict:
    """현재 버전 번들 반환. AnalysisRun 생성 시 사용."""
    return CURRENT_VERSIONS.copy()
