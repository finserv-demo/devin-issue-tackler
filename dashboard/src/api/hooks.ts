/** React Query hooks for dashboard API calls. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchJSON } from './client'
import type {
  IssueSummary,
  IssueDetail,
  CommandResponse,
  MetricsSummary,
  SettingsData,
} from './types'

export function useIssues() {
  return useQuery<IssueSummary[]>({
    queryKey: ['issues'],
    queryFn: () => fetchJSON<IssueSummary[]>('/issues'),
    refetchInterval: 30_000,
  })
}

export function useIssueDetail(number: number) {
  return useQuery<IssueDetail>({
    queryKey: ['issue', number],
    queryFn: () => fetchJSON<IssueDetail>(`/issues/${number}`),
    refetchInterval: 15_000,
  })
}

export function usePostComment(number: number) {
  const queryClient = useQueryClient()
  return useMutation<CommandResponse, Error, string>({
    mutationFn: (body: string) =>
      fetchJSON<CommandResponse>(`/issues/${number}/comment`, {
        method: 'POST',
        body: JSON.stringify({ body }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['issue', number] })
    },
  })
}

export function useCommand(number: number) {
  const queryClient = useQueryClient()
  return useMutation<CommandResponse, Error, { action: string; message?: string }>({
    mutationFn: (params) =>
      fetchJSON<CommandResponse>(`/issues/${number}/command`, {
        method: 'POST',
        body: JSON.stringify(params),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['issue', number] })
      void queryClient.invalidateQueries({ queryKey: ['issues'] })
    },
  })
}

export function useTriageAll() {
  const queryClient = useQueryClient()
  return useMutation<CommandResponse, Error>({
    mutationFn: () =>
      fetchJSON<CommandResponse>('/issues/triage-all', { method: 'POST' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['issues'] })
    },
  })
}

export function useMetrics() {
  return useQuery<MetricsSummary>({
    queryKey: ['metrics'],
    queryFn: () => fetchJSON<MetricsSummary>('/metrics/summary'),
    refetchInterval: 60_000,
  })
}

export function useSettings() {
  return useQuery<SettingsData>({
    queryKey: ['settings'],
    queryFn: () => fetchJSON<SettingsData>('/settings'),
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  return useMutation<SettingsData, Error, Partial<SettingsData>>({
    mutationFn: (update) =>
      fetchJSON<SettingsData>('/settings', {
        method: 'PUT',
        body: JSON.stringify(update),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}
