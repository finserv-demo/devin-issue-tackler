import { useState } from 'react'
import { useMetrics, useLists } from './api/hooks'
import type { MetricCard as MetricCardType, IssueItem } from './api/types'

// ── Sizing badge colors ──

const SIZING_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  'devin:green': { bg: 'bg-emerald-100', text: 'text-emerald-800', label: 'Green' },
  'devin:yellow': { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Yellow' },
  'devin:red': { bg: 'bg-red-100', text: 'text-red-800', label: 'Red' },
}

const STATUS_DISPLAY: Record<string, { bg: string; text: string; label: string }> = {
  'devin:triaged': { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Awaiting Input' },
  'devin:pr-in-progress': { bg: 'bg-orange-100', text: 'text-orange-800', label: 'PR In Progress' },
  'devin:pr-ready': { bg: 'bg-purple-100', text: 'text-purple-800', label: 'PR Ready' },
  'devin:escalated': { bg: 'bg-red-100', text: 'text-red-800', label: 'Escalated' },
  'devin:triage': { bg: 'bg-sky-100', text: 'text-sky-800', label: 'Triaging' },
  'devin:implement': { bg: 'bg-violet-100', text: 'text-violet-800', label: 'Implementing' },
}

// ── Components ──

function HeroMetricCard({ metric, accent }: { metric: MetricCardType; accent?: boolean }) {
  const sentimentColor =
    metric.sentiment === 'positive'
      ? 'text-emerald-600'
      : metric.sentiment === 'negative'
        ? 'text-red-600'
        : 'text-gray-500'

  return (
    <div
      className={`rounded-xl border p-5 ${
        accent ? 'border-emerald-200 bg-emerald-50' : 'border-gray-200 bg-white'
      }`}
    >
      <p className="text-sm font-medium text-gray-500">{metric.label}</p>
      <p className="mt-1 text-3xl font-bold tracking-tight text-gray-900">
        {metric.value}
      </p>
      {metric.subtitle && (
        <p className={`mt-1 text-sm font-medium ${sentimentColor}`}>
          {metric.subtitle}
        </p>
      )}
    </div>
  )
}

function SizingBadge({ label }: { label: string | null }) {
  if (!label) return null
  const style = SIZING_COLORS[label]
  if (!style) return null
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  )
}

function StatusBadge({ label }: { label: string }) {
  const style = STATUS_DISPLAY[label]
  if (!style) return null
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  )
}

const CI_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  passing: { bg: 'bg-emerald-100', text: 'text-emerald-800', label: 'CI Passing' },
  failing: { bg: 'bg-red-100', text: 'text-red-800', label: 'CI Failing' },
  pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'CI Pending' },
}

function CIBadge({ status }: { status: string | null }) {
  if (!status) return null
  const style = CI_STYLES[status]
  if (!style) return null
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  )
}

function ReviewThreadCount({ count }: { count: number | null }) {
  if (count === null || count === undefined) return null
  if (count === 0) return null
  return (
    <span className="inline-flex items-center rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">
      {count} unresolved {count === 1 ? 'thread' : 'threads'}
    </span>
  )
}

function IssueRow({ issue }: { issue: IssueItem }) {
  const isPrStage = issue.status_label === 'devin:pr-in-progress' || issue.status_label === 'devin:pr-ready'

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-3 transition-colors hover:border-gray-300 hover:bg-gray-50">
      <div className="flex items-center gap-3">
        <a
          href={issue.html_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex min-w-0 flex-1 items-center gap-3"
        >
          <span className="shrink-0 font-mono text-sm text-gray-400">#{issue.number}</span>
          <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-900">
            {issue.title}
          </span>
        </a>
        <div className="flex shrink-0 items-center gap-2">
          <SizingBadge label={issue.sizing_label} />
          <StatusBadge label={issue.status_label} />
          {isPrStage && <CIBadge status={issue.ci_status} />}
          {isPrStage && <ReviewThreadCount count={issue.unresolved_review_threads} />}
          {issue.time_in_state && (
            <span className="text-xs text-gray-400">{issue.time_in_state}</span>
          )}
        </div>
      </div>
      {isPrStage && issue.pr_url && (
        <div className="mt-1 pl-9">
          <a
            href={issue.pr_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:text-blue-800 hover:underline"
          >
            View PR
          </a>
        </div>
      )}
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-gray-300 py-8 text-center">
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  )
}

// ── Main App ──

function App() {
  const [days, setDays] = useState(7)
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useMetrics(days)
  const { data: lists, isLoading: listsLoading, error: listsError } = useLists()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Issue Tackler</h1>
            <p className="text-sm text-gray-500">Devin automation dashboard</p>
          </div>
          <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-1">
            <button
              onClick={() => setDays(7)}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                days === 7
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              7 days
            </button>
            <button
              onClick={() => setDays(30)}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                days === 30
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              30 days
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-6">
        {/* Hero Metrics */}
        <section>
          {metricsLoading && (
            <div className="grid grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-28 animate-pulse rounded-xl border border-gray-200 bg-gray-100" />
              ))}
            </div>
          )}
          {metricsError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              Failed to load metrics. Is the backend running?
            </div>
          )}
          {metrics && (
            <div className="grid grid-cols-3 gap-4">
              <HeroMetricCard metric={metrics.issues_resolved} accent />
              <HeroMetricCard metric={metrics.median_resolution_time} />
              <HeroMetricCard metric={metrics.resolved_within_one_week} />
            </div>
          )}
        </section>

        {/* Lists */}
        <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
          {/* Needs Attention */}
          <section>
            <div className="mb-3 flex items-center gap-2">
              <h2 className="text-base font-semibold text-gray-900">Needs Attention</h2>
              {lists && lists.needs_attention.length > 0 && (
                <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-100 px-1.5 text-xs font-medium text-amber-800">
                  {lists.needs_attention.length}
                </span>
              )}
            </div>
            {listsLoading && (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-14 animate-pulse rounded-lg border border-gray-200 bg-gray-100" />
                ))}
              </div>
            )}
            {listsError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                Failed to load issues.
              </div>
            )}
            {lists && lists.needs_attention.length === 0 && (
              <EmptyState message="Nothing needs your attention right now." />
            )}
            {lists && lists.needs_attention.length > 0 && (
              <div className="space-y-2">
                {lists.needs_attention.map((issue) => (
                  <IssueRow key={issue.number} issue={issue} />
                ))}
              </div>
            )}
          </section>

          {/* In Progress */}
          <section>
            <div className="mb-3 flex items-center gap-2">
              <h2 className="text-base font-semibold text-gray-900">In Progress</h2>
              {lists && lists.in_progress.length > 0 && (
                <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-sky-100 px-1.5 text-xs font-medium text-sky-800">
                  {lists.in_progress.length}
                </span>
              )}
            </div>
            {listsLoading && (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-14 animate-pulse rounded-lg border border-gray-200 bg-gray-100" />
                ))}
              </div>
            )}
            {listsError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                Failed to load issues.
              </div>
            )}
            {lists && lists.in_progress.length === 0 && (
              <EmptyState message="No issues being worked on right now." />
            )}
            {lists && lists.in_progress.length > 0 && (
              <div className="space-y-2">
                {lists.in_progress.map((issue) => (
                  <IssueRow key={issue.number} issue={issue} />
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}

export default App
