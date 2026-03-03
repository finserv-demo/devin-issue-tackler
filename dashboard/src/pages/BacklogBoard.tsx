import { useMemo } from 'react'
import { useIssues, useTriageAll, useMetrics } from '../api/hooks'
import { IssueCard } from '../components/IssueCard'
import { STATUS_CONFIG } from '../api/types'
import type { IssueSummary } from '../api/types'

/** Pipeline columns in order */
const PIPELINE_COLUMNS = ['new', 'triage', 'triaged', 'implement', 'pr-opened', 'done', 'escalated'] as const

function BacklogBoard() {
  const { data: issues, isLoading, error } = useIssues()
  const { data: metrics } = useMetrics()
  const triageAll = useTriageAll()

  const attentionIssues = useMemo(() => {
    if (!issues) return []
    return issues.filter((i) => i.needs_attention)
  }, [issues])

  const issuesByStatus = useMemo(() => {
    const map: Record<string, IssueSummary[]> = {}
    for (const col of PIPELINE_COLUMNS) {
      map[col] = []
    }
    if (issues) {
      for (const issue of issues) {
        const status = issue.status
        if (map[status]) {
          map[status].push(issue)
        } else {
          map['new'].push(issue)
        }
      }
    }
    return map
  }, [issues])

  const activeCount = useMemo(() => {
    if (!issues) return 0
    return issues.filter((i) => !['done', 'new'].includes(i.status)).length
  }, [issues])

  const doneCount = metrics?.total_done ?? 0
  const totalProcessed = metrics?.total_processed ?? 0
  const successRate = metrics?.success_rate ?? 0

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#dc2626' }}>
        Failed to load issues: {error.message}
      </div>
    )
  }

  return (
    <div>
      {/* Hero stats — communicate that backlog disappears fast */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '16px',
        marginBottom: '24px',
      }}>
        <StatCard
          label="Resolved"
          value={String(doneCount)}
          subtitle={`of ${totalProcessed} processed`}
          color="#16a34a"
          bgColor="#f0fdf4"
        />
        <StatCard
          label="Success Rate"
          value={`${successRate.toFixed(0)}%`}
          subtitle="issues auto-resolved"
          color="#2563eb"
          bgColor="#eff6ff"
        />
        <StatCard
          label="Active Now"
          value={String(activeCount)}
          subtitle="being triaged or fixed"
          color="#7c3aed"
          bgColor="#f5f3ff"
        />
        <StatCard
          label="Median Resolution"
          value={metrics?.resolution_time ? `${metrics.resolution_time.median_hours.toFixed(0)}h` : '\u2014'}
          subtitle="from triage to PR"
          color="#b45309"
          bgColor="#fffbeb"
        />
      </div>

      {/* Needs Your Attention section */}
      {attentionIssues.length > 0 && (
        <div style={{
          marginBottom: '24px',
          padding: '16px',
          borderRadius: '8px',
          border: '1px solid #fde68a',
          backgroundColor: '#fffbeb',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '12px',
          }}>
            <h2 style={{ margin: 0, fontSize: '16px', color: '#92400e' }}>
              Needs Your Attention ({attentionIssues.length})
            </h2>
          </div>
          {attentionIssues.map((issue) => (
            <IssueCard key={issue.number} issue={issue} compact />
          ))}
        </div>
      )}

      {/* Triage all button + board header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '16px',
      }}>
        <h2 style={{ margin: 0, fontSize: '18px', color: '#111827' }}>Pipeline</h2>
        <button
          onClick={() => triageAll.mutate()}
          disabled={triageAll.isPending}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            border: 'none',
            backgroundColor: '#2563eb',
            color: '#fff',
            fontSize: '13px',
            fontWeight: 600,
            cursor: triageAll.isPending ? 'not-allowed' : 'pointer',
            opacity: triageAll.isPending ? 0.6 : 1,
          }}
        >
          {triageAll.isPending ? 'Starting...' : 'Triage All New Issues'}
        </button>
      </div>

      {/* Kanban board */}
      {isLoading ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>
          Loading issues...
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${PIPELINE_COLUMNS.length}, 1fr)`,
          gap: '12px',
          overflowX: 'auto',
        }}>
          {PIPELINE_COLUMNS.map((status) => {
            const config = STATUS_CONFIG[status]
            const columnIssues = issuesByStatus[status] ?? []
            return (
              <div
                key={status}
                style={{
                  backgroundColor: '#f9fafb',
                  borderRadius: '8px',
                  padding: '12px',
                  minWidth: '200px',
                }}
              >
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '10px',
                  paddingBottom: '8px',
                  borderBottom: `2px solid ${config?.color ?? '#e5e7eb'}`,
                }}>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    color: config?.color ?? '#6b7280',
                  }}>
                    {config?.label ?? status}
                  </span>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color: '#6b7280',
                    backgroundColor: '#e5e7eb',
                    borderRadius: '10px',
                    padding: '1px 7px',
                  }}>
                    {columnIssues.length}
                  </span>
                </div>
                {columnIssues.length === 0 ? (
                  <div style={{ padding: '12px 0', textAlign: 'center', color: '#9ca3af', fontSize: '12px' }}>
                    No issues
                  </div>
                ) : (
                  columnIssues.map((issue) => (
                    <IssueCard key={issue.number} issue={issue} compact />
                  ))
                )}
              </div>
            )
          })}
        </div>
      )}

      {triageAll.isSuccess && (
        <div style={{
          marginTop: '12px',
          padding: '8px 12px',
          borderRadius: '6px',
          backgroundColor: '#dcfce7',
          color: '#16a34a',
          fontSize: '13px',
        }}>
          {triageAll.data.message}
        </div>
      )}
    </div>
  )
}

interface StatCardProps {
  label: string
  value: string
  subtitle: string
  color: string
  bgColor: string
}

function StatCard({ label, value, subtitle, color, bgColor }: StatCardProps) {
  return (
    <div style={{
      padding: '16px 20px',
      borderRadius: '8px',
      backgroundColor: bgColor,
      border: `1px solid ${color}20`,
    }}>
      <div style={{ fontSize: '12px', fontWeight: 600, color, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        {label}
      </div>
      <div style={{ fontSize: '28px', fontWeight: 700, color: '#111827', marginTop: '4px' }}>
        {value}
      </div>
      <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>
        {subtitle}
      </div>
    </div>
  )
}

export default BacklogBoard
