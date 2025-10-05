import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from './use-auth'

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
  const queryClient = useQueryClient()

  const organisationsQuery = useQuery({
    queryKey: ['group-organisations'],
    queryFn: async (): Promise<Organisation[]> => {
      const response = await fetch('/api/organisations/group/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      if (!response.ok) {
        throw new Error('Failed to fetch organisations')
      }
      return response.json()
    },
    enabled: !!token,
  })

  const createOrganisationMutation = useMutation({
    mutationFn: async (data: CreateOrganisationData): Promise<Organisation> => {
      const response = await fetch('/api/organisations/group/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create organisation')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group-organisations'] })
    },
  })

  const updateOrganisationMutation = useMutation({
    mutationFn: async ({ slug, data }: { slug: string; data: UpdateOrganisationData }): Promise<Organisation> => {
      const response = await fetch(`/api/organisations/group/${slug}/`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to update organisation')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group-organisations'] })
    },
  })

  const deleteOrganisationMutation = useMutation({
    mutationFn: async (slug: string): Promise<void> => {
      const response = await fetch(`/api/organisations/group/${slug}/`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete organisation')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group-organisations'] })
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
