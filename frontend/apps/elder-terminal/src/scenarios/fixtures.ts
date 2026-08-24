import {
  makeAgentResponse,
  makeAlert,
  makeCareEvent,
  makeCareTask,
  makeContextSnapshot,
  makeDashboard,
  makeSourceRef,
} from '@carehub/shared-contracts';
import type {
  AgentResponseV1,
  AlertViewV1,
  CareEventV1,
  CareTaskV1,
  ContextSnapshotV1,
  DashboardViewV1,
} from '@carehub/shared-contracts';

/** 演示用的合成主体 ID（虚构，非真实身份）。 */
export const DEMO_SUBJECT_ID = 'subject-sim-001';

export function fixtureMedicationTask(): CareTaskV1 {
  return makeCareTask({
    kind: 'MEDICATION',
    status: 'DUE',
    evidence_state: 'UNKNOWN',
  });
}

export function fixtureTasks(): CareTaskV1[] {
  return [
    fixtureMedicationTask(),
    makeCareTask({ kind: 'ACTIVITY_REVIEW', status: 'UNKNOWN', evidence_state: 'UNKNOWN' }),
  ];
}

export function fixtureDashboard(): DashboardViewV1 {
  return makeDashboard({
    welcome: '您好，今天最重要的一件事是按时服药。',
    primaryTask: fixtureMedicationTask(),
    nextAction: '点击查看任务详情',
    safetyStatus: 'NONE',
  });
}

export function fixtureSmokeGasAlert(): AlertViewV1 {
  return makeAlert({ kind: 'SMOKE_GAS', safety_level: 'S0', status: 'ACTIVE' });
}

export function fixtureSosAlert(): AlertViewV1 {
  return makeAlert({ kind: 'SOS', safety_level: 'S-1', status: 'ACTIVE' });
}

/** 安全告警：S-1（SOS）与 S0（烟雾/燃气）均为不可忽略事件。 */
export function fixtureAlerts(): AlertViewV1[] {
  return [fixtureSmokeGasAlert(), fixtureSosAlert()];
}

export function fixtureAgentResponse(): AgentResponseV1 {
  return makeAgentResponse({
    message: '今日提醒已整理完毕。',
    facts: [
      {
        statement: '上午的服药提醒已由系统生成。',
        source_refs: [makeSourceRef({ label: 'CareDose 合成事件' })],
        confidence: 'VALID',
      },
    ],
    fallback: false,
  });
}

export function fixtureAgentFallback(): AgentResponseV1 {
  return makeAgentResponse({
    message: '助手暂时无法给出解释，请稍后再试或联系家属。',
    facts: [],
    fallback: true,
    reasonCode: 'AGENT_FALLBACK',
  });
}

/**
 * 无来源事实：类型层面是合法 AgentResponseV1，但事实的 source_refs 为空，
 * 运行时 guard（isAgentFact 要求 source_refs.length > 0）会拒绝它。
 * 客户端必须显示模板失败态，绝不可渲染其中的原始模型文本。
 */
export function fixtureAgentNoSource(): AgentResponseV1 {
  return {
    message: '原始模型文本：已按医嘱服药（未经验证，不应被渲染）。',
    facts: [{ statement: '已按医嘱服药。', source_refs: [], confidence: 'VALID' }],
    source_refs: [],
    fallback: false,
  };
}

export function fixtureLowQualityEvent(): CareEventV1 {
  return makeCareEvent({
    event_type: 'LOW_QUALITY_ACTIVITY',
    quality: { status: 'LOW', reason: '活动数据不足，暂未确认' },
  });
}

export function fixtureMedicationDueEvent(): CareEventV1 {
  return makeCareEvent({
    event_type: 'MEDICATION_DUE',
    quality: { status: 'VALID' },
  });
}

export function fixtureConflictEvent(): CareEventV1 {
  return makeCareEvent({
    event_type: 'MEDICATION_DUE',
    quality: { status: 'CONFLICT', reason: '多来源时间不一致' },
  });
}

/** 时间线：模拟 CareDose（MEDICATION_DUE）与 CareRadar（LOW/CONFLICT）事件。 */
export function fixtureTimeline(): CareEventV1[] {
  return [
    fixtureMedicationDueEvent(),
    fixtureLowQualityEvent(),
    fixtureConflictEvent(),
  ];
}

export function fixtureContextSnapshot(): ContextSnapshotV1 {
  return makeContextSnapshot({
    purpose: 'dashboard',
    facts: [{ key: '今日任务数', value: '1', confidence: 'VALID' }],
    unknowns: [{ key: '活动质量', note: '雷达数据不足，暂未确认' }],
    freshness: 'FRESH',
  });
}
