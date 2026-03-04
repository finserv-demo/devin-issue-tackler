import { useQuery } from '@tanstack/react-query'
import { fetchJSON } from './client'
import type { DashboardMetrics, DashboardLists } from './types'

export function useMetrics(days: number) {
  return useQuery<DashboardMetrics>({
    queryKey: ['metrics', days],
    queryFn: () => fetchJSON<DashboardMetrics>(`/metrics?days=${days}`),
  })
}

export function useLists() {
  return useQuery<DashboardLists>({
    queryKey: ['lists'],
    queryFn: () => fetchJSON<DashboardLists>('/lists'),
  })
}
