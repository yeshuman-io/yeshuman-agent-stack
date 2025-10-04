import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from './use-auth'

export interface GroupInfo {
  name: string
  display_name: string
  is_assigned: boolean
  can_focus: boolean
}

export function useGroups() {
  const { token } = useAuth()
  const queryClient = useQueryClient()

  // Query for fetching user's groups
  const groupsQuery = useQuery({
    queryKey: ['user-groups'],
    queryFn: async (): Promise<GroupInfo[]> => {
      if (!token) throw new Error('Not authenticated')

      const response = await fetch('/api/accounts/groups', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error('Failed to fetch groups')
      }

      const data = await response.json()
      return data.groups || []
    },
    enabled: !!token,
  })

  // Mutation for updating user groups
  const updateGroupsMutation = useMutation({
    mutationFn: async (groupUpdates: Record<string, boolean>): Promise<{ message: string }> => {
      if (!token) throw new Error('Not authenticated')

      const response = await fetch('/api/accounts/groups', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          group_updates: groupUpdates
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to update groups')
      }

      return response.json()
    },
    onSuccess: () => {
      // Invalidate groups query to refetch
      queryClient.invalidateQueries({ queryKey: ['user-groups'] })
      // Also invalidate focus queries since groups changed
      queryClient.invalidateQueries({ queryKey: ['user-focus'] })
    },
  })

  return {
    groups: groupsQuery.data || [],
    isLoading: groupsQuery.isLoading,
    error: groupsQuery.error,
    updateGroups: updateGroupsMutation.mutate,
    isUpdating: updateGroupsMutation.isPending,
    updateError: updateGroupsMutation.error,
  }
}
