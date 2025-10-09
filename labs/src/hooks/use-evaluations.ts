import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from './use-auth'

export interface Evaluation {
  id: string
  profile_id: string
  opportunity_id: string
  final_score: number
  rank_in_set: number
  was_llm_judged: boolean
  llm_reasoning?: string
  structured_score: number
  semantic_score: number
  opportunity_title: string
  opportunity_organisation_name: string
  candidate_name?: string // For employer perspective
}

export interface EvaluationSet {
  id: string
  evaluator_perspective: string
  opportunity_id?: string
  profile_id?: string
  total_evaluated: number
  llm_judged_count: number
  is_complete: boolean
  created_at: string
  evaluations: Evaluation[]
}

export interface MatchResult {
  rank: number
  opportunity_id: string
  role_title: string
  company_name: string
  final_score: number
  structured_score: number
  semantic_score: number
  llm_score?: number
  llm_reasoning?: string
  was_llm_judged: boolean
}

export interface MatchingResponse {
  evaluation_set_id: string
  profile_id: string
  total_opportunities_evaluated: number
  llm_judged_count: number
  top_matches: MatchResult[]
}

export function useEvaluations(profileId?: string, opportunityId?: string) {
  const { token } = useAuth()
  const queryClient = useQueryClient()

  console.log('useEvaluations hook:', { token: !!token, profileId, opportunityId })

  // Query for fetching evaluation sets
  const evaluationsQuery = useQuery({
    queryKey: ['evaluations', profileId || 'all', opportunityId || 'all'],
    queryFn: async (): Promise<EvaluationSet[]> => {
      console.log('useEvaluations: executing query')
      if (!token) throw new Error('Not authenticated')

      const response = await fetch('/api/evaluations/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error('Failed to fetch evaluations')
      }

      const allEvaluationSets: EvaluationSet[] = await response.json()

      // Filter by profileId or opportunityId if provided
      if (profileId) {
        return allEvaluationSets.filter(set =>
          set.evaluations.some(evaluation => evaluation.profile_id === profileId)
        )
      }
      if (opportunityId) {
        return allEvaluationSets.filter(set =>
          set.evaluations.some(evaluation => evaluation.opportunity_id === opportunityId)
        )
      }

      return allEvaluationSets
    },
    enabled: !!token && (!!profileId || !!opportunityId),
  })

  console.log('useEvaluations query state:', {
    isLoading: evaluationsQuery.isLoading,
    error: evaluationsQuery.error,
    data: evaluationsQuery.data ? evaluationsQuery.data.length : 'no data'
  })

  // Mutation for regenerating evaluations (candidate perspective)
  const regenerateMutation = useMutation({
    mutationFn: async ({ profileId, threshold, limit }: {
      profileId: string,
      threshold?: number,
      limit?: number
    }): Promise<MatchingResponse> => {
      if (!token) throw new Error('Not authenticated')

      const response = await fetch(`/api/evaluations/profiles/${profileId}/find-opportunities`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          llm_similarity_threshold: threshold ?? 0.7,
          limit: limit ?? 10,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || 'Failed to regenerate evaluations')
      }

      return response.json()
    },
    onSuccess: () => {
      // Refetch evaluations after successful regeneration
      queryClient.invalidateQueries({ queryKey: ['evaluations', profileId || 'all', opportunityId || 'all'] })
    },
  })

  // Mutation for regenerating evaluations (employer perspective)
  const regenerateForOpportunityMutation = useMutation({
    mutationFn: async ({ opportunityId, threshold, limit, appliedFilter }: {
      opportunityId: string,
      threshold?: number,
      limit?: number,
      appliedFilter?: string
    }): Promise<MatchingResponse> => {
      if (!token) throw new Error('Not authenticated')

      const response = await fetch(`/api/evaluations/opportunities/${opportunityId}/find-candidates`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          llm_similarity_threshold: threshold ?? 0.7,
          limit: limit ?? 10,
          applied_filter: appliedFilter,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || 'Failed to regenerate evaluations')
      }

      return response.json()
    },
    onSuccess: () => {
      // Refetch evaluations after successful regeneration
      queryClient.invalidateQueries({ queryKey: ['evaluations', profileId || 'all', opportunityId || 'all'] })
    },
  })

  return {
    evaluations: evaluationsQuery.data?.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    isLoading: evaluationsQuery.isLoading,
    error: evaluationsQuery.error,
    refetch: evaluationsQuery.refetch,
    regenerate: regenerateMutation.mutate,
    regenerateForOpportunity: regenerateForOpportunityMutation.mutate,
    isRegenerating: regenerateMutation.isPending || regenerateForOpportunityMutation.isPending,
    regenerateError: regenerateMutation.error || regenerateForOpportunityMutation.error,
  }
}
