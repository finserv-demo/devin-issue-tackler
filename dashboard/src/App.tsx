import { useState, useEffect } from 'react'
import { useMetrics, useLists } from './api/hooks'
import type { MetricCard as MetricCardType, IssueItem } from './api/types'

const PAGE_SIZE = 5

// ── Filter/sort types ──

type SizeFilterValue = 'all' | 'S' | 'M' | 'L'
type SortDirection = 'none' | 'asc' | 'desc'

const SIZE_ORDER: Record<string, number> = {
  'devin:small': 1,
  'devin:medium': 2,
  'devin:large': 3,
}

const STATUS_ORDER: Record<string, number> = {
  'devin:escalated': 0,
  'devin:pr-ready': 1,
  'devin:triaged': 2,
  'devin:triage': 0,
  'devin:implement': 1,
  'devin:pr-in-progress': 2,
}

const ATTENTION_STATUSES = [
  { value: 'devin:escalated', label: 'Escalated' },
  { value: 'devin:pr-ready', label: 'PR Ready' },
  { value: 'devin:triaged', label: 'Awaiting Input' },
] as const

const PROGRESS_STATUSES = [
  { value: 'devin:triage', label: 'Triaging' },
  { value: 'devin:implement', label: 'Implementing' },
  { value: 'devin:pr-in-progress', label: 'PR In Progress' },
] as const

function applyFiltersAndSorts(
  items: IssueItem[],
  sizeFilter: SizeFilterValue,
  sizeSort: SortDirection,
  statusFilter: string,
  statusSort: SortDirection,
): IssueItem[] {
  const SIZE_FILTER_TO_LABEL: Record<string, string> = {
    S: 'devin:small',
    M: 'devin:medium',
    L: 'devin:large',
  }
  let result = items
  if (sizeFilter !== 'all') {
    const target = SIZE_FILTER_TO_LABEL[sizeFilter]
    result = result.filter((i) => i.sizing_label === target)
  }
  if (statusFilter !== 'all') {
    result = result.filter((i) => i.status_label === statusFilter)
  }
  // Apply sorts — status sort first (primary), then size sort (secondary) if both active
  if (sizeSort !== 'none' || statusSort !== 'none') {
    result = [...result].sort((a, b) => {
      if (statusSort !== 'none') {
        const aStatus = STATUS_ORDER[a.status_label] ?? 99
        const bStatus = STATUS_ORDER[b.status_label] ?? 99
        const statusCmp = statusSort === 'asc' ? aStatus - bStatus : bStatus - aStatus
        if (statusCmp !== 0) return statusCmp
      }
      if (sizeSort !== 'none') {
        const aSize = a.sizing_label ? (SIZE_ORDER[a.sizing_label] ?? 99) : 99
        const bSize = b.sizing_label ? (SIZE_ORDER[b.sizing_label] ?? 99) : 99
        return sizeSort === 'asc' ? aSize - bSize : bSize - aSize
      }
      return 0
    })
  }
  return result
}

// ── Sizing badge colors ──

const SIZING_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  'devin:small': { bg: 'bg-emerald-100', text: 'text-emerald-800', label: 'S' },
  'devin:medium': { bg: 'bg-amber-100', text: 'text-amber-800', label: 'M' },
  'devin:large': { bg: 'bg-red-100', text: 'text-red-800', label: 'L' },
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

function SortButton({ label, sort, onSort }: { label: string; sort: SortDirection; onSort: (v: SortDirection) => void }) {
  const nextSort: Record<SortDirection, SortDirection> = {
    none: 'asc',
    asc: 'desc',
    desc: 'none',
  }
  const arrow: Record<SortDirection, string> = { none: '', asc: ' ↑', desc: ' ↓' }
  return (
    <button
      onClick={() => onSort(nextSort[sort])}
      className={`rounded-md px-2 py-0.5 text-xs font-medium transition-colors ${
        sort !== 'none'
          ? 'bg-gray-200 text-gray-900'
          : 'text-gray-500 hover:text-gray-700'
      }`}
    >
      {label}{arrow[sort]}
    </button>
  )
}

function FilterSortControls({
  sizeFilter,
  onSizeFilter,
  sizeSort,
  onSizeSort,
  statusFilter,
  onStatusFilter,
  statusSort,
  onStatusSort,
  statuses,
}: {
  sizeFilter: SizeFilterValue
  onSizeFilter: (v: SizeFilterValue) => void
  sizeSort: SortDirection
  onSizeSort: (v: SortDirection) => void
  statusFilter: string
  onStatusFilter: (v: string) => void
  statusSort: SortDirection
  onStatusSort: (v: SortDirection) => void
  statuses: readonly { value: string; label: string }[]
}) {
  const sizes: SizeFilterValue[] = ['all', 'S', 'M', 'L']
  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Size filter pills */}
      <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-0.5">
        {sizes.map((s) => (
          <button
            key={s}
            onClick={() => onSizeFilter(s)}
            className={`rounded-md px-2 py-0.5 text-xs font-medium transition-colors ${
              sizeFilter === s
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {s === 'all' ? 'All' : s}
          </button>
        ))}
      </div>
      <SortButton label="Size" sort={sizeSort} onSort={onSizeSort} />
      {/* Status filter pills */}
      <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-0.5">
        <button
          onClick={() => onStatusFilter('all')}
          className={`rounded-md px-2 py-0.5 text-xs font-medium transition-colors ${
            statusFilter === 'all'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          All
        </button>
        {statuses.map((st) => (
          <button
            key={st.value}
            onClick={() => onStatusFilter(st.value)}
            className={`rounded-md px-2 py-0.5 text-xs font-medium transition-colors ${
              statusFilter === st.value
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {st.label}
          </button>
        ))}
      </div>
      <SortButton label="Status" sort={statusSort} onSort={onStatusSort} />
    </div>
  )
}

function Pagination({ current, total, onPage }: { current: number; total: number; onPage: (p: number) => void }) {
  return (
    <div className="mt-3 flex items-center justify-center gap-2">
      <button
        onClick={() => onPage(current - 1)}
        disabled={current <= 1}
        className="rounded-md px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-40 disabled:hover:bg-transparent"
      >
        Prev
      </button>
      <span className="text-sm text-gray-500">
        {current} / {total}
      </span>
      <button
        onClick={() => onPage(current + 1)}
        disabled={current >= total}
        className="rounded-md px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-40 disabled:hover:bg-transparent"
      >
        Next
      </button>
    </div>
  )
}

// ── Main App ──

function App() {
  const [days, setDays] = useState(7)
  const [attentionPage, setAttentionPage] = useState(1)
  const [progressPage, setProgressPage] = useState(1)
  const [attentionSizeFilter, setAttentionSizeFilter] = useState<SizeFilterValue>('all')
  const [attentionSizeSort, setAttentionSizeSort] = useState<SortDirection>('none')
  const [attentionStatusFilter, setAttentionStatusFilter] = useState('all')
  const [attentionStatusSort, setAttentionStatusSort] = useState<SortDirection>('none')
  const [progressSizeFilter, setProgressSizeFilter] = useState<SizeFilterValue>('all')
  const [progressSizeSort, setProgressSizeSort] = useState<SortDirection>('none')
  const [progressStatusFilter, setProgressStatusFilter] = useState('all')
  const [progressStatusSort, setProgressStatusSort] = useState<SortDirection>('none')
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useMetrics(days)
  const { data: lists, isLoading: listsLoading, error: listsError } = useLists()

  const filteredAttention = lists
    ? applyFiltersAndSorts(lists.needs_attention, attentionSizeFilter, attentionSizeSort, attentionStatusFilter, attentionStatusSort)
    : []
  const filteredProgress = lists
    ? applyFiltersAndSorts(lists.in_progress, progressSizeFilter, progressSizeSort, progressStatusFilter, progressStatusSort)
    : []

  const attentionTotal = Math.max(1, Math.ceil(filteredAttention.length / PAGE_SIZE))
  const progressTotal = Math.max(1, Math.ceil(filteredProgress.length / PAGE_SIZE))

  useEffect(() => {
    if (attentionPage > attentionTotal) setAttentionPage(Math.max(1, attentionTotal))
  }, [attentionPage, attentionTotal])

  useEffect(() => {
    if (progressPage > progressTotal) setProgressPage(Math.max(1, progressTotal))
  }, [progressPage, progressTotal])

  // Reset pages when filter/sort changes
  useEffect(() => {
    setAttentionPage(1)
  }, [attentionSizeFilter, attentionSizeSort, attentionStatusFilter, attentionStatusSort])

  useEffect(() => {
    setProgressPage(1)
  }, [progressSizeFilter, progressSizeSort, progressStatusFilter, progressStatusSort])

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
        <div className="mt-8 space-y-8">
          {/* Needs Attention */}
          <section>
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-gray-900">Needs Attention</h2>
                {lists && lists.needs_attention.length > 0 && (
                    <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-100 px-1.5 text-xs font-medium text-amber-800">
                      {filteredAttention.length}{(attentionSizeFilter !== 'all' || attentionStatusFilter !== 'all') ? ` / ${lists.needs_attention.length}` : ''}
                    </span>
                )}
              </div>
              {lists && lists.needs_attention.length > 0 && (
                <FilterSortControls
                  sizeFilter={attentionSizeFilter}
                  onSizeFilter={setAttentionSizeFilter}
                  sizeSort={attentionSizeSort}
                  onSizeSort={setAttentionSizeSort}
                  statusFilter={attentionStatusFilter}
                  onStatusFilter={setAttentionStatusFilter}
                  statusSort={attentionStatusSort}
                  onStatusSort={setAttentionStatusSort}
                  statuses={ATTENTION_STATUSES}
                />
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
            {lists && lists.needs_attention.length > 0 && filteredAttention.length === 0 && (
              <EmptyState message="No issues match the selected filters." />
            )}
            {filteredAttention.length > 0 && (
              <>
                <div className="space-y-2">
                  {filteredAttention.slice((attentionPage - 1) * PAGE_SIZE, attentionPage * PAGE_SIZE).map((issue) => (
                    <IssueRow key={issue.number} issue={issue} />
                  ))}
                </div>
                {filteredAttention.length > PAGE_SIZE && (
                  <Pagination
                    current={attentionPage}
                    total={Math.ceil(filteredAttention.length / PAGE_SIZE)}
                    onPage={setAttentionPage}
                  />
                )}
              </>
            )}
          </section>

          {/* In Progress */}
          <section>
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-gray-900">In Progress</h2>
                {lists && lists.in_progress.length > 0 && (
                    <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-sky-100 px-1.5 text-xs font-medium text-sky-800">
                      {filteredProgress.length}{(progressSizeFilter !== 'all' || progressStatusFilter !== 'all') ? ` / ${lists.in_progress.length}` : ''}
                    </span>
                )}
              </div>
              {lists && lists.in_progress.length > 0 && (
                <FilterSortControls
                  sizeFilter={progressSizeFilter}
                  onSizeFilter={setProgressSizeFilter}
                  sizeSort={progressSizeSort}
                  onSizeSort={setProgressSizeSort}
                  statusFilter={progressStatusFilter}
                  onStatusFilter={setProgressStatusFilter}
                  statusSort={progressStatusSort}
                  onStatusSort={setProgressStatusSort}
                  statuses={PROGRESS_STATUSES}
                />
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
            {lists && lists.in_progress.length > 0 && filteredProgress.length === 0 && (
              <EmptyState message="No issues match the selected filters." />
            )}
            {filteredProgress.length > 0 && (
              <>
                <div className="space-y-2">
                  {filteredProgress.slice((progressPage - 1) * PAGE_SIZE, progressPage * PAGE_SIZE).map((issue) => (
                    <IssueRow key={issue.number} issue={issue} />
                  ))}
                </div>
                {filteredProgress.length > PAGE_SIZE && (
                  <Pagination
                    current={progressPage}
                    total={Math.ceil(filteredProgress.length / PAGE_SIZE)}
                    onPage={setProgressPage}
                  />
                )}
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}

export default App
