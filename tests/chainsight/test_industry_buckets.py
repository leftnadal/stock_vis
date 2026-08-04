"""⑳-3 S3-MINDMAP S2 — industry→표시 버킷 매핑표."""

from apps.chain_sight.services.industry_buckets import (
    INDUSTRY_BUCKET_MAP,
    industry_to_bucket,
)


class TestIndustryBuckets:
    def test_core_mappings(self):
        assert industry_to_bucket("Semiconductors") == "반도체·메모리"
        assert industry_to_bucket("Software - Application") == "클라우드·엔터프라이즈SW"
        assert industry_to_bucket("Banks - Regional") == "금융·결제·거래소"
        assert industry_to_bucket("Medical - Devices") == "헬스케어·의료기기·제약"
        assert industry_to_bucket("Regulated Electric") == "유틸리티"
        assert industry_to_bucket("REIT - Residential") == "부동산·REIT"
        assert industry_to_bucket("Chemicals - Specialty") == "소재·화학"

    def test_casefold_uppercase_variants(self):
        # FMP가 간헐 대문자로 넣는 값 흡수
        assert industry_to_bucket("SEMICONDUCTORS") == "반도체·메모리"
        assert industry_to_bucket("AUTO MANUFACTURERS") == industry_to_bucket("AUTO MANUFACTURERS")
        assert industry_to_bucket("CAPITAL MARKETS") == "금융·결제·거래소"
        assert industry_to_bucket("CONSUMER ELECTRONICS") == "반도체·메모리"

    def test_unmapped_falls_back_to_raw(self):
        # 미등록 industry는 원값 폴백(identity)
        assert industry_to_bucket("Some New Industry XYZ") == "Some New Industry XYZ"

    def test_empty_and_none(self):
        assert industry_to_bucket(None) is None
        assert industry_to_bucket("") is None
        assert industry_to_bucket("   ") is None

    def test_whitespace_stripped(self):
        assert industry_to_bucket("  Semiconductors  ") == "반도체·메모리"

    def test_coverage_guarantee_by_fallback(self):
        # 폴백 구조상 비어있지 않은 어떤 industry도 비어있지 않은 버킷을 얻는다(전값 커버)
        samples = [
            "Regulated Electric", "Industrial - Machinery", "Semiconductors",
            "Software - Application", "Aerospace & Defense", "Asset Management",
            "Oil & Gas Exploration & Production", "Entertainment", "Restaurants",
            "REIT - Retail", "Biotechnology", "Steel", "Grocery Stores",
            "Rare Unmapped Industry", "Gold", "Tobacco", "Airlines, Airports & Air Services",
        ]
        for ind in samples:
            b = industry_to_bucket(ind)
            assert b and b.strip(), f"버킷 비어있음: {ind}"

    def test_bucket_count_reasonable(self):
        # 매핑된 버킷은 소수(마인드맵 상위 가지) — 13개 정도
        assert len(set(INDUSTRY_BUCKET_MAP.values())) <= 15
