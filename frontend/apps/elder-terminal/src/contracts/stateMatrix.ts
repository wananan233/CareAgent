/** 页面可展示的状态（用于状态矩阵与“不得用空白/0 冒充”校验）。 */
export type DisplayState =
  | 'READY'
  | 'ONLINE'
  | 'OFFLINE'
  | 'STALE'
  | 'DENIED'
  | 'FAILED'
  | 'UNKNOWN'
  | 'CONFLICT'
  | 'FALLBACK'
  | 'ACTIVE'
  | 'ACKNOWLEDGED'
  | 'RESOLVED';

export interface PageStateRule {
  route: string;
  label: string;
  states: DisplayState[];
  forbidden: string;
}

/** 页面状态矩阵（契约冻结，U0 证据之一）。 */
export const PAGE_STATE_MATRIX: PageStateRule[] = [
  {
    route: '/home',
    label: '今日',
    states: ['READY', 'UNKNOWN', 'STALE', 'OFFLINE', 'FAILED'],
    forbidden: '同时堆满多个任务；隐藏安全状态',
  },
  {
    route: '/task/:id',
    label: '任务详情',
    states: ['READY', 'UNKNOWN', 'STALE', 'OFFLINE', 'DENIED', 'FAILED'],
    forbidden: '把 UNKNOWN 显示为已完成；改药/剂量',
  },
  {
    route: '/safety',
    label: '安全提示',
    states: ['READY', 'ACTIVE', 'ACKNOWLEDGED', 'OFFLINE', 'FAILED'],
    forbidden: '关闭/降级 S-1/S0 告警；调用急救',
  },
  {
    route: '/agent',
    label: '小护',
    states: ['READY', 'FALLBACK', 'OFFLINE', 'DENIED', 'FAILED'],
    forbidden: '拟人化依赖话术；无来源断言',
  },
  {
    route: '/timeline',
    label: '时间线',
    states: ['READY', 'UNKNOWN', 'CONFLICT', 'STALE', 'OFFLINE', 'FAILED'],
    forbidden: '展示原始敏感 payload 或其它用户数据',
  },
  {
    route: '/settings',
    label: '设置',
    states: ['READY', 'OFFLINE'],
    forbidden: '修改安全规则、药物计划、权限绕过',
  },
  {
    route: '/system',
    label: '系统状态',
    states: ['ONLINE', 'OFFLINE', 'STALE', 'FAILED'],
    forbidden: '将陈旧缓存标作实时状态',
  },
];
