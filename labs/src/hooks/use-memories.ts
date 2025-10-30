import { useQuery } from '@tanstack/react-query'
import { useAuth } from './use-auth'
import { authorizedFetch } from '@/lib/api'

export interface Memory {
  id: string
  user_id: string
  content: string
  memory_type: string
  interaction_type: string
  category: string
  subcategory: string
  importance: string
  created_at: string
}

export function useMemories() {
  const { token, user } = useAuth()

  const memoriesQuery = useQuery({
    queryKey: ['memories', user?.id],
    queryFn: async (): Promise<Memory[]> => {
      if (!token || !user) throw new Error('Not authenticated')

      const response = await authorizedFetch(`/api/memories/?user_id=${user.id}`)

      if (!response.ok) {
        throw new Error('Failed to fetch memories')
      }

      return response.json()
    },
    enabled: !!token && !!user,
  })

  return {
    memories: memoriesQuery.data || [],
    isLoading: memoriesQuery.isLoading,
    error: memoriesQuery.error,
    refetch: memoriesQuery.refetch,
  }
}




