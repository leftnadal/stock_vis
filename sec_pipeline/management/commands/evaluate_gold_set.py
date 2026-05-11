"""
SEC-PR-5: Gold Set 평가 management command.

Usage:
    python manage.py evaluate_gold_set
    python manage.py evaluate_gold_set --prompt-version v1
"""

import json
import os

from django.core.management.base import BaseCommand

from sec_pipeline.models import RawDocumentStore, SupplyChainEvidence


class Command(BaseCommand):
    help = 'SEC Pipeline Gold Set 평가'

    def add_arguments(self, parser):
        parser.add_argument(
            '--prompt-version', type=str, default=None,
            help='평가할 프롬프트 버전 (기본: 전체)',
        )

    def handle(self, *args, **options):
        prompt_version = options.get('prompt_version')

        # Gold Set 로드
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'fixtures', 'gold_set.json',
        )
        with open(fixture_path, 'r') as f:
            gold_set = json.load(f)

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'SEC Pipeline Gold Set 평가 (prompt_version={prompt_version or "all"})'
        ))
        self.stdout.write('=' * 70)

        # ── Section Presence 평가 ──
        section_results = self._evaluate_sections(gold_set)

        # ── Track A Precision & Recall 평가 ──
        track_a_results = self._evaluate_track_a(gold_set, prompt_version)

        # ── 요약 ──
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.MIGRATE_HEADING('Summary'))

        section_rate = section_results['correct'] / max(section_results['total'], 1)
        self.stdout.write(
            f"Section Extraction: {section_results['correct']}/{section_results['total']} "
            f"= {section_rate:.1%} (target: ≥90%)"
        )

        if track_a_results['precision_denom'] > 0:
            precision = track_a_results['tp'] / track_a_results['precision_denom']
            self.stdout.write(
                f"Track A Precision: {track_a_results['tp']}/{track_a_results['precision_denom']} "
                f"= {precision:.1%} (target: ≥70%)"
            )
        else:
            self.stdout.write("Track A Precision: N/A (no extractions)")

        if track_a_results['recall_denom'] > 0:
            recall = track_a_results['tp'] / track_a_results['recall_denom']
            self.stdout.write(
                f"Track A Recall: {track_a_results['tp']}/{track_a_results['recall_denom']} "
                f"= {recall:.1%} (target: ≥50%)"
            )
        else:
            self.stdout.write("Track A Recall: N/A (no gold labels)")

    def _evaluate_sections(self, gold_set):
        """섹션 추출 정확도 평가."""
        self.stdout.write(self.style.MIGRATE_HEADING('\n[Section Extraction]'))

        total = 0
        correct = 0
        not_collected = 0

        for entry in gold_set:
            symbol = entry['symbol']
            expected = entry.get('section_presence', {})

            doc = (RawDocumentStore.objects
                   .filter(symbol_id=symbol)
                   .order_by('-filing_date')
                   .first())

            if not doc:
                self.stdout.write(f"  {symbol}: NOT COLLECTED")
                not_collected += 1
                continue

            for key in ['item_1', 'item_1a', 'item_7']:
                if key not in expected:
                    continue
                total += 1
                actual = bool(getattr(doc, f'{key}_text', ''))
                expected_val = expected[key]

                if actual == expected_val:
                    correct += 1
                    mark = '✓'
                else:
                    mark = '✗'

                self.stdout.write(f"  {symbol} {key}: {mark} (expected={expected_val}, actual={actual})")

        self.stdout.write(f"\n  Total: {correct}/{total}, Not collected: {not_collected}")
        return {'correct': correct, 'total': total, 'not_collected': not_collected}

    def _evaluate_track_a(self, gold_set, prompt_version):
        """Track A Precision & Recall 평가."""
        self.stdout.write(self.style.MIGRATE_HEADING('\n[Track A — Supply Chain]'))

        tp = 0  # True Positive
        fp = 0  # False Positive
        fn = 0  # False Negative

        for entry in gold_set:
            symbol = entry['symbol']
            gold_relations = entry.get('supply_chain_relations', [])

            # DB에서 추출된 관계
            qs = SupplyChainEvidence.objects.filter(source_company_id=symbol)
            if prompt_version:
                qs = qs.filter(prompt_version=prompt_version)

            extracted = list(qs.values_list('target_company_name', 'relationship_type'))

            # Gold → extracted 매칭 (target_name 부분 일치)
            gold_matched = set()
            extracted_matched = set()

            for g_idx, gold_rel in enumerate(gold_relations):
                gold_name = gold_rel['target_name'].lower()
                for e_idx, (e_name, e_type) in enumerate(extracted):
                    if e_idx in extracted_matched:
                        continue
                    if gold_name in e_name.lower() or e_name.lower() in gold_name:
                        # 이름 매칭 성공
                        if gold_rel['primary_type'] == e_type:
                            tp += 1
                            gold_matched.add(g_idx)
                            extracted_matched.add(e_idx)
                            self.stdout.write(
                                f"  {symbol}: TP — {gold_rel['target_name']} "
                                f"({gold_rel['primary_type']})"
                            )
                            break

            # 미매칭 gold = FN
            for g_idx, gold_rel in enumerate(gold_relations):
                if g_idx not in gold_matched:
                    fn += 1
                    self.stdout.write(
                        f"  {symbol}: FN — {gold_rel['target_name']} "
                        f"({gold_rel['primary_type']}) NOT EXTRACTED"
                    )

            # 미매칭 extracted = FP
            fp_count = len(extracted) - len(extracted_matched)
            if fp_count > 0:
                fp += fp_count
                self.stdout.write(f"  {symbol}: FP — {fp_count} extra extractions")

            if not gold_relations and not extracted:
                self.stdout.write(f"  {symbol}: OK — no relations expected or found")

        self.stdout.write(f"\n  TP={tp}, FP={fp}, FN={fn}")
        return {
            'tp': tp,
            'precision_denom': tp + fp,
            'recall_denom': tp + fn,
        }
