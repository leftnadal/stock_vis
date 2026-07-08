# components/thesis/_reuse — FE 재사용 부품 격리소 (P1 철거 잔존)

> Monitor 허브 재건(ADR `D-MONITOR-REBUILD`, 2026-07-08)에서 신축에 이식할 FE 부품 보존.
> 폐기 대상 thesis 라우트/전용 컴포넌트와 분리. **import 경로가 신축 시 바뀔 수 있음(참조용).**

| 부품 | 역할 |
|------|------|
| `MoonPhase.tsx` | overall_score(-1~1) → 달 위상 밝기 시각화 |
| `ArrowIndicator.tsx` | score → 화살표 방향(0~180°)+색 시각화 |
| `builder/` | 대화형 빌더 골격 (ChatBubble·PremiseCard·SuggestionCard·NewsSelector·OptionButton·MultiSelectFooter·ProgressBar·TextInput·BottomSheet) |

## 수명
- **P3**: Monitor 빌더 4단계 + IA-2 페이지 신축 시 이 골격을 꺼내 재사용.
- **P3 완료 시**: 이 폴더 **삭제**.
