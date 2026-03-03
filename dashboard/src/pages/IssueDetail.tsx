import { useParams, Link } from 'react-router-dom'
import { useIssueDetail, useCommand, usePostComment } from '../api/hooks'
import { StatusBadge, SizingBadge } from '../components/StatusBadge'
import { Timeline } from '../components/Timeline'
import { ActionButtons } from '../components/ActionButtons'

function IssueDetail() {
  const { number } = useParams<{ number: string }>()
  const issueNumber = Number(number)
  const { data: issue, isLoading, error } = useIssueDetail(issueNumber)
  const command = useCommand(issueNumber)
  const postComment = usePostComment(issueNumber)

  const handleAction = (action: string, message?: string) => {
    if (action === 'feedback' && message) {
      postComment.mutate(message)
    } else {
      command.mutate({ action, message })
    }
  }

  if (isLoading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>Loading...</div>
  }

  if (error || !issue) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#dc2626' }}>
        {error ? `Failed to load issue: ${error.message}` : 'Issue not found'}
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '960px' }}>
      {/* Breadcrumb */}
      <div style={{ marginBottom: '16px' }}>
        <Link to="/" style={{ color: '#6b7280', textDecoration: 'none', fontSize: '13px' }}>
          ← Back to Board
        </Link>
      </div>

      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <span style={{ color: '#6b7280', fontSize: '18px' }}>#{issue.number}</span>
          <h1 style={{ margin: 0, fontSize: '22px', color: '#111827' }}>{issue.title}</h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <StatusBadge status={issue.status} />
          <SizingBadge sizing={issue.sizing} />
          {issue.html_url && (
            <a href={issue.html_url} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: '12px', color: '#3b82f6', textDecoration: 'none' }}>
              View on GitHub →
            </a>
          )}
          {issue.pr_url && (
            <a href={issue.pr_url} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: '12px', color: '#3b82f6', textDecoration: 'none' }}>
              PR #{issue.pr_number} →
            </a>
          )}
        </div>
      </div>

      {/* Top cards row: Status + Action Required + Next Steps */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
        {/* Action Required / Attention */}
        {issue.needs_attention && issue.attention_reason ? (
          <div style={{
            padding: '16px',
            borderRadius: '8px',
            border: '1px solid #fde68a',
            backgroundColor: '#fffbeb',
          }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: '#92400e', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
              Action Required
            </div>
            <div style={{ fontSize: '14px', color: '#92400e', fontWeight: 500, marginBottom: '12px' }}>
              {issue.attention_reason}
            </div>
            <ActionButtons
              availableActions={issue.available_actions}
              onAction={handleAction}
              isLoading={command.isPending || postComment.isPending}
            />
          </div>
        ) : (
          <div style={{
            padding: '16px',
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            backgroundColor: '#f9fafb',
          }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
              Actions
            </div>
            <ActionButtons
              availableActions={issue.available_actions}
              onAction={handleAction}
              isLoading={command.isPending || postComment.isPending}
            />
          </div>
        )}

        {/* Next Steps */}
        <div style={{
          padding: '16px',
          borderRadius: '8px',
          border: '1px solid #dbeafe',
          backgroundColor: '#eff6ff',
        }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
            Next Steps
          </div>
          <div style={{ fontSize: '14px', color: '#1e3a5f', lineHeight: '1.5' }}>
            {issue.next_steps}
          </div>
        </div>
      </div>

      {/* Command result */}
      {(command.isSuccess || postComment.isSuccess) && (
        <div style={{
          marginBottom: '16px',
          padding: '8px 12px',
          borderRadius: '6px',
          backgroundColor: '#dcfce7',
          color: '#15803d',
          fontSize: '13px',
        }}>
          {command.data?.message ?? postComment.data?.message}
        </div>
      )}

      {/* Devin Sessions */}
      {issue.sessions.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 12px', fontSize: '14px', color: '#374151' }}>Devin Sessions</h3>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {issue.sessions.map((session) => (
              <a
                key={session.session_id}
                href={session.session_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'block',
                  padding: '10px 14px',
                  borderRadius: '6px',
                  border: '1px solid #e5e7eb',
                  backgroundColor: '#fff',
                  textDecoration: 'none',
                  color: 'inherit',
                  fontSize: '13px',
                  minWidth: '180px',
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: '4px', textTransform: 'capitalize' }}>
                  {session.stage} Session
                </div>
                <div style={{ display: 'flex', gap: '12px', color: '#6b7280', fontSize: '12px' }}>
                  <span>Status: <span style={{
                    color: session.status === 'completed' ? '#15803d' : session.status === 'failed' ? '#dc2626' : '#b45309',
                    fontWeight: 500,
                  }}>{session.status}</span></span>
                  <span>{session.acus_consumed.toFixed(1)} ACUs</span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Issue body */}
      {issue.body && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 12px', fontSize: '14px', color: '#374151' }}>Description</h3>
          <div style={{
            padding: '14px 16px',
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            backgroundColor: '#fff',
            fontSize: '13px',
            lineHeight: '1.6',
            whiteSpace: 'pre-wrap',
            color: '#374151',
          }}>
            {issue.body}
          </div>
        </div>
      )}

      {/* Timeline */}
      <div>
        <h3 style={{ margin: '0 0 16px', fontSize: '14px', color: '#374151' }}>
          Activity ({issue.timeline.length} events)
        </h3>
        <Timeline entries={issue.timeline} />
      </div>
    </div>
  )
}

export default IssueDetail
