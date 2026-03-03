import { useState } from 'react'

interface ActionButtonsProps {
  availableActions: string[]
  onAction: (action: string, message?: string) => void
  isLoading: boolean
}

const ACTION_CONFIG: Record<string, { label: string; color: string; bgColor: string; hoverBg: string; description: string }> = {
  proceed: {
    label: 'Proceed',
    color: '#ffffff',
    bgColor: '#2563eb',
    hoverBg: '#1d4ed8',
    description: 'Move to the next stage',
  },
  close: {
    label: 'Close',
    color: '#ffffff',
    bgColor: '#6b7280',
    hoverBg: '#4b5563',
    description: 'Close this issue',
  },
  feedback: {
    label: 'Give Feedback',
    color: '#2563eb',
    bgColor: '#eff6ff',
    hoverBg: '#dbeafe',
    description: 'Send feedback to Devin',
  },
}

export function ActionButtons({ availableActions, onAction, isLoading }: ActionButtonsProps) {
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')

  const handleAction = (action: string) => {
    if (action === 'feedback') {
      setShowFeedback(true)
      return
    }
    onAction(action)
  }

  const handleSubmitFeedback = () => {
    if (!feedbackText.trim()) return
    onAction('feedback', feedbackText)
    setFeedbackText('')
    setShowFeedback(false)
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {availableActions.map((action) => {
          const config = ACTION_CONFIG[action]
          if (!config) return null
          return (
            <button
              key={action}
              onClick={() => handleAction(action)}
              disabled={isLoading}
              title={config.description}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                border: action === 'feedback' ? '1px solid #bfdbfe' : 'none',
                backgroundColor: config.bgColor,
                color: config.color,
                fontSize: '13px',
                fontWeight: 600,
                cursor: isLoading ? 'not-allowed' : 'pointer',
                opacity: isLoading ? 0.6 : 1,
                transition: 'background-color 0.15s',
              }}
              onMouseEnter={(e) => {
                if (!isLoading) e.currentTarget.style.backgroundColor = config.hoverBg
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = config.bgColor
              }}
            >
              {config.label}
            </button>
          )
        })}
      </div>

      {showFeedback && (
        <div style={{ marginTop: '12px' }}>
          <textarea
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            placeholder="Type your feedback for Devin..."
            style={{
              width: '100%',
              minHeight: '80px',
              padding: '10px 12px',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
              fontSize: '13px',
              fontFamily: 'inherit',
              resize: 'vertical',
              outline: 'none',
              boxSizing: 'border-box',
            }}
            onFocus={(e) => { e.currentTarget.style.borderColor = '#3b82f6' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = '#d1d5db' }}
          />
          <div style={{ display: 'flex', gap: '8px', marginTop: '8px', justifyContent: 'flex-end' }}>
            <button
              onClick={() => { setShowFeedback(false); setFeedbackText('') }}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: '1px solid #d1d5db',
                backgroundColor: '#fff',
                color: '#374151',
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmitFeedback}
              disabled={!feedbackText.trim() || isLoading}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: feedbackText.trim() ? '#2563eb' : '#93c5fd',
                color: '#fff',
                fontSize: '13px',
                fontWeight: 600,
                cursor: feedbackText.trim() && !isLoading ? 'pointer' : 'not-allowed',
              }}
            >
              Send Feedback
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
