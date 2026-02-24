'use client';

import {
  Swords,
  Factory,
  Newspaper,
  Crown,
  Link,
  Brain,
  BatteryCharging,
  CreditCard,
  Cloud,
  Dna,
  BarChart3,
  Cpu,
  Rocket,
  Bot,
  Sun,
  ShieldCheck,
  ShieldAlert,
  Leaf,
  Globe,
  Gamepad2,
  Wrench,
  ShoppingCart,
  Users,
  Scale,
  type LucideIcon,
} from 'lucide-react';

const ICON_MAP: Record<string, LucideIcon> = {
  swords: Swords,
  factory: Factory,
  newspaper: Newspaper,
  crown: Crown,
  link: Link,
  brain: Brain,
  'battery-charging': BatteryCharging,
  'credit-card': CreditCard,
  cloud: Cloud,
  dna: Dna,
  'bar-chart-3': BarChart3,
  cpu: Cpu,
  rocket: Rocket,
  bot: Bot,
  sun: Sun,
  'shield-check': ShieldCheck,
  leaf: Leaf,
  globe: Globe,
  'gamepad-2': Gamepad2,
  wrench: Wrench,
  'shopping-cart': ShoppingCart,
  users: Users,
  scale: Scale,
  'shield-alert': ShieldAlert,
};

interface CategoryIconProps {
  name: string;
  className?: string;
}

/**
 * 카테고리 아이콘 컴포넌트
 *
 * 백엔드에서 전달된 lucide 아이콘명을 실제 아이콘으로 렌더링합니다.
 */
export default function CategoryIcon({ name, className = 'h-4 w-4' }: CategoryIconProps) {
  const IconComponent = ICON_MAP[name] || BarChart3;
  return <IconComponent className={className} />;
}
