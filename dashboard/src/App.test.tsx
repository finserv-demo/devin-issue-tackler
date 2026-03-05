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

  it('renders loading skeleton for hero metrics', () => {
    renderWithProviders()
    // While metrics are loading, 3 skeleton placeholders are shown
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThanOrEqual(3)
  })

  it('renders the list section headers', () => {
    renderWithProviders()
    expect(screen.getByText('Needs Attention')).toBeInTheDocument()
    expect(screen.getByText('In Progress')).toBeInTheDocument()
  })
})
