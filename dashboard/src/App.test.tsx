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
  it('renders the navigation links', () => {
    renderWithProviders()
    expect(screen.getByText('Board')).toBeInTheDocument()
    expect(screen.getByText('Metrics')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders the app title', () => {
    renderWithProviders()
    expect(screen.getByText('Backlog Automation')).toBeInTheDocument()
  })
})
