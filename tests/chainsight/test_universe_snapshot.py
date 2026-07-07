"""
유니버스 스냅샷 서비스 테스트 (TH-3, 설계서 §6.0 잠금장치 3 Cycle 1 판).

검증 (지시서 요구 "저장·참조 별도 2건" + 추가):
- 저장: 라이브 유니버스를 배치 일자로 스냅샷 생성 + 전일 대비 diff 로그.
- 참조: 같은 batch_date 재호출 = 멱등(저장분 반환, 재조회 없음).
- diff: 전일 스냅샷 대비 추가/제거 심볼 산출.
- sector_constituents: 스냅샷 모집단 ∩ 섹터.
"""

from datetime import date

import pytest

from apps.chain_sight.models import UniverseSnapshot
from apps.chain_sight.services import universe_snapshot as us
from packages.shared.stocks.models import SP500Constituent


def _mk(symbol, sector="Information Technology", active=True):
    return SP500Constituent.objects.create(
        symbol=symbol,
        company_name=f"{symbol} Inc.",
        sector=sector,
        is_active=active,
    )


@pytest.mark.django_db
class TestUniverseSnapshotSave:
    def test_save_creates_snapshot_from_live_universe(self):
        """저장: SP500 active − '.' 심볼을 배치 일자로 동결."""
        _mk("AAA")
        _mk("BBB", sector="Financials")
        _mk("CC.D")           # '.' 포함 → 제외 (FMP 402 회피)
        _mk("ZZZ", active=False)  # 비활성 → 제외

        symbols, snap, diff = us.get_or_create_universe_snapshot(batch_date=date(2026, 7, 7))

        assert symbols == ["AAA", "BBB"]  # 정렬, '.'·비활성 제외
        assert snap.batch_date == date(2026, 7, 7)
        assert snap.symbols == ["AAA", "BBB"]
        assert diff["reused"] is False
        assert UniverseSnapshot.objects.count() == 1

    def test_diff_reports_added_and_removed_vs_previous(self):
        """전일 대비 추가/제거 diff 산출."""
        UniverseSnapshot.objects.create(
            batch_date=date(2026, 7, 6), symbols=["AAA", "OLD"]
        )
        _mk("AAA")
        _mk("NEW")
        # OLD 는 이제 유니버스에 없음 (제거), NEW 는 신규 (추가)

        symbols, _snap, diff = us.get_or_create_universe_snapshot(batch_date=date(2026, 7, 7))

        assert symbols == ["AAA", "NEW"]
        assert diff["added"] == ["NEW"]
        assert diff["removed"] == ["OLD"]


@pytest.mark.django_db
class TestUniverseSnapshotReference:
    def test_idempotent_reuse_of_existing_snapshot(self):
        """참조(멱등): 같은 batch_date 재호출은 저장분을 반환하고 라이브 재조회하지 않는다."""
        UniverseSnapshot.objects.create(
            batch_date=date(2026, 7, 7), symbols=["FROZEN1", "FROZEN2"]
        )
        # 라이브 유니버스를 바꿔도(신규 종목 추가) 스냅샷은 불변이어야 drift 차단
        _mk("LIVE_ADDED")

        symbols, snap, diff = us.get_or_create_universe_snapshot(batch_date=date(2026, 7, 7))

        assert symbols == ["FROZEN1", "FROZEN2"]  # 저장분 그대로 (LIVE_ADDED 미반영)
        assert diff["reused"] is True
        assert UniverseSnapshot.objects.count() == 1  # 중복 생성 없음

    def test_sector_constituents_intersects_snapshot_with_sector(self):
        """모집단 참조: 섹터 구성 = 스냅샷 심볼 ∩ 섹터."""
        _mk("TECH1", sector="Information Technology")
        _mk("TECH2", sector="Information Technology")
        _mk("FIN1", sector="Financials")

        members = us.sector_constituents(
            "Information Technology", ["TECH1", "TECH2", "FIN1", "NOT_IN_UNIVERSE"]
        )
        # TECH1/TECH2 는 스냅샷 ∩ IT, FIN1 은 섹터 불일치, NOT_IN_UNIVERSE 는 모집단 밖
        assert members == ["TECH1", "TECH2"]
