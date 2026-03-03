import type { TimelineEntry } from '../api/types'

interface TimelineProps {
  entries: TimelineEntry[]
}

function formatTimestamp(iso: string): string {
  try {
    const date = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60_000)
    const diffHours = Math.floor(diffMs / 3_600_000)
    const diffDays = Math.floor(diffMs / 86_400_000)

    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch {
    return iso
  }
}

function getEntryIcon(type: string): string {
  switch (type) {
    case 'comment': return '\u{1F4AC}'
    case 'state_change': return '\u{1F504}'
    case 'session_event': return '\u{1F916}'
    case 'label': return '\u{1F3F7}'
    default: return '\u{1F4CB}'
  }
}

function getEntryColor(type: string): string {
  switch (type) {
    case 'comment': return '#3b82f6'
    case 'state_change': return '#8b5cf6'
    case 'session_event': return '#06b6d4'
    case 'label': return '#f59e0b'
    default: return '#6b7280'
  }
}

export function Timeline({ entries }: TimelineProps) {
  // Show newest first
  const sorted = [...entries].reverse()

  return (
    <div style={{ position: 'relative' }}>
      {sorted.map((entry, i) => (
        <div
          key={`${entry.timestamp}-${i}`}
          style={{
            display: 'flex',
            gap: '12px',
            paddingBottom: '20px',
            position: 'relative',
          }}
        >
          {/* Timeline line */}
          {i < sorted.length - 1 && (
            <div
              style={{
                position: 'absolute',
                left: '15px',
                top: '32px',
                bottom: '0',
                width: '2px',
                backgroundColor: '#e5e7eb',
              }}
            />
          )}

          {/* Icon */}
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: `${getEntryColor(entry.type)}15`,
              border: `2px solid ${getEntryColor(entry.type)}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
              flexShrink: 0,
              zIndex: 1,
            }}
          >
            {getEntryIcon(entry.type)}
          </div>

          {/* Content */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '4px',
            }}>
              <span style={{ fontWeight: 600, fontSize: '13px', color: '#374151' }}>
                {entry.actor}
              </span>
              <span style={{ fontSize: '12px', color: '#9ca3af' }}>
                {formatTimestamp(entry.timestamp)}
              </span>
            </div>

            {entry.type === 'state_change' && (
              <div style={{
                fontSize: '13px',
                color: '#6b7280',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}>
                {entry.from_state && (
                  <>
                    <span style={{
                      padding: '1px 6px',
                      borderRadius: '4px',
                      backgroundColor: '#f3f4f6',
                      fontSize: '12px',
                    }}>
                      {entry.from_state}
                    </span>
                    <span>→</span>
                  </>
                )}
                <span style={{
                  padding: '1px 6px',
                  borderRadius: '4px',
                  backgroundColor: '#dbeafe',
                  fontSize: '12px',
                  fontWeight: 500,
                }}>
                  {entry.to_state}
                </span>
                {entry.body && <span style={{ marginLeft: '4px' }}>— {entry.body}</span>}
              </div>
            )}

            {entry.type === 'label' && (
              <div style={{ fontSize: '13px', color: '#6b7280' }}>
                {entry.body}
                {entry.label && (
                  <span style={{
                    marginLeft: '4px',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    backgroundColor: '#fef3c7',
                    fontSize: '12px',
                  }}>
                    {entry.label}
                  </span>
                )}
              </div>
            )}

            {entry.type === 'comment' && (
              <div style={{
                fontSize: '13px',
                color: '#374151',
                backgroundColor: '#f9fafb',
                borderRadius: '8px',
                padding: '10px 12px',
                border: '1px solid #e5e7eb',
                whiteSpace: 'pre-wrap',
                lineHeight: '1.5',
              }}>
                {entry.body}
              </div>
            )}

            {entry.type === 'session_event' && (
              <div style={{ fontSize: '13px', color: '#374151' }}>
                {entry.body}
                {entry.session_url && (
                  <a
                    href={entry.session_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      marginLeft: '8px',
                      color: '#3b82f6',
                      fontSize: '12px',
                      textDecoration: 'none',
                    }}
                  >
                    View session →
                  </a>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
