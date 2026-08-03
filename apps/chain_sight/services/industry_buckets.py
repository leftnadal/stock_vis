"""L2 시장관계 카테고리 — FMP industry → 표시 버킷 매핑 (⑳-3 S3-MINDMAP S2).

마인드맵 L2는 엣지에 태그를 쓰지 않고, 서빙 시 상대 노드의 Stock.industry를 표시 버킷으로
'파생'한다(기업 industry 변경 시 자동 추종, 데이터 중복 0). 버킷 어휘는 검수 normalized_tag
(53종)와 정렬하고, 산업 커버리지 확장을 위해 유틸리티·부동산·소재 버킷을 추가한다.

미매핑 industry는 원값으로 폴백(identity) — 롱테일은 자기 이름 버킷으로 표시.
케이스 정규화: FMP가 간헐 대문자로 넣는 값(SEMICONDUCTORS 등)을 casefold 키로 흡수.
"""

# 표시 버킷 (검수 normalized_tag 어휘 정렬 + L2 확장 3종)
BUCKET_SEMI = "반도체·메모리"
BUCKET_SW = "클라우드·엔터프라이즈SW"
BUCKET_COMM = "통신·네트워크"
BUCKET_FIN = "금융·결제·거래소"
BUCKET_HEALTH = "헬스케어·의료기기·제약"
BUCKET_INDUSTRIAL = "자동차·부품·산업재"
BUCKET_CONSUMER = "소매·소비재"
BUCKET_MEDIA = "미디어·스트리밍·검색"
BUCKET_TRAVEL = "여행·숙박·크루즈"
BUCKET_ENERGY = "에너지·유전·수처리"
BUCKET_UTIL = "유틸리티"          # L2 확장
BUCKET_REALESTATE = "부동산·REIT"  # L2 확장
BUCKET_MATERIALS = "소재·화학"     # L2 확장

# casefold(소문자) industry → 버킷
INDUSTRY_BUCKET_MAP = {
    # 반도체·하드웨어
    "semiconductors": BUCKET_SEMI,
    "electronic components": BUCKET_SEMI,
    "hardware, equipment & parts": BUCKET_SEMI,
    "computer hardware": BUCKET_SEMI,
    "consumer electronics": BUCKET_SEMI,
    # 소프트웨어·IT서비스
    "software - application": BUCKET_SW,
    "software - infrastructure": BUCKET_SW,
    "software - services": BUCKET_SW,
    "information technology services": BUCKET_SW,
    "internet content & information": BUCKET_SW,
    "e-commerce": BUCKET_SW,
    "technology": BUCKET_SW,
    "medical - healthcare information services": BUCKET_SW,
    # 통신·네트워크
    "telecommunications services": BUCKET_COMM,
    "communication equipment": BUCKET_COMM,
    # 금융
    "banks - regional": BUCKET_FIN,
    "banks - diversified": BUCKET_FIN,
    "financial - data & stock exchanges": BUCKET_FIN,
    "financial - credit services": BUCKET_FIN,
    "financial - capital markets": BUCKET_FIN,
    "capital markets": BUCKET_FIN,
    "asset management": BUCKET_FIN,
    "asset management - global": BUCKET_FIN,
    "insurance - property & casualty": BUCKET_FIN,
    "insurance - brokers": BUCKET_FIN,
    "insurance - diversified": BUCKET_FIN,
    "insurance - life": BUCKET_FIN,
    "insurance - reinsurance": BUCKET_FIN,
    "insurance - specialty": BUCKET_FIN,
    "investment - banking & investment services": BUCKET_FIN,
    "index fund": BUCKET_FIN,
    # 헬스케어
    "medical - devices": BUCKET_HEALTH,
    "medical - diagnostics & research": BUCKET_HEALTH,
    "medical - instruments & supplies": BUCKET_HEALTH,
    "medical - healthcare plans": BUCKET_HEALTH,
    "medical - distribution": BUCKET_HEALTH,
    "medical - care facilities": BUCKET_HEALTH,
    "medical - equipment & services": BUCKET_HEALTH,
    "medical - pharmaceuticals": BUCKET_HEALTH,
    "drug manufacturers - general": BUCKET_HEALTH,
    "drug manufacturers - specialty & generic": BUCKET_HEALTH,
    "biotechnology": BUCKET_HEALTH,
    # 산업재·운송·자동차
    "industrial - machinery": BUCKET_INDUSTRIAL,
    "industrial - distribution": BUCKET_INDUSTRIAL,
    "industrial - pollution & treatment controls": BUCKET_INDUSTRIAL,
    "aerospace & defense": BUCKET_INDUSTRIAL,
    "agricultural - machinery": BUCKET_INDUSTRIAL,
    "electrical equipment & parts": BUCKET_INDUSTRIAL,
    "manufacturing - tools & accessories": BUCKET_INDUSTRIAL,
    "auto - parts": BUCKET_INDUSTRIAL,
    "auto - manufacturers": BUCKET_INDUSTRIAL,
    "auto manufacturers": BUCKET_INDUSTRIAL,  # FMP 대문자 변형(하이픈 없음)
    "railroads": BUCKET_INDUSTRIAL,
    "trucking": BUCKET_INDUSTRIAL,
    "integrated freight & logistics": BUCKET_INDUSTRIAL,
    "airlines, airports & air services": BUCKET_INDUSTRIAL,
    "engineering & construction": BUCKET_INDUSTRIAL,
    "specialty business services": BUCKET_INDUSTRIAL,
    "consulting services": BUCKET_INDUSTRIAL,
    "staffing & employment services": BUCKET_INDUSTRIAL,
    "business equipment & supplies": BUCKET_INDUSTRIAL,
    "rental & leasing services": BUCKET_INDUSTRIAL,
    "security & protection services": BUCKET_INDUSTRIAL,
    "conglomerates": BUCKET_INDUSTRIAL,
    "waste management": BUCKET_INDUSTRIAL,
    # 소비재·소매
    "specialty retail": BUCKET_CONSUMER,
    "apparel - retail": BUCKET_CONSUMER,
    "apparel - footwear & accessories": BUCKET_CONSUMER,
    "apparel - manufacturers": BUCKET_CONSUMER,
    "discount stores": BUCKET_CONSUMER,
    "grocery stores": BUCKET_CONSUMER,
    "home improvement": BUCKET_CONSUMER,
    "packaged foods": BUCKET_CONSUMER,
    "food confectioners": BUCKET_CONSUMER,
    "food distribution": BUCKET_CONSUMER,
    "agricultural farm products": BUCKET_CONSUMER,
    "household & personal products": BUCKET_CONSUMER,
    "personal products & services": BUCKET_CONSUMER,
    "beverages - non-alcoholic": BUCKET_CONSUMER,
    "beverages - alcoholic": BUCKET_CONSUMER,
    "beverages - wineries & distilleries": BUCKET_CONSUMER,
    "tobacco": BUCKET_CONSUMER,
    "restaurants": BUCKET_CONSUMER,
    "luxury goods": BUCKET_CONSUMER,
    "furnishings, fixtures & appliances": BUCKET_CONSUMER,
    "auto - dealerships": BUCKET_CONSUMER,
    # 미디어
    "entertainment": BUCKET_MEDIA,
    "advertising agencies": BUCKET_MEDIA,
    "social media": BUCKET_MEDIA,
    "electronic gaming & multimedia": BUCKET_MEDIA,
    # 여행·레저
    "travel services": BUCKET_TRAVEL,
    "travel lodging": BUCKET_TRAVEL,
    "gambling, resorts & casinos": BUCKET_TRAVEL,
    "leisure": BUCKET_TRAVEL,
    # 에너지
    "oil & gas exploration & production": BUCKET_ENERGY,
    "oil & gas equipment & services": BUCKET_ENERGY,
    "oil & gas midstream": BUCKET_ENERGY,
    "oil & gas refining & marketing": BUCKET_ENERGY,
    "oil & gas integrated": BUCKET_ENERGY,
    "solar": BUCKET_ENERGY,
    # 유틸리티
    "regulated electric": BUCKET_UTIL,
    "regulated gas": BUCKET_UTIL,
    "regulated water": BUCKET_UTIL,
    "diversified utilities": BUCKET_UTIL,
    "general utilities": BUCKET_UTIL,
    "independent power producers": BUCKET_UTIL,
    "utilities - independent power producers": BUCKET_UTIL,
    "renewable utilities": BUCKET_UTIL,
    # 부동산·건설
    "reit - residential": BUCKET_REALESTATE,
    "reit - specialty": BUCKET_REALESTATE,
    "reit - retail": BUCKET_REALESTATE,
    "reit - office": BUCKET_REALESTATE,
    "reit - industrial": BUCKET_REALESTATE,
    "reit - healthcare facilities": BUCKET_REALESTATE,
    "reit - hotel & motel": BUCKET_REALESTATE,
    "reit - diversified": BUCKET_REALESTATE,
    "real estate - services": BUCKET_REALESTATE,
    "residential construction": BUCKET_REALESTATE,
    "construction": BUCKET_REALESTATE,
    "construction materials": BUCKET_REALESTATE,
    "packaging & containers": BUCKET_REALESTATE,
    # 소재·화학
    "chemicals - specialty": BUCKET_MATERIALS,
    "chemicals": BUCKET_MATERIALS,
    "agricultural inputs": BUCKET_MATERIALS,
    "steel": BUCKET_MATERIALS,
    "copper": BUCKET_MATERIALS,
    "gold": BUCKET_MATERIALS,
}


def industry_to_bucket(industry):
    """Stock.industry → 표시 버킷. 미매핑은 원값 폴백(identity), 빈값은 None."""
    if not industry:
        return None
    key = str(industry).strip()
    if not key:
        return None
    return INDUSTRY_BUCKET_MAP.get(key.lower(), key)
