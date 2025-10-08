import { useQuery, useMutation } from '@tanstack/react-query'
import { API_BASE_URL } from '../constants'

export interface Skill {
  id: string
  name: string
}

export function useSkills() {
  const API_URL = API_BASE_URL || '/api'
  const fullUrl = API_URL ? `${API_URL}/api/skills` : '/api/skills'

  const skillsQuery = useQuery({
    queryKey: ['skills'],
    queryFn: async (): Promise<Skill[]> => {
      const urlWithSlash = fullUrl.endsWith('/') ? fullUrl : fullUrl + '/'
      const response = await fetch(urlWithSlash)
      if (!response.ok) {
        throw new Error(`Failed to fetch skills: ${response.status}`)
      }
      return response.json()
    },
  })

  const createSkillMutation = useMutation({
    mutationFn: async (skillName: string): Promise<Skill> => {
      const urlWithSlash = fullUrl.endsWith('/') ? fullUrl : fullUrl + '/'
      const response = await fetch(urlWithSlash, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: skillName }),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || `Failed to create skill: ${response.status}`)
      }
      return response.json()
    },
    onSuccess: () => {
      skillsQuery.refetch()
    },
  })

  return {
    skills: skillsQuery.data || [],
    isLoading: skillsQuery.isLoading,
    error: skillsQuery.error,
    createSkill: createSkillMutation.mutate,
    isCreatingSkill: createSkillMutation.isPending,
    createSkillError: createSkillMutation.error,
  }
}
