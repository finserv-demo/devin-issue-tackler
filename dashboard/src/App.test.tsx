import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect } from 'vitest'
import App from './App'

function renderWithProviders() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  )
}

describe('App', () => {
  it('renders the dashboard header', () => {
    renderWithProviders()
    expect(screen.getByText('Issue Tackler')).toBeInTheDocument()
    expect(screen.getByText('Devin automation dashboard')).toBeInTheDocument()
  })

  it('renders the time window toggle', () => {
    renderWithProviders()
    expect(screen.getByText('7 days')).toBeInTheDocument()
    expect(screen.getByText('30 days')).toBeInTheDocument()
  })

  it('renders the list section headers', () => {
    renderWithProviders()
    expect(screen.getByText('Needs Attention')).toBeInTheDocument()
    expect(screen.getByText('In Progress')).toBeInTheDocument()
  })
})
