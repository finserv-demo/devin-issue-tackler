import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import BacklogBoard from './pages/BacklogBoard'
import IssueDetail from './pages/IssueDetail'
import Metrics from './pages/Metrics'
import Settings from './pages/Settings'

const navLinkStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
  textDecoration: 'none',
  padding: '6px 12px',
  borderRadius: '6px',
  fontSize: '14px',
  fontWeight: isActive ? 600 : 400,
  color: isActive ? '#2563eb' : '#6b7280',
  backgroundColor: isActive ? '#eff6ff' : 'transparent',
  transition: 'color 0.15s, background-color 0.15s',
})

function App() {
  return (
    <BrowserRouter>
      <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', backgroundColor: '#f9fafb', minHeight: '100vh' }}>
        <nav style={{
          padding: '12px 24px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          backgroundColor: '#fff',
        }}>
          <span style={{ fontWeight: 700, fontSize: '15px', color: '#111827', marginRight: '16px' }}>
            Backlog Automation
          </span>
          <NavLink to="/" style={navLinkStyle} end>Board</NavLink>
          <NavLink to="/metrics" style={navLinkStyle}>Metrics</NavLink>
          <NavLink to="/settings" style={navLinkStyle}>Settings</NavLink>
        </nav>
        <main style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
          <Routes>
            <Route path="/" element={<BacklogBoard />} />
            <Route path="/issues/:number" element={<IssueDetail />} />
            <Route path="/metrics" element={<Metrics />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
