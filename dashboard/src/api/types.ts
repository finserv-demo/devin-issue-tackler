/** TypeScript types matching the backend API schemas. */

export interface TimelineEntry {
  type: 'comment' | 'state_change' | 'session_event' | 'label'
  timestamp: string
  actor: string
  body: string
  from_state: string | null
  to_state: string | null
  label: string | null
  session_url: string | null
}

export interface SessionSummary {
  session_id: string
  stage: string
  status: string
  session_url: string
  acus_consumed: number
  created_at: string
}

export interface IssueSummary {
  number: number
  title: string
  state: string
  status: string
  sizing: string | null
  labels: string[]
  created_at: string
  updated_at: string
  time_in_state: string
  html_url: string
  pr_url: string | null
  needs_attention: boolean
  attention_reason: string | null
}

export interface IssueDetail {
  number: number
  title: string
  body: string | null
  state: string
  status: string
  sizing: string | null
  labels: string[]
  created_at: string
  updated_at: string
  html_url: string
  pr_url: string | null
  pr_number: number | null
  needs_attention: boolean
  attention_reason: string | null
  next_steps: string
  timeline: TimelineEntry[]
  sessions: SessionSummary[]
  available_actions: string[]
}

export interface CommandResponse {
  success: boolean
  message: string
}

export interface PipelineCount {
  state: string
  count: number
  color: string
  label: string
  github_filter_url: string
}

export interface ThroughputPoint {
  period: string
  resolved: number
  opened: number
}

export interface ResolutionTimeStats {
  median_hours: number
  mean_hours: number
  p90_hours: number
  total_resolved: number
}

export interface AcuSpendEntry {
  sizing: string
  avg_acus: number
  total_acus: number
  issue_count: number
}

export interface MetricsSummary {
  pipeline: PipelineCount[]
  throughput: ThroughputPoint[]
  resolution_time: ResolutionTimeStats | null
  acu_spend: AcuSpendEntry[]
  success_rate: number
  total_processed: number
  total_done: number
  total_escalated: number
}

export interface SettingsData {
  opt_out_label: string
  acu_limit_triage: number
  acu_limit_implement: number
  max_concurrent_implement: number
  max_concurrent_total: number
  polling_interval_seconds: number
  bulk_triage_rate_limit: number
  target_repo: string
}

export interface SettingsUpdate {
  opt_out_label?: string
  acu_limit_triage?: number
  acu_limit_implement?: number
  max_concurrent_implement?: number
  max_concurrent_total?: number
  polling_interval_seconds?: number
  bulk_triage_rate_limit?: number
}

/** Pipeline status display configuration.
 * Colors reflect progression: cool (early) → warm (late).
 * Escalated = red, skipped = gray, done = green (terminal).
 */
export const STATUS_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
  new: { label: 'New', color: '#6b7280', bgColor: '#f3f4f6' },
  triage: { label: 'Triaging', color: '#3b82f6', bgColor: '#dbeafe' },
  triaged: { label: 'Triaged', color: '#0ea5e9', bgColor: '#e0f2fe' },
  implement: { label: 'Implementing', color: '#6366f1', bgColor: '#eef2ff' },
  'pr-opened': { label: 'PR Open', color: '#f59e0b', bgColor: '#fef3c7' },
  done: { label: 'Done', color: '#16a34a', bgColor: '#dcfce7' },
  escalated: { label: 'Escalated', color: '#dc2626', bgColor: '#fee2e2' },
  skipped: { label: 'Skipped', color: '#9ca3af', bgColor: '#f3f4f6' },
}

export const SIZING_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
  green: { label: 'S', color: '#16a34a', bgColor: '#dcfce7' },
  yellow: { label: 'M', color: '#b45309', bgColor: '#fef3c7' },
  red: { label: 'L', color: '#dc2626', bgColor: '#fee2e2' },
}
