import { useParams } from 'react-router-dom'

function IssueDetail() {
  const { number } = useParams<{ number: string }>()
  return (
    <div>
      <h1>Issue #{number}</h1>
      <p>Issue detail + timeline — coming in Phase 3 (issue #17)</p>
    </div>
  )
}

export default IssueDetail
