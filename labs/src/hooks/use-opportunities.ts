import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from './use-auth'
import { API_BASE_URL } from '../constants'

export interface Opportunity {
  id: string
  title: string
  description: string
  location: string
  organisation_name: string
  skills: OpportunitySkill[]
  experiences: OpportunityExperience[]
}

export interface OpportunitySkill {
  id: string
  skill_name: string
  requirement_type: string
}

export interface OpportunityExperience {
  id: string
  description: string
}

export interface PaginatedOpportunities {
  results: Opportunity[]
  page: number
  page_size: number
  total: number
  has_next: boolean
}

export interface OpportunitiesFilters {
  q?: string
  organisation?: string
  location?: string
  mode?: 'keyword' | 'semantic' | 'hybrid'
  page?: number
  page_size?: number
}

export function useOpportunities(filters: OpportunitiesFilters = {}) {
  const { token } = useAuth()
  const API_URL = API_BASE_URL || '/api'
  const queryClient = useQueryClient()

  // Build query key that includes all filters
  const queryKey = ['opportunities', filters]

  const opportunitiesQuery = useQuery({
    queryKey,
    queryFn: async (): Promise<PaginatedOpportunities> => {
      const params = new URLSearchParams()

      // Add filters to query params
      if (filters.q) params.append('q', filters.q)
      if (filters.organisation) params.append('organisation', filters.organisation)
      if (filters.location) params.append('location', filters.location)
      if (filters.mode) params.append('mode', filters.mode || 'hybrid')
      if (filters.page) params.append('page', filters.page.toString())
      if (filters.page_size) params.append('page_size', (filters.page_size || 20).toString())

      const url = `${API_URL}/api/opportunities/?${params.toString()}`

      const response = await fetch(url, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error('Failed to fetch opportunities')
      }

      return response.json()
    },
    enabled: true, // This is a public endpoint, no auth required but we include token if available
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Function to load more results
  const loadMore = () => {
    if (!opportunitiesQuery.data?.has_next) return

    const nextPage = (opportunitiesQuery.data.page || 1) + 1
    const nextFilters = { ...filters, page: nextPage }

    queryClient.prefetchQuery({
      queryKey: ['opportunities', nextFilters],
      queryFn: async (): Promise<PaginatedOpportunities> => {
        const params = new URLSearchParams()

        if (nextFilters.q) params.append('q', nextFilters.q)
        if (nextFilters.organisation) params.append('organisation', nextFilters.organisation)
        if (nextFilters.location) params.append('location', nextFilters.location)
        if (nextFilters.mode) params.append('mode', nextFilters.mode || 'hybrid')
        if (nextFilters.page) params.append('page', nextFilters.page.toString())
        if (nextFilters.page_size) params.append('page_size', (nextFilters.page_size || 20).toString())

        const url = `${API_URL}/api/opportunities/?${params.toString()}`

        const response = await fetch(url, {
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'Content-Type': 'application/json',
          },
        })

        if (!response.ok) {
          throw new Error('Failed to fetch opportunities')
        }

        return response.json()
      },
    })
  }

  return {
    opportunities: opportunitiesQuery.data?.results || [],
    pagination: {
      page: opportunitiesQuery.data?.page || 1,
      page_size: opportunitiesQuery.data?.page_size || 20,
      total: opportunitiesQuery.data?.total || 0,
      has_next: opportunitiesQuery.data?.has_next || false,
    },
    isLoading: opportunitiesQuery.isLoading,
    error: opportunitiesQuery.error,
    loadMore,
    refetch: opportunitiesQuery.refetch,
  }
}
