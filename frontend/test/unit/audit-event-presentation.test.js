import { describe, expect, it } from 'vitest';
import {
  auditActionLabel,
  auditActionDescription,
  auditActorTypeLabel,
  auditOutcomeLabel,
  auditPhaseLabel,
  auditRequesterLabel,
  auditSummaryEntries,
  formatAuditOccurredAt,
  hasAuditValue,
} from '@/utils/audit-event-display.js';

describe('统一操作审计展示', () => {
  it('formats ISO timestamps without fractional seconds', () => {
    expect(formatAuditOccurredAt('2026-07-20T20:33:32.932602')).toBe('2026-07-20 20:33:32');
  });

  it('shows the API requester when one was retained and identifies scheduled work otherwise', () => {
    expect(auditRequesterLabel({
      actor_type: 'user',
      actor: { display_name: '郭建鹏' },
    })).toBe('郭建鹏');
    expect(auditRequesterLabel({ actor_type: 'service' })).toBe('系统定时任务');
  });

  it('uses readable collection labels and result summaries', () => {
    expect(auditActionLabel('storage.collection.run')).toBe('存储采集');
    expect(auditPhaseLabel('result')).toBe('执行结果');
    expect(auditSummaryEntries({ storage_usage_count: 12, group_count: 3 })).toEqual([
      { label: '更新用户目录', value: '12' },
      { label: '更新项目组', value: '3' },
    ]);
  });

  it('formats actor, action, outcome, and retained values consistently', () => {
    expect(auditActorTypeLabel('ai_tool')).toBe('AI 工具');
    expect(auditActionDescription('storage.collection.run')).toBe('存储采集（storage.collection.run）');
    expect(auditOutcomeLabel('denied')).toBe('已拒绝');
    expect(hasAuditValue({ status_code: 200 })).toBe(true);
    expect(hasAuditValue([])).toBe(false);
  });
});
