/**
 * 适老 UI 设计 token（任务书 3.1 的 P0 标准）。以常量形式冻结，供测试断言：
 * 正文 >= 20px、主要任务 >= 30px、数字时间 >= 28px、主要按钮 >= 56x56px。
 */
export const tokens = {
  fontSize: {
    body: 24,
    main: 32,
    time: 28,
    caption: 20,
  },
  touch: {
    minTarget: 56,
  },
  color: {
    textPrimary: '#1a1a1a',
    textOnDark: '#ffffff',
    background: '#f7f5f0',
    surface: '#ffffff',
    brand: '#0b3d2e',
    danger: '#b3261e',
    warning: '#8a5a00',
    info: '#1f4e79',
    focusRing: '#f0a500',
  },
  spacing: {
    xs: 8,
    sm: 16,
    md: 24,
    lg: 32,
  },
  radius: {
    md: 12,
    lg: 16,
  },
} as const;

export type DesignTokens = typeof tokens;
