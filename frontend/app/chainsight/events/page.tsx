import { redirect } from 'next/navigation';

// RD3 역전(2026-06-18): 이벤트 보드는 루트 /chainsight로 승격.
// 기존 /chainsight/events 인덱스는 중복 보드 URL이므로 루트로 영구 이전.
// 그룹 상세(/chainsight/events/[theme])는 유지.
export default function EventBoardIndexPage() {
  redirect('/chainsight');
}
