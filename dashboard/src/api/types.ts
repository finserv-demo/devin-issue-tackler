export interface MetricCard {
  label: string
  value: string
  subtitle: string
  sentiment: 'positive' | 'negative' | 'neutral'
}

export interface DashboardMetrics {
  time_window_days: number
  issues_resolved: MetricCard
  median_resolution_time: MetricCard
  resolved_within_one_week: MetricCard
}

export interface IssueItem {
  number: number
  title: string
  html_url: string
  status_label: string
  sizing_label: string | null
  time_in_state: string
  pr_url: string | null
  created_at: string
}

export interface DashboardLists {
  needs_attention: IssueItem[]
  in_progress: IssueItem[]
}
