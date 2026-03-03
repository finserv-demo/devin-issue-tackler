import { STATUS_CONFIG, SIZING_CONFIG } from '../api/types'

interface StatusBadgeProps {
  status: string
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? { label: status, color: '#6b7280', bgColor: '#f3f4f6' }
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '12px',
        fontSize: '12px',
        fontWeight: 600,
        color: config.color,
        backgroundColor: config.bgColor,
        whiteSpace: 'nowrap',
      }}
    >
      {config.label}
    </span>
  )
}

interface SizingBadgeProps {
  sizing: string | null
}

export function SizingBadge({ sizing }: SizingBadgeProps) {
  if (!sizing) return null
  const config = SIZING_CONFIG[sizing] ?? { label: sizing, color: '#6b7280', bgColor: '#f3f4f6' }
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 6px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: 700,
        color: config.color,
        backgroundColor: config.bgColor,
        letterSpacing: '0.5px',
      }}
    >
      {config.label}
    </span>
  )
}
