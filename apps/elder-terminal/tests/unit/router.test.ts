import { describe, expect, it } from 'vitest';
import { routes } from '@/router';

const PAGE_PATHS = [
  '/home',
  '/task/:id',
  '/safety',
  '/agent',
  '/timeline',
  '/settings',
  '/system',
];

describe('路由清单（契约冻结）', () => {
  it('包含 7 个页面路由 + 根重定向 + 兜底', () => {
    const paths = routes.map((r) => r.path);
    for (const p of PAGE_PATHS) {
      expect(paths).toContain(p);
    }
    expect(paths).toContain('/:pathMatch(.*)*');

    const root = routes.find((r) => r.path === '/');
    expect(root?.redirect).toBe('/home');
  });

  it('每个页面路由都绑定组件并带标题 meta', () => {
    const pageRoutes = routes.filter(
      (r) => r.path !== '/' && r.path !== '/:pathMatch(.*)*',
    );
    for (const r of pageRoutes) {
      expect(r.component).toBeDefined();
      expect(r.meta?.title).toBeTruthy();
    }
  });
});
