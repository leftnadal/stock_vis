"""LLM 빌더 (Phase A-MVP + Hardening) 단위 테스트."""

import uuid
from unittest.mock import patch, MagicMock

import pytest

from thesis.services.builder_state import (
    BuilderMode, BuilderPhase, FallbackReason,
    ChatMessage, PremiseData, IndicatorRecommendation,
    CollectedData, ConversationState,
    VALID_THESIS_TYPES, MONITORING_PRESETS,
)
from thesis.services.prompt_builder import (
    build_base_instruction, build_type_guide_block,
    build_indicator_block, build_system_prompt,
    get_indicator_by_id, INDICATOR_CATALOG,
)
from thesis.services.llm_postprocess import (
    normalize_llm_output, validate_llm_output, merge_to_collected,
)
from thesis.services.builder_events import (
    log_event,
    EVENT_BUILDER_STARTED, EVENT_PROPOSAL_GENERATED,
    EVENT_LLM_PARSE_FAILED, EVENT_FALLBACK_TRIGGERED,
    EVENT_PRESET_SELECTED, EVENT_CONFIRM_CLICKED,
    EVENT_THESIS_CREATED,
)
from thesis.feature_flags import FEATURE_FLAGS, get_feature_flags


# ──────────────────────────────────────────────
# builder_state.py 테스트
# ──────────────────────────────────────────────

class TestBuilderState:
    def test_conversation_state_roundtrip(self):
        """ConversationState model_dump → model_validate 왕복."""
        state = ConversationState(conv_id='test-123', entry_source='free_input')
        d = state.model_dump()
        restored = ConversationState.model_validate(d)
        assert restored.conv_id == 'test-123'
        assert restored.mode == 'llm'
        assert restored.phase == 'proposal'
        assert restored.turn_count == 0
        assert restored.history == []

    def test_conversation_state_with_history(self):
        """history 포함 직렬화/역직렬화."""
        state = ConversationState(
            conv_id='test-456',
            history=[
                ChatMessage(role='user', content='삼성전자 반등'),
                ChatMessage(role='assistant', content='가설을 설계했어요.'),
            ],
            turn_count=1,
        )
        d = state.model_dump()
        restored = ConversationState.model_validate(d)
        assert len(restored.history) == 2
        assert restored.history[0].role == 'user'
        assert restored.turn_count == 1

    def test_collected_data_with_premises(self):
        """CollectedData + PremiseData + IndicatorRecommendation."""
        collected = CollectedData(
            direction='bullish',
            target='삼성전자',
            thesis_type=['earnings', 'chain'],
            premises=[PremiseData(
                title='HBM3E 양산',
                recommended_indicators=[
                    IndicatorRecommendation(indicator_db_id=5, why='실적 추적', signal_type='leading'),
                ],
            )],
        )
        d = collected.model_dump()
        assert d['premises'][0]['recommended_indicators'][0]['indicator_db_id'] == 5
        assert d['premises'][0]['recommended_indicators'][0]['signal_type'] == 'leading'

    def test_enums(self):
        assert BuilderMode.LLM.value == 'llm'
        assert BuilderMode.WIZARD.value == 'wizard'
        assert BuilderPhase.PROPOSAL.value == 'proposal'
        assert BuilderPhase.PRESET.value == 'preset'
        assert BuilderPhase.CONFIRM.value == 'confirm'
        assert BuilderPhase.COMPLETE.value == 'complete'
        assert BuilderPhase.FALLBACK.value == 'fallback'
        assert FallbackReason.LLM_API_ERROR.value == 'llm_api_error'

    def test_valid_thesis_types(self):
        assert VALID_THESIS_TYPES == {'earnings', 'flow', 'macro', 'chain', 'event'}

    def test_monitoring_presets(self):
        assert len(MONITORING_PRESETS) == 3
        for key in ('short', 'medium', 'long'):
            preset = MONITORING_PRESETS[key]
            assert 'timeframe' in preset
            assert 'magnitude' in preset
            assert 'sensitivity' in preset
            assert 'label' in preset


# ──────────────────────────────────────────────
# prompt_builder.py 테스트
# ──────────────────────────────────────────────

class TestPromptBuilder:
    def test_build_base_instruction(self):
        text = build_base_instruction()
        assert '투자 가설 설계 전문가' in text
        assert 'One-shot Proposal' in text
        assert 'confidence' in text

    def test_build_type_guide_block(self):
        text = build_type_guide_block()
        for t in ('earnings', 'flow', 'macro', 'chain', 'event'):
            assert t in text

    def test_build_indicator_block(self):
        text = build_indicator_block()
        assert '(id:1)' in text
        assert '(id:11)' in text
        assert '시장 데이터' in text
        assert '거시경제' in text

    def test_build_system_prompt_with_indicators(self):
        flags = {'INDICATOR_CONTEXT_ENABLED': True}
        prompt = build_system_prompt(None, flags)
        assert 'id:' in prompt
        assert '투자 가설 설계 전문가' in prompt

    def test_build_system_prompt_without_indicators(self):
        flags = {'INDICATOR_CONTEXT_ENABLED': False}
        prompt = build_system_prompt(None, flags)
        assert 'id:' not in prompt

    def test_get_indicator_by_id(self):
        ind = get_indicator_by_id(8)
        assert ind is not None
        assert ind['name'] == 'VIX (공포지수)'
        assert get_indicator_by_id(999) is None

    def test_indicator_catalog_has_all_fields(self):
        for ind in INDICATOR_CATALOG:
            assert 'id' in ind
            assert 'name' in ind
            assert 'category' in ind
            assert 'data_source' in ind


# ──────────────────────────────────────────────
# llm_postprocess.py 테스트
# ──────────────────────────────────────────────

class TestLLMPostprocess:
    def test_normalize_thesis_type_str_to_list(self):
        raw = {'thesis_type': 'earnings+chain', 'premises': []}
        result = normalize_llm_output(raw)
        assert result['thesis_type'] == ['earnings', 'chain']

    def test_normalize_thesis_type_filters_invalid(self):
        raw = {'thesis_type': ['earnings', 'invalid', 'macro'], 'premises': []}
        result = normalize_llm_output(raw)
        assert result['thesis_type'] == ['earnings', 'macro']

    def test_normalize_dedup_premises(self):
        raw = {
            'thesis_type': [],
            'premises': [
                {'title': 'A', 'description': '1'},
                {'title': 'A', 'description': '2'},
                {'title': 'B', 'description': '3'},
            ],
        }
        result = normalize_llm_output(raw)
        assert len(result['premises']) == 2

    def test_normalize_direction_default(self):
        raw = {'direction': 'unknown', 'thesis_type': [], 'premises': []}
        result = normalize_llm_output(raw)
        assert result['direction'] == 'bearish'

    def test_validate_valid_output(self):
        raw = {
            'direction': 'bullish',
            'target': '삼성전자',
            'confidence': 'high',
            'premises': [{'title': 'Test'}],
        }
        _, warnings, errors = validate_llm_output(raw)
        assert not errors

    def test_validate_missing_direction(self):
        raw = {'direction': '', 'target': '삼성전자', 'confidence': 'high', 'premises': [{'title': 'Test'}]}
        _, _, errors = validate_llm_output(raw)
        assert any('direction' in e for e in errors)

    def test_validate_missing_target(self):
        raw = {'direction': 'bullish', 'target': '', 'confidence': 'high', 'premises': [{'title': 'Test'}]}
        _, _, errors = validate_llm_output(raw)
        assert any('target' in e for e in errors)

    def test_validate_low_confidence_skips_premise_check(self):
        """confidence=low일 때 premises 비어도 에러 아님."""
        raw = {'direction': 'bullish', 'target': 'X', 'confidence': 'low', 'premises': []}
        _, _, errors = validate_llm_output(raw)
        assert not errors

    def test_validate_truncates_over_5_premises(self):
        raw = {
            'direction': 'bullish', 'target': 'X', 'confidence': 'high',
            'premises': [{'title': f'P{i}'} for i in range(8)],
        }
        validated, warnings, _ = validate_llm_output(raw)
        assert len(validated['premises']) == 5
        assert any('5개로 축소' in w for w in warnings)

    def test_merge_to_collected(self):
        collected = CollectedData()
        validated = {
            'direction': 'bullish',
            'target': '삼성전자',
            'target_type': 'stock',
            'thesis_type': ['earnings'],
            'title': '삼성전자 반등',
            'premises': [
                {
                    'title': 'HBM3E',
                    'description': '양산 본격화',
                    'recommended_indicators': [
                        {'indicator_db_id': 5, 'why': '실적', 'signal_type': 'coincident'},
                    ],
                },
            ],
        }
        merged = merge_to_collected(collected, validated)
        assert merged.direction == 'bullish'
        assert merged.target == '삼성전자'
        assert merged.title == '삼성전자 반등'
        assert len(merged.premises) == 1
        assert merged.premises[0].title == 'HBM3E'
        assert merged.premises[0].recommended_indicators[0].indicator_db_id == 5


# ──────────────────────────────────────────────
# builder_events.py 테스트
# ──────────────────────────────────────────────

class TestBuilderEvents:
    def test_event_catalog_has_7_events(self):
        events = [
            EVENT_BUILDER_STARTED, EVENT_PROPOSAL_GENERATED,
            EVENT_LLM_PARSE_FAILED, EVENT_FALLBACK_TRIGGERED,
            EVENT_PRESET_SELECTED, EVENT_CONFIRM_CLICKED,
            EVENT_THESIS_CREATED,
        ]
        assert len(events) == 7
        assert all(isinstance(e, str) for e in events)

    @patch('thesis.services.builder_events.logger')
    def test_log_event_outputs_json(self, mock_logger):
        log_event('test_event', {'key': 'value'})
        mock_logger.info.assert_called_once()
        import json
        logged = json.loads(mock_logger.info.call_args[0][0])
        assert logged['event'] == 'test_event'
        assert logged['data']['key'] == 'value'
        assert 'timestamp' in logged


# ──────────────────────────────────────────────
# feature_flags.py 테스트
# ──────────────────────────────────────────────

class TestFeatureFlags:
    def test_get_feature_flags_returns_copy(self):
        flags = get_feature_flags()
        flags['LLM_BUILDER_ENABLED'] = False
        assert FEATURE_FLAGS['LLM_BUILDER_ENABLED'] is True

    def test_mvp_flags(self):
        flags = get_feature_flags()
        assert flags['LLM_BUILDER_ENABLED'] is True
        assert flags['INDICATOR_CONTEXT_ENABLED'] is True
        assert flags['KEYWORD_HINTS_ENABLED'] is False


# ──────────────────────────────────────────────
# thesis_builder.py LLM 함수 테스트
# ──────────────────────────────────────────────

class TestThesisBuilderLLM:
    def test_start_llm_conversation_free_input(self):
        from thesis.services.thesis_builder import start_llm_conversation
        result = start_llm_conversation('free_input')
        assert result['phase'] == 'proposal'
        assert result['conversation_state']['mode'] == 'llm'
        assert result['input_type'] == 'text'
        assert '아이디어' in result['message']

    def test_start_llm_conversation_news(self):
        from thesis.services.thesis_builder import start_llm_conversation
        with patch('thesis.services.thesis_builder._get_news_title', return_value='테스트 뉴스'):
            result = start_llm_conversation('news', source_news_id='fake-uuid')
        assert result['phase'] == 'proposal'
        assert '테스트 뉴스' in result['message']

    def test_detect_preset(self):
        from thesis.services.thesis_builder import _detect_preset
        assert _detect_preset('short') == 'short'
        assert _detect_preset('중기') == 'medium'
        assert _detect_preset('long') == 'long'
        assert _detect_preset('random text') is None

    def test_is_confirm_intent(self):
        from thesis.services.thesis_builder import _is_confirm_intent
        for word in ('confirm', '등록', '좋아', '네', '예', 'yes', 'ok'):
            assert _is_confirm_intent(word), f'{word} should be confirm'
        assert not _is_confirm_intent('아니요')

    def test_is_restart_intent(self):
        from thesis.services.thesis_builder import _is_restart_intent
        for word in ('restart', '다시', '다시 만들기', '처음부터'):
            assert _is_restart_intent(word), f'{word} should be restart'
        assert not _is_restart_intent('확인')

    def test_fallback_to_wizard(self):
        from thesis.services.thesis_builder import _fallback_to_wizard
        state = ConversationState(conv_id='test-123')
        result = _fallback_to_wizard(state, 'input', FallbackReason.LLM_API_ERROR)
        assert result['phase'] == 'fallback'
        assert result['fallback_reason'] == 'llm_api_error'
        # LLM state 유지 (retry 가능하도록)
        cs = result['conversation_state']
        assert cs['mode'] == 'llm'
        assert cs['phase'] == 'fallback'

    @patch('thesis.services.prompt_builder.call_gemini')
    def test_handle_proposal_gemini_failure_triggers_fallback(self, mock_gemini):
        """Gemini 호출 실패 → fallback."""
        from thesis.services.thesis_builder import _handle_proposal
        mock_gemini.return_value = None
        state = ConversationState(
            conv_id='test-123',
            history=[ChatMessage(role='user', content='삼성전자 반등')],
        )
        result = _handle_proposal(state, '삼성전자 반등')
        assert result['phase'] == 'fallback'
        assert result['fallback_reason'] == 'llm_api_error'

    @patch('thesis.services.prompt_builder.call_gemini')
    @patch('thesis.services.indicator_matcher.match_indicators_for_llm')
    def test_handle_proposal_success_moves_to_preset(self, mock_match, mock_gemini):
        """정상 Gemini 응답 → PRESET phase 전이."""
        mock_gemini.return_value = {
            'direction': 'bullish',
            'target': '삼성전자',
            'target_type': 'stock',
            'thesis_type': ['earnings'],
            'confidence': 'high',
            'title': '삼성전자 반등',
            'message': '가설을 설계했어요.',
            'premises': [
                {'title': 'HBM3E', 'description': '양산', 'recommended_indicators': []},
            ],
        }
        mock_match.return_value = []

        from thesis.services.thesis_builder import _handle_proposal
        state = ConversationState(
            conv_id='test-123',
            history=[ChatMessage(role='user', content='삼성전자 반등')],
        )
        result = _handle_proposal(state, '삼성전자 반등')
        assert result['phase'] == 'preset'
        assert result['confidence'] == 'high'
        assert result['needs_preset'] is True
        assert len(result['buttons']) == 3  # short/medium/long

    @patch('thesis.services.prompt_builder.call_gemini')
    @patch('thesis.services.indicator_matcher.match_indicators_for_llm')
    def test_handle_proposal_low_confidence_stays_proposal(self, mock_match, mock_gemini):
        """Low confidence → PROPOSAL 유지."""
        mock_gemini.return_value = {
            'direction': 'bullish',
            'target': '',
            'target_type': 'index',
            'thesis_type': [],
            'confidence': 'low',
            'title': '',
            'message': '좀 더 구체적으로 알려주세요.',
            'premises': [],
        }
        mock_match.return_value = []

        from thesis.services.thesis_builder import _handle_proposal
        state = ConversationState(
            conv_id='test-123',
            history=[ChatMessage(role='user', content='주식')],
        )
        result = _handle_proposal(state, '주식')
        assert result['phase'] == 'proposal'
        assert result['confidence'] == 'low'

    def test_handle_preset_valid_selection(self):
        from thesis.services.thesis_builder import _handle_preset
        state = ConversationState(
            conv_id='test-123',
            phase=BuilderPhase.PRESET.value,
            collected=CollectedData(direction='bullish', target='삼성전자', title='삼성전자 반등'),
        )
        result = _handle_preset(state, 'medium')
        assert result['phase'] == 'confirm'
        assert '등록' in str(result['buttons'])

    def test_handle_preset_invalid_reprompts(self):
        from thesis.services.thesis_builder import _handle_preset
        state = ConversationState(conv_id='test-123', phase=BuilderPhase.PRESET.value)
        result = _handle_preset(state, 'invalid')
        assert result['phase'] == 'preset'
        assert result['needs_preset'] is True

    def test_process_llm_turn_state_validation_failure(self):
        """잘못된 state → fallback."""
        from thesis.services.thesis_builder import process_llm_turn
        result = process_llm_turn({'invalid': True}, 'test')
        assert result['phase'] == 'fallback'


# ──────────────────────────────────────────────
# indicator_matcher.py LLM 매칭 테스트
# ──────────────────────────────────────────────

class TestIndicatorMatcherLLM:
    def test_pk_match_success(self):
        from thesis.services.indicator_matcher import match_indicators_for_llm
        collected = CollectedData(
            direction='bullish', target='삼성전자',
            premises=[PremiseData(
                title='금리 인하',
                recommended_indicators=[
                    IndicatorRecommendation(indicator_db_id=6, why='기준금리', signal_type='leading'),
                ],
            )],
        )
        results = match_indicators_for_llm(collected)
        pk_results = [r for r in results if r['match_method'] == 'pk']
        assert len(pk_results) == 1
        assert pk_results[0]['indicator_name'] == '미국 기준금리 (Fed Funds Rate)'
        assert pk_results[0]['auto_matched'] is True

    def test_pk_match_failure_falls_back_to_text(self):
        from thesis.services.indicator_matcher import match_indicators_for_llm
        collected = CollectedData(
            direction='bullish', target='삼성전자',
            premises=[PremiseData(
                title='외국인 매수 전환',
                recommended_indicators=[
                    IndicatorRecommendation(indicator_db_id=999, why='없는 지표'),
                ],
            )],
        )
        results = match_indicators_for_llm(collected)
        text_results = [r for r in results if r['match_method'] == 'text']
        assert len(text_results) >= 1
        assert text_results[0]['auto_matched'] is False

    def test_dedup_across_premises(self):
        """같은 지표가 여러 전제에서 추천되면 중복 제거."""
        from thesis.services.indicator_matcher import match_indicators_for_llm
        collected = CollectedData(
            direction='bullish', target='X',
            premises=[
                PremiseData(title='P1', recommended_indicators=[
                    IndicatorRecommendation(indicator_db_id=8, why='VIX 1'),
                ]),
                PremiseData(title='P2', recommended_indicators=[
                    IndicatorRecommendation(indicator_db_id=8, why='VIX 2'),
                ]),
            ],
        )
        results = match_indicators_for_llm(collected)
        vix_results = [r for r in results if 'VIX' in r['indicator_name']]
        assert len(vix_results) == 1

    def test_empty_premises(self):
        from thesis.services.indicator_matcher import match_indicators_for_llm
        collected = CollectedData(direction='bullish', target='X')
        results = match_indicators_for_llm(collected)
        assert results == []


# ──────────────────────────────────────────────
# conversation_views.py 테스트
# ──────────────────────────────────────────────

class TestConversationViews:
    def test_detect_mode_llm(self):
        from thesis.views.conversation_views import _detect_mode
        assert _detect_mode({'mode': 'llm'}) == 'llm'

    def test_detect_mode_wizard(self):
        from thesis.views.conversation_views import _detect_mode
        assert _detect_mode({'step': 1}) == 'wizard'
        assert _detect_mode({}) == 'wizard'

    def test_sanitize_llm_state_removes_unknown_keys(self):
        from thesis.views.conversation_views import _sanitize_llm_state
        state = {
            'conv_id': 'x', 'entry_source': 'free_input', 'mode': 'llm',
            'phase': 'proposal', 'history': [], 'collected': {},
            'turn_count': 0, 'EVIL': 'injected',
        }
        result = _sanitize_llm_state(state)
        assert result is not None
        assert 'EVIL' not in result

    def test_sanitize_llm_state_rejects_non_llm_mode(self):
        from thesis.views.conversation_views import _sanitize_llm_state
        state = {'conv_id': 'x', 'entry_source': 'free_input', 'mode': 'wizard'}
        result = _sanitize_llm_state(state)
        assert result is None

    def test_sanitize_llm_state_rejects_invalid_entry_source(self):
        from thesis.views.conversation_views import _sanitize_llm_state
        state = {'conv_id': 'x', 'entry_source': 'EVIL', 'mode': 'llm'}
        result = _sanitize_llm_state(state)
        assert result is None

    def test_sanitize_llm_state_truncates_long_history(self):
        from thesis.views.conversation_views import _sanitize_llm_state, MAX_HISTORY_LENGTH
        state = {
            'conv_id': 'x', 'entry_source': 'free_input', 'mode': 'llm',
            'phase': 'proposal', 'turn_count': 0, 'collected': {},
            'history': [{'role': 'user', 'content': f'm{i}'} for i in range(30)],
        }
        result = _sanitize_llm_state(state)
        assert len(result['history']) == MAX_HISTORY_LENGTH

    def test_wizard_sanitize_still_works(self):
        from thesis.views.conversation_views import _sanitize_conversation_state
        state = {
            'conv_id': 'w-123', 'entry_source': 'free_input',
            'step': 1, 'collected': {'direction': 'bullish'},
        }
        result = _sanitize_conversation_state(state)
        assert result is not None
        assert result['collected']['direction'] == 'bullish'


# ──────────────────────────────────────────────
# Phase A-Hardening: normalize 보강 테스트
# ──────────────────────────────────────────────

class TestNormalizeHardening:
    def test_direction_korean_alias(self):
        """한국어 direction → 영어 변환."""
        from thesis.services.llm_postprocess import normalize_llm_output
        assert normalize_llm_output({'direction': '상승', 'premises': []})['direction'] == 'bullish'
        assert normalize_llm_output({'direction': '하락', 'premises': []})['direction'] == 'bearish'
        assert normalize_llm_output({'direction': 'BULLISH', 'premises': []})['direction'] == 'bullish'
        assert normalize_llm_output({'direction': 'Bear', 'premises': []})['direction'] == 'bearish'

    def test_direction_unknown_defaults_bearish(self):
        from thesis.services.llm_postprocess import normalize_llm_output
        assert normalize_llm_output({'direction': 'sideways', 'premises': []})['direction'] == 'bearish'

    def test_premise_title_whitespace_cleanup(self):
        from thesis.services.llm_postprocess import normalize_llm_output
        raw = {'direction': 'bullish', 'premises': [
            {'title': '  · 실적  개선  ', 'description': '  desc  '},
        ]}
        result = normalize_llm_output(raw)
        assert result['premises'][0]['title'] == '실적 개선'
        assert result['premises'][0]['description'] == 'desc'

    def test_premise_empty_title_removed(self):
        from thesis.services.llm_postprocess import normalize_llm_output
        raw = {'direction': 'bullish', 'premises': [
            {'title': '', 'description': 'no title'},
            {'title': '유효', 'description': 'ok'},
        ]}
        result = normalize_llm_output(raw)
        assert len(result['premises']) == 1
        assert result['premises'][0]['title'] == '유효'

    def test_indicator_db_id_nullified_if_not_in_catalog(self):
        from thesis.services.llm_postprocess import normalize_llm_output
        raw = {'direction': 'bullish', 'premises': [
            {'title': 'Test', 'recommended_indicators': [
                {'indicator_db_id': 999, 'why': 'test'},
                {'indicator_db_id': 8, 'why': 'VIX'},
            ]},
        ]}
        result = normalize_llm_output(raw)
        inds = result['premises'][0]['recommended_indicators']
        assert inds[0]['indicator_db_id'] is None  # 999 → None
        assert inds[1]['indicator_db_id'] == 8  # 유효 → 유지

    def test_confidence_normalization(self):
        from thesis.services.llm_postprocess import normalize_llm_output
        assert normalize_llm_output({'confidence': 'HIGH', 'premises': []})['confidence'] == 'high'
        assert normalize_llm_output({'confidence': 'unknown', 'premises': []})['confidence'] == 'medium'

    def test_non_dict_premise_skipped(self):
        from thesis.services.llm_postprocess import normalize_llm_output
        raw = {'direction': 'bullish', 'premises': ['not_a_dict', {'title': 'ok'}]}
        result = normalize_llm_output(raw)
        assert len(result['premises']) == 1


class TestValidateHardening:
    def test_direction_message_mismatch_warning(self):
        from thesis.services.llm_postprocess import validate_llm_output
        raw = {
            'direction': 'bullish', 'target': 'X', 'confidence': 'high',
            'message': '하락이 예상됩니다',
            'premises': [{'title': 'P1'}],
        }
        _, warnings, errors = validate_llm_output(raw)
        assert not errors
        assert any('불일치' in w for w in warnings)

    def test_no_mismatch_warning_when_aligned(self):
        from thesis.services.llm_postprocess import validate_llm_output
        raw = {
            'direction': 'bullish', 'target': 'X', 'confidence': 'high',
            'message': '상승이 기대됩니다',
            'premises': [{'title': 'P1'}],
        }
        _, warnings, _ = validate_llm_output(raw)
        assert not any('불일치' in w for w in warnings)

    def test_empty_indicator_premise_warning(self):
        from thesis.services.llm_postprocess import validate_llm_output
        raw = {
            'direction': 'bullish', 'target': 'X', 'confidence': 'high',
            'premises': [
                {'title': 'P1', 'recommended_indicators': []},
                {'title': 'P2', 'recommended_indicators': [{'indicator_db_id': 1, 'why': 'ok'}]},
            ],
        }
        _, warnings, _ = validate_llm_output(raw)
        assert any('P1' in w and '추천 지표 없음' in w for w in warnings)


# ──────────────────────────────────────────────
# Phase A-Hardening: fallback 안정화 테스트
# ──────────────────────────────────────────────

class TestFallbackStability:
    def test_fallback_retry_returns_to_proposal(self):
        """fallback → retry → proposal."""
        from thesis.services.thesis_builder import _handle_fallback_choice
        state = ConversationState(
            conv_id='test-fb',
            phase=BuilderPhase.FALLBACK.value,
            history=[
                ChatMessage(role='user', content='삼성전자 반등'),
                ChatMessage(role='user', content='retry'),
            ],
        )
        with patch('thesis.services.prompt_builder.call_gemini', return_value=None):
            result = _handle_fallback_choice(state, 'retry', None)
        # Gemini 실패 시 다시 fallback (retry의 retry)
        assert result['phase'] in ('fallback', 'proposal')

    def test_fallback_wizard_switches_mode(self):
        """fallback → wizard 선택 → wizard 시작."""
        from thesis.services.thesis_builder import _handle_fallback_choice
        state = ConversationState(
            conv_id='test-fb',
            phase=BuilderPhase.FALLBACK.value,
            entry_source='free_input',
        )
        result = _handle_fallback_choice(state, 'wizard', None)
        # wizard 모드로 전환: step 기반 응답
        cs = result.get('conversation_state', {})
        assert 'step' in cs

    def test_turn_count_overflow_triggers_fallback(self):
        """turn_count > 20 → fallback."""
        from thesis.services.thesis_builder import process_llm_turn
        state_dict = ConversationState(
            conv_id='test-overflow',
            turn_count=20,
        ).model_dump()
        result = process_llm_turn(state_dict, 'test')
        assert result['phase'] == 'fallback'

    def test_fallback_preserves_llm_state_for_retry(self):
        """fallback이 LLM state를 유지해서 retry 가능."""
        from thesis.services.thesis_builder import _fallback_to_wizard
        state = ConversationState(
            conv_id='test-preserve',
            history=[ChatMessage(role='user', content='원래 입력')],
            turn_count=1,
        )
        result = _fallback_to_wizard(state, 'input', FallbackReason.LLM_API_ERROR)
        cs = result['conversation_state']
        assert cs.get('mode') == 'llm'
        assert cs.get('phase') == 'fallback'
        assert len(cs.get('history', [])) >= 1

    def test_process_llm_turn_handles_fallback_phase(self):
        """process_llm_turn이 fallback phase를 처리."""
        from thesis.services.thesis_builder import process_llm_turn
        state_dict = ConversationState(
            conv_id='test-fb-phase',
            phase=BuilderPhase.FALLBACK.value,
            entry_source='free_input',
        ).model_dump()
        result = process_llm_turn(state_dict, 'wizard')
        # wizard 전환 또는 재시도 응답
        assert 'conversation_state' in result
