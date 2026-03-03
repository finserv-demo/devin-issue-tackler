import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders the navigation links', () => {
    render(<App />)
    expect(screen.getByText('Board')).toBeInTheDocument()
    expect(screen.getByText('Metrics')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders the backlog board by default', () => {
    render(<App />)
    expect(screen.getByText('Backlog Board')).toBeInTheDocument()
  })
})
