"""검증 스크립트 공통 — Django 초기화."""

from __future__ import annotations

import os

import django


def init_django() -> None:
    """`DJANGO_SETTINGS_MODULE`을 `config.settings`로 고정 + django.setup()."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
