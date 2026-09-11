import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { DashboardTabs } from '@/components/eod/DashboardTabs';

describe('DashboardTabs', () => {
  it('[발견][시장] 두 탭을 렌더한다', () => {
    render(<DashboardTabs activeTab="discover" onTabChange={() => {}} />);
    expect(screen.getByRole('tab', { name: '발견' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '시장' })).toBeInTheDocument();
  });

  it('activeTab이 aria-selected로 표시된다', () => {
    render(<DashboardTabs activeTab="market" onTabChange={() => {}} />);
    expect(screen.getByRole('tab', { name: '시장' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: '발견' })).toHaveAttribute('aria-selected', 'false');
  });

  it('탭 클릭 시 onTabChange가 해당 id로 호출된다', () => {
    const onTabChange = vi.fn();
    render(<DashboardTabs activeTab="discover" onTabChange={onTabChange} />);
    fireEvent.click(screen.getByRole('tab', { name: '시장' }));
    expect(onTabChange).toHaveBeenCalledWith('market');
  });

  it('우측 슬롯(children)을 렌더한다', () => {
    render(
      <DashboardTabs activeTab="discover" onTabChange={() => {}}>
        <span>신선도배지</span>
      </DashboardTabs>
    );
    expect(screen.getByText('신선도배지')).toBeInTheDocument();
  });

  it('children 미지정 시에도 탭 줄은 렌더된다', () => {
    render(<DashboardTabs activeTab="discover" onTabChange={() => {}} />);
    expect(screen.getByRole('tablist')).toBeInTheDocument();
  });
});
