import { Link } from 'react-router-dom'
import type { IssueSummary } from '../api/types'
import { StatusBadge, SizingBadge } from './StatusBadge'

interface IssueCardProps {
  issue: IssueSummary
  compact?: boolean
}

export function IssueCard({ issue, compact = false }: IssueCardProps) {
  const borderColor = issue.needs_attention ? '#f59e0b' : '#e5e7eb'

  return (
    <Link
      to={`/issues/${issue.number}`}
      style={{
        display: 'block',
        textDecoration: 'none',
        color: 'inherit',
        padding: compact ? '10px 12px' : '14px 16px',
        borderRadius: '8px',
        border: `1px solid ${borderColor}`,
        borderLeft: issue.needs_attention ? '4px solid #f59e0b' : `1px solid ${borderColor}`,
        backgroundColor: '#fff',
        transition: 'box-shadow 0.15s, border-color 0.15s',
        marginBottom: '8px',
        cursor: 'pointer',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'
        e.currentTarget.style.borderColor = '#3b82f6'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = 'none'
        e.currentTarget.style.borderColor = borderColor
      }}
    >
      {compact ? (
        /* Compact layout for kanban columns — stacked vertically to avoid overlap */
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <span style={{ color: '#6b7280', fontSize: '12px', fontWeight: 600, flexShrink: 0 }}>#{issue.number}</span>
            <SizingBadge sizing={issue.sizing} />
            <StatusBadge status={issue.status} />
            <span style={{ fontSize: '11px', color: '#9ca3af', whiteSpace: 'nowrap', marginLeft: 'auto' }}>
              {issue.time_in_state}
            </span>
          </div>
          <div style={{
            fontSize: '13px',
            fontWeight: 500,
            color: '#111827',
            lineHeight: '1.4',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}>
            {issue.title}
          </div>
          {issue.needs_attention && issue.attention_reason && (
            <div style={{
              fontSize: '11px',
              color: '#b45309',
              marginTop: '6px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '4px',
              lineHeight: '1.3',
            }}>
              <span style={{ fontSize: '12px', flexShrink: 0 }}>&#9888;</span>
              {issue.attention_reason}
            </div>
          )}
        </div>
      ) : (
        /* Full layout for attention section and other wide contexts */
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ color: '#6b7280', fontSize: '13px', fontWeight: 500, flexShrink: 0 }}>#{issue.number}</span>
              <span style={{
                fontSize: '14px',
                fontWeight: 500,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {issue.title}
              </span>
            </div>
            {issue.needs_attention && issue.attention_reason && (
              <div style={{
                fontSize: '12px',
                color: '#b45309',
                marginTop: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}>
                <span style={{ fontSize: '14px' }}>&#9888;</span>
                {issue.attention_reason}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
            <SizingBadge sizing={issue.sizing} />
            <StatusBadge status={issue.status} />
            <span style={{ fontSize: '11px', color: '#9ca3af', whiteSpace: 'nowrap' }}>
              {issue.time_in_state}
            </span>
          </div>
        </div>
      )}
    </Link>
  )
}
