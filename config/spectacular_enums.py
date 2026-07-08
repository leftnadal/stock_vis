"""
drf-spectacular ENUM_NAME_OVERRIDES dotted-path target.

여러 모델에서 동일 필드명(category / status)이 충돌하면 drf-spectacular가
자동 생성한 'CategoryCdbEnum' 같은 가독성 떨어지는 이름을 부여한다.
본 모듈은 의미가 분명한 enum 클래스를 정의해 schema가 명시적으로 참조하게 한다.

config/settings.py SPECTACULAR_SETTINGS.ENUM_NAME_OVERRIDES에서:
    'NewsCategoryEnum': 'config.spectacular_enums.NewsCategoryEnum'
같은 dotted path로 참조.
"""
from __future__ import annotations

from enum import Enum


class NewsCategoryEnum(str, Enum):
    """news.NewsArticle.category."""
    GENERAL = 'general'
    COMPANY = 'company'
    PRESS_RELEASE = 'press_release'
    FOREX = 'forex'
    CRYPTO = 'crypto'


class SavedPathStatusEnum(str, Enum):
    """chainsight.SavedPath.status."""
    WATCHING = 'watching'
    ACTIVE = 'active'
    ARCHIVED = 'archived'
    RESOLVED = 'resolved'
