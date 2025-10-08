import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from './use-auth'
import { API_BASE_URL } from '../constants'

export interface OrganisationOpportunity {
  id: string
  title: string
  description: string
  skills: OrganisationOpportunitySkill[]
  experiences: OrganisationOpportunityExperience[]
  created_at: string
  updated_at: string
}

export interface OrganisationOpportunitySkill {
  id: string
  skill_name: string
  requirement_type: string
}

export interface OrganisationOpportunityExperience {
  id: string
  description: string
}

export interface OrganisationOpportunitySkillData {
  skill_id: string
  requirement_type: 'required' | 'preferred'
}

export interface CreateOrganisationOpportunityData {
  title: string
  description: string
  skills: OrganisationOpportunitySkillData[]
}

export interface UpdateOrganisationOpportunityData {
  title: string
  description: string
}

export function useOrganisationOpportunities(organisationSlug: string) {
  const { token } = useAuth()
  const API_URL = API_BASE_URL || '/api'
  const queryClient = useQueryClient()

  const opportunitiesQuery = useQuery({
    queryKey: ['organisation-opportunities', organisationSlug],
    queryFn: async (): Promise<OrganisationOpportunity[]> => {
      const response = await fetch(`${API_URL}/api/organisations/managed/${organisationSlug}/opportunities/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      if (!response.ok) {
        throw new Error('Failed to fetch opportunities')
      }
      return response.json()
    },
    enabled: !!token && !!organisationSlug,
  })

  const createOpportunityMutation = useMutation({
    mutationFn: async (data: CreateOrganisationOpportunityData): Promise<OrganisationOpportunity> => {
      const response = await fetch(`${API_URL}/api/organisations/managed/${organisationSlug}/opportunities/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create opportunity')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organisation-opportunities', organisationSlug] })
    },
  })

  const updateOpportunityMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateOrganisationOpportunityData }): Promise<OrganisationOpportunity> => {
      const response = await fetch(`${API_URL}/api/organisations/managed/${organisationSlug}/opportunities/${id}/`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to update opportunity')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organisation-opportunities', organisationSlug] })
    },
  })

  const deleteOpportunityMutation = useMutation({
    mutationFn: async (id: string): Promise<void> => {
      const response = await fetch(`${API_URL}/api/organisations/managed/${organisationSlug}/opportunities/${id}/`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete opportunity')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organisation-opportunities', organisationSlug] })
    },
  })

  return {
    opportunities: opportunitiesQuery.data || [],
    isLoading: opportunitiesQuery.isLoading,
    error: opportunitiesQuery.error,
    createOpportunity: createOpportunityMutation.mutate,
    isCreating: createOpportunityMutation.isPending,
    createError: createOpportunityMutation.error,
    updateOpportunity: updateOpportunityMutation.mutate,
    isUpdating: updateOpportunityMutation.isPending,
    updateError: updateOpportunityMutation.error,
    deleteOpportunity: deleteOpportunityMutation.mutate,
    isDeleting: deleteOpportunityMutation.isPending,
    deleteError: deleteOpportunityMutation.error,
  }
}
