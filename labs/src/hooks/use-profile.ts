import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from './use-auth'
import { authorizedFetch } from '@/lib/api'

export interface ProfileData {
  id?: string
  full_name?: string
  email?: string
  bio?: string
  city?: string
  country?: string
  skills?: string[]
  first_name?: string
  last_name?: string
  experiences?: Experience[]
}

export interface Experience {
  id: string
  title: string
  company: string
  description?: string
  start_date: string
  end_date?: string | null
  skills?: string[]
}

export function useProfile() {
  const { token } = useAuth()
  const queryClient = useQueryClient()

  // Query for fetching profile data
  const profileQuery = useQuery({
    queryKey: ['profile'],
    queryFn: async (): Promise<ProfileData> => {
      if (!token) throw new Error('Not authenticated')

      const response = await authorizedFetch('/api/profiles/my')

      if (!response.ok) {
        throw new Error('Failed to fetch profile')
      }

      return response.json()
    },
    enabled: !!token,
  })

  // Mutation for updating profile data
  const updateProfileMutation = useMutation({
    mutationFn: async (data: Partial<ProfileData>): Promise<ProfileData> => {
      if (!token) throw new Error('Not authenticated')

      const response = await authorizedFetch('/api/profiles/my', {
        method: 'POST',
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || 'Failed to update profile')
      }

      return response.json()
    },
    onSuccess: (data) => {
      // Update the cache with the new data
      queryClient.setQueryData(['profile'], data)
    },
  })

  // Mutation: add experience
  const addExperienceMutation = useMutation({
    mutationFn: async (exp: Omit<Experience, 'id'>): Promise<Experience> => {
      if (!token) throw new Error('Not authenticated')

      const response = await authorizedFetch('/api/profiles/my/experiences', {
        method: 'POST',
        body: JSON.stringify(exp),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || 'Failed to add experience')
      }

      return response.json()
    },
    onSuccess: (newExp) => {
      // Update cached profile
      queryClient.setQueryData(['profile'], (oldData: ProfileData | undefined) => {
        if (!oldData) return oldData
        const experiences = Array.isArray(oldData.experiences) ? oldData.experiences : []
        return { ...oldData, experiences: [newExp, ...experiences] }
      })
    },
  })

  // Mutation: update experience
  const updateExperienceMutation = useMutation({
    mutationFn: async ({ id, updates }: { id: string, updates: Partial<Omit<Experience, 'id'>> }): Promise<Experience> => {
      if (!token) throw new Error('Not authenticated')

      const response = await authorizedFetch(`/api/profiles/my/experiences/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || 'Failed to update experience')
      }

      return response.json()
    },
    onSuccess: (updatedExp) => {
      queryClient.setQueryData(['profile'], (oldData: ProfileData | undefined) => {
        if (!oldData || !Array.isArray(oldData.experiences)) return oldData
        const experiences = oldData.experiences.map((e) => e.id === updatedExp.id ? updatedExp : e)
        return { ...oldData, experiences }
      })
    },
  })

  // Mutation: delete experience
  const deleteExperienceMutation = useMutation({
    mutationFn: async (id: string): Promise<string> => {
      if (!token) throw new Error('Not authenticated')

      const response = await authorizedFetch(`/api/profiles/my/experiences/${id}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || 'Failed to delete experience')
      }

      return id
    },
    onSuccess: (deletedId) => {
      queryClient.setQueryData(['profile'], (oldData: ProfileData | undefined) => {
        if (!oldData || !Array.isArray(oldData.experiences)) return oldData
        const experiences = oldData.experiences.filter((e) => e.id !== deletedId)
        return { ...oldData, experiences }
      })
    },
  })

  // Mutation: add skill to experience
  const addExperienceSkillMutation = useMutation({
    mutationFn: async ({ experienceId, skillName }: { experienceId: string, skillName: string }): Promise<Experience> => {
      if (!token) throw new Error('Not authenticated')

      const response = await authorizedFetch(`/api/profiles/my/experiences/${experienceId}/skills`, {
        method: 'POST',
        body: JSON.stringify({ skill_names: [skillName] }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || 'Failed to add skill to experience')
      }

      return response.json()
    },
    onSuccess: (updatedExp) => {
      queryClient.setQueryData(['profile'], (oldData: ProfileData | undefined) => {
        if (!oldData || !Array.isArray(oldData.experiences)) return oldData
        const experiences = oldData.experiences.map((e) => e.id === updatedExp.id ? updatedExp : e)
        return { ...oldData, experiences }
      })
    },
  })

  // Mutation: remove skill from experience
  const removeExperienceSkillMutation = useMutation({
    mutationFn: async ({ experienceId, skillName }: { experienceId: string, skillName: string }): Promise<Experience> => {
      if (!token) throw new Error('Not authenticated')

      const response = await authorizedFetch(`/api/profiles/my/experiences/${experienceId}/skills/${encodeURIComponent(skillName)}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || 'Failed to remove skill from experience')
      }

      return response.json()
    },
    onSuccess: (updatedExp) => {
      queryClient.setQueryData(['profile'], (oldData: ProfileData | undefined) => {
        if (!oldData || !Array.isArray(oldData.experiences)) return oldData
        const experiences = oldData.experiences.map((e) => e.id === updatedExp.id ? updatedExp : e)
        return { ...oldData, experiences }
      })
    },
  })

  return {
    profile: profileQuery.data,
    isLoading: profileQuery.isLoading,
    error: profileQuery.error,
    refetch: profileQuery.refetch,
    updateProfile: updateProfileMutation.mutate,
    isUpdating: updateProfileMutation.isPending,
    updateError: updateProfileMutation.error,
    addExperience: addExperienceMutation.mutate,
    updateExperience: updateExperienceMutation.mutate,
    deleteExperience: deleteExperienceMutation.mutate,
    addExperienceSkill: addExperienceSkillMutation.mutate,
    removeExperienceSkill: removeExperienceSkillMutation.mutate,
  }
}
