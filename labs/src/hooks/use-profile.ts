import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from './use-auth'

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
}

export function useProfile() {
  const { token } = useAuth()
  const queryClient = useQueryClient()

  // Query for fetching profile data
  const profileQuery = useQuery({
    queryKey: ['profile'],
    queryFn: async (): Promise<ProfileData> => {
      if (!token) throw new Error('Not authenticated')

      const response = await fetch('/api/profiles/my', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

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

      const response = await fetch('/api/profiles/my', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
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

  return {
    profile: profileQuery.data,
    isLoading: profileQuery.isLoading,
    error: profileQuery.error,
    refetch: profileQuery.refetch,
    updateProfile: updateProfileMutation.mutate,
    isUpdating: updateProfileMutation.isPending,
    updateError: updateProfileMutation.error,
  }
}
