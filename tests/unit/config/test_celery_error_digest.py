"""HEARTBEAT-1 B·C-1 — error digest 회귀.

B: NotRegistered 실패는 TaskResult.task_name 이 NULL 이다. 그 레코드가 섞이면
   sorted() 가 str 과 None 을 비교하다 TypeError 로 죽었다 — 실패를 알려줄 장치가
   실패 때문에 죽는 구조. 2026-09-16·17 라이브 2건 발생.
C-1: 발송이 실패해도 산출물은 남아야 한다(알림 경로 이중화).
"""

import json

import pytest
from django.utils import timezone

from config.tasks import _task_sort_key, send_celery_error_digest


def _failure(task_name, exc_type, **extra):
    from django_celery_results.models import TaskResult

    return TaskResult.objects.create(
        task_id=f"t-{task_name or 'none'}-{exc_type}-{extra.get('n', 0)}",
        task_name=task_name,
        status="FAILURE",
        date_done=timezone.now(),
        result=json.dumps({"exc_type": exc_type, "exc_message": ["x"]}),
        traceback=f"{exc_type}: boom",
    )


class TestTaskSortKey:
    def test_none_becomes_empty_string(self):
        assert _task_sort_key(None) == ""

    def test_name_passes_through(self):
        assert _task_sort_key("a.b.c") == "a.b.c"

    def test_mixed_list_sorts_without_typeerror(self):
        """★ 회귀 핵심 — None 이 섞인 키 집합이 정렬 가능해야 한다."""
        keys = ["z.task", None, "a.task"]
        assert sorted(keys, key=_task_sort_key) == [None, "a.task", "z.task"]


@pytest.mark.django_db
class TestDigestWithNullTaskName:
    def test_digest_survives_null_task_name(self, tmp_path, monkeypatch):
        """★ 회귀 핵심 — NotRegistered(task_name=NULL) 가 섞여도 예외 없이 생성된다."""
        import config.tasks as ct

        monkeypatch.setattr(ct, "CELERY_DIGEST_ARTIFACT", tmp_path / "digest.json")
        monkeypatch.setattr(ct.settings, "CELERY_ERROR_RECIPIENTS", [], raising=False)
        _failure(None, "NotRegistered", n=1)
        _failure("metrics.tasks.send_daily_report_task", "SMTPAuthenticationError", n=2)
        _failure("config.tasks.send_celery_error_digest", "TypeError", n=3)

        out = send_celery_error_digest(days=1)  # 예외가 나면 실패
        assert out is not None

    def test_artifact_written_even_when_send_skipped(self, tmp_path, monkeypatch):
        """C-1 — 수신자가 없어 발송을 건너뛰어도 산출물은 남는다."""
        import config.tasks as ct

        art = tmp_path / "digest.json"
        monkeypatch.setattr(ct, "CELERY_DIGEST_ARTIFACT", art)
        monkeypatch.setattr(ct.settings, "CELERY_ERROR_RECIPIENTS", [], raising=False)
        _failure(None, "NotRegistered", n=4)

        send_celery_error_digest(days=1)
        assert art.exists(), "발송을 건너뛰어도 산출물은 남아야 한다"
        d = json.loads(art.read_text(encoding="utf-8"))
        assert d["failure_count"] >= 1
        assert "(이름없음·NotRegistered)" in d["by_task"]

    def test_artifact_written_even_when_send_raises(self, tmp_path, monkeypatch):
        """C-1 ★ — 발송이 예외를 던져도 산출물은 이미 저장돼 있다(이중화의 핵심)."""
        import config.tasks as ct

        art = tmp_path / "digest.json"
        monkeypatch.setattr(ct, "CELERY_DIGEST_ARTIFACT", art)
        monkeypatch.setattr(ct.settings, "CELERY_ERROR_RECIPIENTS", ["x@example.com"], raising=False)

        def _boom(*a, **k):
            raise RuntimeError("SMTP down")

        monkeypatch.setattr(ct, "send_mail", _boom)
        _failure(None, "NotRegistered", n=5)

        out = send_celery_error_digest(days=1)
        assert "failed" in str(out).lower()
        assert art.exists(), "발송 실패해도 산출물은 남아야 한다"

    def test_no_failures_skips_everything(self):
        """실패 0건이면 종전대로 조기 반환(동작 범위 불변)."""
        out = send_celery_error_digest(days=1)
        assert "No errors" in str(out)
