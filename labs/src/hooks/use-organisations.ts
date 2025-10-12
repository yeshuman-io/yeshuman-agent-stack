import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from './use-auth'
import { API_BASE_URL } from '../constants'
import { authorizedFetch } from '@/lib/api'

export interface Organisation {
  id: string
  name: string
  slug: string
  description: string
  website: string
  industry: string
  created_at: string
  updated_at: string
}

export interface CreateOrganisationData {
  name: string
  description?: string
  website?: string
  industry?: string
}

export interface UpdateOrganisationData {
  name: string
  description?: string
  website?: string
  industry?: string
}

export function useOrganisations() {
  const { token } = useAuth()
  const API_URL = API_BASE_URL || '/api'
  const queryClient = useQueryClient()

  const organisationsQuery = useQuery({
    queryKey: ['managed-organisations'],
    queryFn: async (): Promise<Organisation[]> => {
      const response = await authorizedFetch(`${API_URL}/api/organisations/managed`)
      if (!response.ok) {
        throw new Error('Failed to fetch organisations')
      }
      return response.json()
    },
    enabled: !!token,
  })

  const createOrganisationMutation = useMutation({
    mutationFn: async (data: CreateOrganisationData): Promise<Organisation> => {
      const response = await authorizedFetch(`${API_URL}/api/organisations/managed`, {
        method: 'POST',
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create organisation')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['managed-organisations'] })
    },
  })

  const updateOrganisationMutation = useMutation({
    mutationFn: async ({ slug, data }: { slug: string; data: UpdateOrganisationData }): Promise<Organisation> => {
      const response = await authorizedFetch(`${API_URL}/api/organisations/managed/${slug}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to update organisation')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['managed-organisations'] })
    },
  })

  const deleteOrganisationMutation = useMutation({
    mutationFn: async (slug: string): Promise<void> => {
      const response = await authorizedFetch(`${API_URL}/api/organisations/managed/${slug}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete organisation')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['managed-organisations'] })
    },
  })

  return {
    organisations: organisationsQuery.data || [],
    isLoading: organisationsQuery.isLoading,
    error: organisationsQuery.error,
    createOrganisation: createOrganisationMutation.mutate,
    isCreating: createOrganisationMutation.isPending,
    createError: createOrganisationMutation.error,
    updateOrganisation: updateOrganisationMutation.mutate,
    isUpdating: updateOrganisationMutation.isPending,
    updateError: updateOrganisationMutation.error,
    deleteOrganisation: deleteOrganisationMutation.mutate,
    isDeleting: deleteOrganisationMutation.isPending,
    deleteError: deleteOrganisationMutation.error,
  }
}
