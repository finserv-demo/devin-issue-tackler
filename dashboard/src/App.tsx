import { useState, useEffect, useRef } from 'react'
import { useMetrics, useLists } from './api/hooks'
import type { MetricCard as MetricCardType, IssueItem } from './api/types'

const PAGE_SIZE = 5

// ── Filter/sort types ──

type SizeFilterValue = 'all' | 'S' | 'M' | 'L'
type AcuFilterValue = 'all' | 'none' | 'low' | 'moderate' | 'high'
type SortByValue = 'created_on' | 'last_updated' | 'status' | 'size' | 'acu'
type SortOrder = 'asc' | 'desc'

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

const SIZE_FILTER_TO_LABEL: Record<string, string> = {
  S: 'devin:small',
  M: 'devin:medium',
  L: 'devin:large',
}

function applyFiltersAndSort(
  items: IssueItem[],
  sizeFilter: SizeFilterValue,
  statusFilter: string,
  acuFilter: AcuFilterValue,
  sortBy: SortByValue,
  sortOrder: SortOrder,
): IssueItem[] {
  let result = items

  if (sizeFilter !== 'all') {
    const target = SIZE_FILTER_TO_LABEL[sizeFilter]
    result = result.filter((i) => i.sizing_label === target)
  }
  if (statusFilter !== 'all') {
    result = result.filter((i) => i.status_label === statusFilter)
  }
  if (acuFilter !== 'all') {
    result = result.filter((i) => {
      const acus = i.acus_consumed
      switch (acuFilter) {
        case 'none': return acus === null || acus === undefined
        case 'low': return acus !== null && acus !== undefined && acus < ACU_THRESHOLD_LOW
        case 'moderate': return acus !== null && acus !== undefined && acus >= ACU_THRESHOLD_LOW && acus <= ACU_THRESHOLD_HIGH
        case 'high': return acus !== null && acus !== undefined && acus > ACU_THRESHOLD_HIGH
        default: return true
      }
    })
  }

  result = [...result].sort((a, b) => {
    let cmp = 0
    switch (sortBy) {
      case 'created_on': {
        const aDate = a.created_at || ''
        const bDate = b.created_at || ''
        cmp = aDate.localeCompare(bDate)
        break
      }
      case 'last_updated': {
        const aDate = a.updated_at || ''
        const bDate = b.updated_at || ''
        cmp = aDate.localeCompare(bDate)
        break
      }
      case 'status': {
        const aStatus = STATUS_ORDER[a.status_label] ?? 99
        const bStatus = STATUS_ORDER[b.status_label] ?? 99
        cmp = aStatus - bStatus
        break
      }
      case 'size': {
        const aSize = a.sizing_label ? (SIZE_ORDER[a.sizing_label] ?? 99) : 99
        const bSize = b.sizing_label ? (SIZE_ORDER[b.sizing_label] ?? 99) : 99
        cmp = aSize - bSize
        break
      }
      case 'acu': {
        const aAcu = a.acus_consumed ?? -1
        const bAcu = b.acus_consumed ?? -1
        cmp = aAcu - bAcu
        break
      }
    }
    return sortOrder === 'asc' ? cmp : -cmp
  })

  return result
}

// ── Sizing badge colors ──

const SIZING_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  'devin:small': { bg: 'bg-emerald-100', text: 'text-emerald-800', label: 'S' },
  'devin:medium': { bg: 'bg-amber-100', text: 'text-amber-800', label: 'M' },
  'devin:large': { bg: 'bg-red-100', text: 'text-red-800', label: 'L' },
}

const STATUS_DISPLAY: Record<string, { bg: string; text: string; label: string }> = {
  'devin:pr-in-progress': { bg: 'bg-orange-100', text: 'text-orange-800', label: 'PR In Progress' },
  'devin:triage': { bg: 'bg-sky-100', text: 'text-sky-800', label: 'Triaging' },
  'devin:implement': { bg: 'bg-violet-100', text: 'text-violet-800', label: 'Implementing' },
}

// CTA buttons for statuses that need human action
const STATUS_CTA: Record<string, { bg: string; hoverBg: string; text: string; label: string }> = {
  'devin:triaged': { bg: 'bg-blue-600', hoverBg: 'hover:bg-blue-700', text: 'text-white', label: 'Review Triage \u2192' },
  'devin:pr-ready': { bg: 'bg-purple-600', hoverBg: 'hover:bg-purple-700', text: 'text-white', label: 'Review PR \u2192' },
  'devin:escalated': { bg: 'bg-red-600', hoverBg: 'hover:bg-red-700', text: 'text-white', label: 'Review Escalation \u2192' },
}

// ── Components ──

function HeroMetricCard({ metric, accent }: { metric: MetricCardType; accent?: boolean }) {
  const sentimentColor =
    metric.sentiment === 'positive'
      ? 'text-emerald-600'
      : metric.sentiment === 'negative'
        ? 'text-red-600'
        : 'text-gray-500'

  const Wrapper = metric.link_url ? 'a' : 'div'
  const wrapperProps = metric.link_url
    ? { href: metric.link_url, target: '_blank' as const, rel: 'noopener noreferrer' }
    : {}

  return (
    <Wrapper
      {...wrapperProps}
      className={`block rounded-xl border p-5 ${
        accent ? 'border-emerald-200 bg-emerald-50' : 'border-gray-200 bg-white'
      }${metric.link_url ? ' cursor-pointer transition-shadow hover:shadow-md' : ''}`}
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
    </Wrapper>
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

function StatusCTA({ label, href }: { label: string; href: string }) {
  const style = STATUS_CTA[label]
  if (!style) return null
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${style.bg} ${style.hoverBg} ${style.text} transition-colors`}
    >
      {style.label}
    </a>
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

// ── ACU badge thresholds (easily adjustable) ──

const ACU_THRESHOLD_LOW = 5
const ACU_THRESHOLD_HIGH = 10

const ACU_STYLES = {
  low: { bg: 'bg-emerald-100', text: 'text-emerald-800' },
  moderate: { bg: 'bg-amber-100', text: 'text-amber-800' },
  high: { bg: 'bg-red-100', text: 'text-red-800' },
} as const

function AcuBadge({ acus }: { acus: number | null }) {
  if (acus === null || acus === undefined) return null
  const level =
    acus < ACU_THRESHOLD_LOW ? 'low' : acus <= ACU_THRESHOLD_HIGH ? 'moderate' : 'high'
  const style = ACU_STYLES[level]
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}
    >
      {acus.toFixed(1)} ACU
    </span>
  )
}

function IssueRow({ issue }: { issue: IssueItem }) {
  const isPrStage = issue.status_label === 'devin:pr-in-progress' || issue.status_label === 'devin:pr-ready'
  const ctaStyle = STATUS_CTA[issue.status_label]
  // For PR-ready issues, the CTA links to the PR; otherwise link to the issue
  const ctaHref = issue.status_label === 'devin:pr-ready' && issue.pr_url ? issue.pr_url : issue.html_url

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
          {ctaStyle ? (
            <StatusCTA label={issue.status_label} href={ctaHref} />
          ) : (
            <StatusBadge label={issue.status_label} />
          )}
          <AcuBadge acus={issue.acus_consumed} />
          {isPrStage && <CIBadge status={issue.ci_status} />}
          {isPrStage && <ReviewThreadCount count={issue.unresolved_review_threads} />}
          {issue.time_in_state && (
            <span className="text-xs text-gray-400">{issue.time_in_state}</span>
          )}
        </div>
      </div>
      {issue.devin_latest_message && (
        <div className="mt-1 pl-9">
          <p className="truncate text-xs text-gray-400">{issue.devin_latest_message}</p>
        </div>
      )}
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

// ── Dropdown components ──

function useClickOutside(ref: React.RefObject<HTMLDivElement | null>, onClose: () => void) {
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [ref, onClose])
}

const CHEVRON_SVG = (
  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
  </svg>
)

const CHECK_SVG = (
  <svg className="h-3 w-3 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
  </svg>
)

function DropdownButton({
  label,
  isOpen,
  onToggle,
  isFiltered,
}: {
  label: string
  isOpen: boolean
  onToggle: () => void
  isFiltered?: boolean
}) {
  return (
    <button
      onClick={onToggle}
      className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
        isFiltered
          ? 'border-blue-300 bg-blue-50 text-blue-700'
          : isOpen
            ? 'border-gray-300 bg-gray-50 text-gray-900'
            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
      }`}
    >
      {label}
      {CHEVRON_SVG}
    </button>
  )
}

function DropdownOption({
  label,
  selected,
  onClick,
}: {
  label: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs ${
        selected ? 'bg-gray-50 font-medium text-gray-900' : 'text-gray-600 hover:bg-gray-50'
      }`}
    >
      {selected ? CHECK_SVG : <span className="h-3 w-3" />}
      {label}
    </button>
  )
}

function LabelDropdown({
  value,
  onChange,
}: {
  value: SizeFilterValue
  onChange: (v: SizeFilterValue) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useClickOutside(ref, () => setOpen(false))

  const options: { value: SizeFilterValue; label: string }[] = [
    { value: 'all', label: 'All sizes' },
    { value: 'S', label: 'S (Small)' },
    { value: 'M', label: 'M (Medium)' },
    { value: 'L', label: 'L (Large)' },
  ]

  const displayLabel = value === 'all' ? 'Label' : options.find((o) => o.value === value)?.label ?? value

  return (
    <div className="relative" ref={ref}>
      <DropdownButton
        label={displayLabel}
        isOpen={open}
        onToggle={() => setOpen(!open)}
        isFiltered={value !== 'all'}
      />
      {open && (
        <div className="absolute right-0 z-10 mt-1 w-40 rounded-md border border-gray-200 bg-white py-1 shadow-lg">
          {options.map((opt) => (
            <DropdownOption
              key={opt.value}
              label={opt.label}
              selected={value === opt.value}
              onClick={() => { onChange(opt.value); setOpen(false) }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function StatusDropdown({
  value,
  onChange,
  statuses,
}: {
  value: string
  onChange: (v: string) => void
  statuses: readonly { value: string; label: string }[]
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useClickOutside(ref, () => setOpen(false))

  const allOptions = [{ value: 'all', label: 'All statuses' }, ...statuses]
  const displayLabel = value === 'all' ? 'Status' : allOptions.find((o) => o.value === value)?.label ?? value

  return (
    <div className="relative" ref={ref}>
      <DropdownButton
        label={displayLabel}
        isOpen={open}
        onToggle={() => setOpen(!open)}
        isFiltered={value !== 'all'}
      />
      {open && (
        <div className="absolute right-0 z-10 mt-1 w-44 rounded-md border border-gray-200 bg-white py-1 shadow-lg">
          {allOptions.map((opt) => (
            <DropdownOption
              key={opt.value}
              label={opt.label}
              selected={value === opt.value}
              onClick={() => { onChange(opt.value); setOpen(false) }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function SortDropdown({
  sortBy,
  sortOrder,
  onSortByChange,
  onSortOrderChange,
}: {
  sortBy: SortByValue
  sortOrder: SortOrder
  onSortByChange: (v: SortByValue) => void
  onSortOrderChange: (v: SortOrder) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useClickOutside(ref, () => setOpen(false))

  const sortByOptions: { value: SortByValue; label: string }[] = [
    { value: 'created_on', label: 'Created on' },
    { value: 'last_updated', label: 'Last updated' },
    { value: 'status', label: 'Status' },
    { value: 'size', label: 'Size' },
    { value: 'acu', label: 'ACU usage' },
  ]

  const isTimeBased = sortBy === 'created_on' || sortBy === 'last_updated'
  const orderOptions: { value: SortOrder; label: string }[] = isTimeBased
    ? [
        { value: 'asc', label: 'Oldest' },
        { value: 'desc', label: 'Newest' },
      ]
    : [
        { value: 'asc', label: 'Ascending' },
        { value: 'desc', label: 'Descending' },
      ]

  const currentOrderLabel = orderOptions.find((o) => o.value === sortOrder)?.label ?? ''

  return (
    <div className="relative" ref={ref}>
      <DropdownButton
        label={currentOrderLabel}
        isOpen={open}
        onToggle={() => setOpen(!open)}
      />
      {open && (
        <div className="absolute right-0 z-10 mt-1 w-44 rounded-md border border-gray-200 bg-white shadow-lg">
          {/* Sort by section */}
          <div className="border-b border-gray-100 px-3 py-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Sort by</span>
          </div>
          <div className="py-1">
            {sortByOptions.map((opt) => (
              <DropdownOption
                key={opt.value}
                label={opt.label}
                selected={sortBy === opt.value}
                onClick={() => onSortByChange(opt.value)}
              />
            ))}
          </div>
          {/* Order section */}
          <div className="border-t border-gray-100 px-3 py-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Order</span>
          </div>
          <div className="py-1">
            {orderOptions.map((opt) => (
              <DropdownOption
                key={opt.value}
                label={opt.label}
                selected={sortOrder === opt.value}
                onClick={() => { onSortOrderChange(opt.value); setOpen(false) }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function AcuDropdown({
  value,
  onChange,
}: {
  value: AcuFilterValue
  onChange: (v: AcuFilterValue) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useClickOutside(ref, () => setOpen(false))

  const options: { value: AcuFilterValue; label: string }[] = [
    { value: 'all', label: 'All ACU' },
    { value: 'none', label: 'No usage' },
    { value: 'low', label: `Low (< ${ACU_THRESHOLD_LOW})` },
    { value: 'moderate', label: `Medium (${ACU_THRESHOLD_LOW}–${ACU_THRESHOLD_HIGH})` },
    { value: 'high', label: `High (> ${ACU_THRESHOLD_HIGH})` },
  ]

  const displayLabel = value === 'all' ? 'ACU' : options.find((o) => o.value === value)?.label ?? value

  return (
    <div className="relative" ref={ref}>
      <DropdownButton
        label={displayLabel}
        isOpen={open}
        onToggle={() => setOpen(!open)}
        isFiltered={value !== 'all'}
      />
      {open && (
        <div className="absolute right-0 z-10 mt-1 w-44 rounded-md border border-gray-200 bg-white py-1 shadow-lg">
          {options.map((opt) => (
            <DropdownOption
              key={opt.value}
              label={opt.label}
              selected={value === opt.value}
              onClick={() => { onChange(opt.value); setOpen(false) }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function FilterSortControls({
  sizeFilter,
  onSizeFilter,
  statusFilter,
  onStatusFilter,
  acuFilter,
  onAcuFilter,
  sortBy,
  onSortBy,
  sortOrder,
  onSortOrder,
  statuses,
}: {
  sizeFilter: SizeFilterValue
  onSizeFilter: (v: SizeFilterValue) => void
  statusFilter: string
  onStatusFilter: (v: string) => void
  acuFilter: AcuFilterValue
  onAcuFilter: (v: AcuFilterValue) => void
  sortBy: SortByValue
  onSortBy: (v: SortByValue) => void
  sortOrder: SortOrder
  onSortOrder: (v: SortOrder) => void
  statuses: readonly { value: string; label: string }[]
}) {
  return (
    <div className="flex items-center gap-2">
      <LabelDropdown value={sizeFilter} onChange={onSizeFilter} />
      <StatusDropdown value={statusFilter} onChange={onStatusFilter} statuses={statuses} />
      <AcuDropdown value={acuFilter} onChange={onAcuFilter} />
      <SortDropdown sortBy={sortBy} sortOrder={sortOrder} onSortByChange={onSortBy} onSortOrderChange={onSortOrder} />
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
  const [attentionStatusFilter, setAttentionStatusFilter] = useState('all')
  const [attentionSortBy, setAttentionSortBy] = useState<SortByValue>('created_on')
  const [attentionSortOrder, setAttentionSortOrder] = useState<SortOrder>('desc')
  const [attentionAcuFilter, setAttentionAcuFilter] = useState<AcuFilterValue>('all')
  const [progressSizeFilter, setProgressSizeFilter] = useState<SizeFilterValue>('all')
  const [progressStatusFilter, setProgressStatusFilter] = useState('all')
  const [progressSortBy, setProgressSortBy] = useState<SortByValue>('created_on')
  const [progressSortOrder, setProgressSortOrder] = useState<SortOrder>('desc')
  const [progressAcuFilter, setProgressAcuFilter] = useState<AcuFilterValue>('all')
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useMetrics(days)
  const { data: lists, isLoading: listsLoading, error: listsError } = useLists()

  const filteredAttention = lists
    ? applyFiltersAndSort(lists.needs_attention, attentionSizeFilter, attentionStatusFilter, attentionAcuFilter, attentionSortBy, attentionSortOrder)
    : []
  const filteredProgress = lists
    ? applyFiltersAndSort(lists.in_progress, progressSizeFilter, progressStatusFilter, progressAcuFilter, progressSortBy, progressSortOrder)
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
  }, [attentionSizeFilter, attentionStatusFilter, attentionAcuFilter, attentionSortBy, attentionSortOrder])

  useEffect(() => {
    setProgressPage(1)
  }, [progressSizeFilter, progressStatusFilter, progressAcuFilter, progressSortBy, progressSortOrder])

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
                      {filteredAttention.length}{(attentionSizeFilter !== 'all' || attentionStatusFilter !== 'all' || attentionAcuFilter !== 'all') ? ` / ${lists.needs_attention.length}` : ''}
                    </span>
                )}
              </div>
              {lists && lists.needs_attention.length > 0 && (
                <FilterSortControls
                  sizeFilter={attentionSizeFilter}
                  onSizeFilter={setAttentionSizeFilter}
                  statusFilter={attentionStatusFilter}
                  onStatusFilter={setAttentionStatusFilter}
                  acuFilter={attentionAcuFilter}
                  onAcuFilter={setAttentionAcuFilter}
                  sortBy={attentionSortBy}
                  onSortBy={setAttentionSortBy}
                  sortOrder={attentionSortOrder}
                  onSortOrder={setAttentionSortOrder}
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
                      {filteredProgress.length}{(progressSizeFilter !== 'all' || progressStatusFilter !== 'all' || progressAcuFilter !== 'all') ? ` / ${lists.in_progress.length}` : ''}
                    </span>
                )}
              </div>
              {lists && lists.in_progress.length > 0 && (
                <FilterSortControls
                  sizeFilter={progressSizeFilter}
                  onSizeFilter={setProgressSizeFilter}
                  statusFilter={progressStatusFilter}
                  onStatusFilter={setProgressStatusFilter}
                  acuFilter={progressAcuFilter}
                  onAcuFilter={setProgressAcuFilter}
                  sortBy={progressSortBy}
                  onSortBy={setProgressSortBy}
                  sortOrder={progressSortOrder}
                  onSortOrder={setProgressSortOrder}
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
