import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import BacklogBoard from './pages/BacklogBoard'
import IssueDetail from './pages/IssueDetail'
import Metrics from './pages/Metrics'
import Settings from './pages/Settings'

function App() {
  return (
    <BrowserRouter>
      <div style={{ fontFamily: 'system-ui, sans-serif' }}>
        <nav style={{ padding: '1rem', borderBottom: '1px solid #eee', display: 'flex', gap: '1rem' }}>
          <NavLink to="/">Board</NavLink>
          <NavLink to="/metrics">Metrics</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
        <main style={{ padding: '1rem' }}>
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
