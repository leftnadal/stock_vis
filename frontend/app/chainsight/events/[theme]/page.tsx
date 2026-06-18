import EventRanking from '@/components/chainsight/EventRanking';

interface Props {
  params: Promise<{ theme: string }>;
}

export default async function EventRankingPage({ params }: Props) {
  const { theme } = await params;
  return <EventRanking theme={theme} />;
}
