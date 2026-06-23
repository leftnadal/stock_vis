import EventRanking from '@/components/chainsight/EventRanking';

interface Props {
  params: Promise<{ theme: string }>;
}

export default async function EventRankingPage({ params }: Props) {
  const { theme } = await params;
  // ⓑ 인코딩 정합: EventBoard가 encodeURIComponent로 push → 여기서 단일 디코딩.
  // decodeURIComponent는 멱등(% 없으면 no-op)이라 Next 자동디코딩 여부와 무관하게 안전.
  // 그룹명(섹터·테마)은 literal '%'를 포함하지 않음.
  const decodedTheme = decodeURIComponent(theme);
  return <EventRanking theme={decodedTheme} />;
}
