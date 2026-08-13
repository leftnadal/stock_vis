"""CS-P2-8K Slice2: 8-K 수집기 (백필 1년, EDGAR only, FMP 0).

682 유니버스 CIK × item 1.01/2.01 필터 · 백필 --days(기본 365) · EDGAR 규약(UA·10req/s)
· 재개 가능(기존 accession_no skip) · 재시도.

기본 --dry-run: EDGAR 스캔 → 건수/커버/기간 분포 집계 + --sample 개 원문 발췌(게이트용, DB 미기록).
--apply: SEC8KFiling 적재(마이그 0004 적용 후에만 = 병진 GO 뒤). 관계 착지는 별도(Slice3).

주의: dev=prod 공유 DB. --apply 는 신규 테이블 sec_8k_filing 에만 INSERT(기존 무접촉).
"""

import time
from collections import Counter
from datetime import date, datetime, timedelta

import requests
from django.core.management.base import BaseCommand

from packages.shared.api_request.sec_edgar_client import (
    SECEdgarClient,
    SECEdgarError,
)

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
DEFAULT_ITEMS = ["1.01", "2.01"]


def download_8k_text(client, cik, acc_nodash, primary_doc, retries=2):
    """primaryDocument 직접 URL로 8-K 원문 다운로드(공유 클라이언트의 디렉토리 스크래퍼 우회).

    archives 경로는 CIK를 leading-zero 없이 사용. client._make_request로 rate limit 준수.
    503(일시) 등은 짧게 재시도.
    """
    cik_int = str(int(cik))  # zero-padding 제거
    url = f"{client.ARCHIVES_URL}/{cik_int}/{acc_nodash}/{primary_doc}"
    last = None
    for attempt in range(retries + 1):
        try:
            resp = client._make_request(url, timeout=60)
            if primary_doc.lower().endswith((".htm", ".html")):
                return client._html_to_text(resp.text)
            return resp.text
        except Exception as e:
            last = e
            time.sleep(1.0 * (attempt + 1))
    raise last


class Command(BaseCommand):
    help = "8-K 수집(item 1.01/2.01, 백필). 기본 dry-run(스캔+표본), --apply로 SEC8KFiling 적재."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="SEC8KFiling 적재(마이그 후).")
        parser.add_argument("--days", type=int, default=365, help="백필 기간(캘린더일).")
        parser.add_argument("--limit", type=int, default=0, help="유니버스 상한(0=전체, 테스트용).")
        parser.add_argument("--sample", type=int, default=20, help="dry-run 원문 발췌 건수.")
        parser.add_argument("--items", type=str, default=",".join(DEFAULT_ITEMS))

    def handle(self, *args, **opts):
        from packages.shared.stocks.models import Stock

        apply = opts["apply"]
        cutoff = date.today() - timedelta(days=opts["days"])
        target_items = {x.strip() for x in opts["items"].split(",") if x.strip()}
        client = SECEdgarClient()

        # 1) ticker→cik (1 요청)
        client._rate_limit()
        tk2cik = {}
        try:
            data = client._session.get(TICKERS_URL, timeout=20).json()
            for e in data.values():
                tk2cik[e.get("ticker", "").upper()] = str(e["cik_str"]).zfill(10)
        except Exception as e:
            self.stderr.write(f"company_tickers.json 실패: {e}")
            return

        def resolve_cik(sym):
            u = sym.upper()
            return tk2cik.get(u) or tk2cik.get(u.replace(".", "-"))

        universe = list(Stock.objects.values_list("symbol", flat=True).order_by("symbol"))
        if opts["limit"]:
            universe = universe[: opts["limit"]]

        # --apply: 기존 적재분 skip
        existing_acc = set()
        if apply:
            from services.sec_pipeline.models import SEC8KFiling

            existing_acc = set(SEC8KFiling.objects.values_list("accession_no", flat=True))

        covered = missing = 0
        item_counter = Counter()
        month_counter = Counter()
        per_stock_hits = Counter()
        matched_filings = []  # (sym, cik, acc, fdate, items_list, company)
        scan_fail = 0

        self.stdout.write(
            f"=== 8-K 스캔 시작 (백필 {opts['days']}일, cutoff={cutoff}, items={sorted(target_items)}, "
            f"universe={len(universe)}, mode={'APPLY' if apply else 'DRY-RUN'}) ==="
        )

        for idx, sym in enumerate(universe):
            cik = resolve_cik(sym)
            if not cik:
                missing += 1
                continue
            covered += 1
            try:
                info = client.get_company_info(cik)  # rate-limited
            except SECEdgarError:
                scan_fail += 1
                continue
            except Exception:
                scan_fail += 1
                continue
            rec = info.get("filings", {}).get("recent", {})
            forms = rec.get("form", [])
            accs = rec.get("accessionNumber", [])
            fdates = rec.get("filingDate", [])
            items_arr = rec.get("items", [])
            primary = rec.get("primaryDocument", [])
            company = info.get("name", sym)
            for i, f in enumerate(forms):
                if f not in ("8-K", "8-K/A"):
                    continue
                try:
                    fd = datetime.strptime(fdates[i], "%Y-%m-%d").date()
                except Exception:
                    continue
                if fd < cutoff:
                    continue
                raw_items = items_arr[i] if i < len(items_arr) else ""
                items_list = [x.strip() for x in raw_items.split(",") if x.strip()]
                if not (target_items & set(items_list)):
                    continue
                # 대상 filing
                for it in target_items & set(items_list):
                    item_counter[it] += 1
                month_counter[fd.strftime("%Y-%m")] += 1
                per_stock_hits[sym] += 1
                matched_filings.append(
                    {
                        "sym": sym, "cik": cik,
                        "acc": accs[i].replace("-", ""),
                        "fdate": fd, "items": items_list, "company": company,
                        "primary": primary[i] if i < len(primary) else "",
                    }
                )
            if (idx + 1) % 100 == 0:
                self.stdout.write(f"  ...스캔 {idx+1}/{len(universe)}  누적 대상 {len(matched_filings)}")

        # ── 집계 리포트 ──
        self.stdout.write("\n=== 스캔 집계 ===")
        self.stdout.write(f"  CIK 커버: {covered}/{len(universe)} ({covered/len(universe)*100:.1f}%)  미매칭 {missing}  스캔실패 {scan_fail}")
        self.stdout.write(f"  대상 filing(중복행 제거 전 filing 수): {len(matched_filings)}")
        self.stdout.write(f"  item별 건수: {dict(item_counter)}")
        self.stdout.write(f"  종목 커버(1건+ 보유): {len(per_stock_hits)}")
        self.stdout.write(f"  기간 분포(월별): {dict(sorted(month_counter.items()))}")
        top = per_stock_hits.most_common(10)
        self.stdout.write(f"  상위 종목: {top}")

        if not apply:
            # 표본 원문 발췌
            n = opts["sample"]
            if n > 0 and matched_filings:
                step = max(1, len(matched_filings) // n)
                sample = matched_filings[::step][:n]
                self.stdout.write(f"\n=== 원문 표본 {len(sample)}건 발췌(각 앞 600자) ===")
                for m in sample:
                    try:
                        text = download_8k_text(client, m["cik"], m["acc"], m["primary"])
                    except Exception as e:
                        self.stdout.write(f"\n--- {m['sym']} {m['fdate']} items={m['items']} : 다운로드 실패 {e}")
                        continue
                    excerpt = " ".join(text.split())[:600]
                    self.stdout.write(
                        f"\n--- {m['sym']} {m['fdate']} items={m['items']} acc={m['acc']} ({len(text)}자) ---\n{excerpt}"
                    )
            self.stdout.write(self.style.WARNING("\ndry-run: DB 기록 0건 (--apply + migrate 0004 후 적재)"))
            return

        # ── --apply: SEC8KFiling 적재 ──
        from services.sec_pipeline.models import SEC8KFiling

        stock_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=[m["sym"] for m in matched_filings])}
        # filing 단위 dedup(같은 acc 여러 target item)
        by_acc = {}
        for m in matched_filings:
            by_acc.setdefault(m["acc"], m)
        created = skipped = failed = 0
        for acc, m in by_acc.items():
            if acc in existing_acc:
                skipped += 1
                continue
            try:
                text = download_8k_text(client, m["cik"], acc, m["primary"])
            except Exception as e:
                failed += 1
                self.stderr.write(f"  다운로드 실패 {m['sym']} {acc}: {e}")
                continue
            st = "collected" if text.strip() else "empty"
            SEC8KFiling.objects.create(
                symbol=stock_map[m["sym"]],
                cik=m["cik"],
                accession_no=acc,
                filing_date=m["fdate"],
                items=m["items"],
                primary_doc_url="",
                raw_text=text,
                status=st,
            )
            created += 1
            if created % 50 == 0:
                self.stdout.write(f"  ...적재 {created}")
        self.stdout.write(self.style.SUCCESS(
            f"\n적재 완료: created {created} / skipped(기존) {skipped} / failed {failed}"
        ))
