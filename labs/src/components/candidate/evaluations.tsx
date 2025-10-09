"use client"

import { useState, useEffect } from 'react'
import { useEvaluations } from '../../hooks/use-evaluations'
import { useProfile } from '../../hooks/use-profile'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { PageContainer } from '../ui/page-container'
import { Sparkles, RefreshCw, ChevronDown } from 'lucide-react'

export function CandidateEvaluations() {
  const { profile, isLoading: profileLoading, error: profileError } = useProfile()
  const { evaluations, isLoading, error, regenerate, isRegenerating } = useEvaluations(profile?.id)
  const [showCounts, setShowCounts] = useState<Record<string, number>>({})

  // Reset show counts when evaluations data changes (e.g., after regeneration)
  useEffect(() => {
    setShowCounts({})
  }, [evaluations])

  const getShowCount = (evaluationSetId: string) => showCounts[evaluationSetId] ?? 5

  const increaseShowCount = (evaluationSetId: string) => {
    setShowCounts(prev => ({
      ...prev,
      [evaluationSetId]: getShowCount(evaluationSetId) + 10
    }))
  }

  // If profile is still loading, show loading
  if (profileLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading profile...</p>
        </div>
      </div>
    )
  }

  // If there's a profile error, show it
  if (profileError) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Profile Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{profileError.message}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  // If no profile, show auth required
  if (!profile) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Please Login</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              You need to be logged in to view your job evaluations.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const handleRegenerate = () => {
    if (profile?.id) {
      regenerate({ profileId: profile.id })
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading evaluations...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Error Loading Evaluations</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{error.message}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <PageContainer maxWidth="6xl">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Job Evaluations</h1>
            <p className="text-muted-foreground">AI-powered job matching for your profile</p>
          </div>
          <Button
            onClick={handleRegenerate}
            disabled={isRegenerating || !profile?.id}
            className="flex items-center gap-2"
          >
            {isRegenerating ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {isRegenerating ? 'Evaluating...' : 'Run Evaluation'}
          </Button>
        </div>

        {/* Evaluations List */}
        {evaluations && evaluations.length > 0 ? (
          <div className="space-y-4">
            {evaluations.map((evaluationSet) => (
              <Card key={evaluationSet.id} className="w-full">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg">
                        Evaluation Set #{evaluationSet.id.slice(-8)}
                      </CardTitle>
                      <CardDescription>
                        Completed {new Date(evaluationSet.created_at).toLocaleDateString()} •
                        Evaluated {evaluationSet.total_evaluated} opportunities •
                        {evaluationSet.llm_judged_count} AI analyzed
                      </CardDescription>
                    </div>
                    <Badge variant="secondary">
                      {evaluationSet.evaluator_perspective}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {evaluationSet.evaluations.slice(0, getShowCount(evaluationSet.id)).map((evaluation) => (
                      <div key={evaluation.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="text-sm font-medium">
                            #{evaluation.rank_in_set}
                          </div>
                          <div>
                            <div className="font-medium">{evaluation.opportunity_title}</div>
                            <div className="text-sm text-muted-foreground">
                              {evaluation.opportunity_organisation_name}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <div className="text-sm font-medium">
                              {(evaluation.final_score * 100).toFixed(1)}% match
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Structured: {(evaluation.structured_score * 100).toFixed(0)}% •
                              Semantic: {(evaluation.semantic_score * 100).toFixed(0)}%
                            </div>
                          </div>
                          {evaluation.was_llm_judged && (
                            <Badge variant="outline" className="text-xs">
                              AI Reviewed
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                    {evaluationSet.evaluations.length > getShowCount(evaluationSet.id) && (
                      <div className="text-center pt-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => increaseShowCount(evaluationSet.id)}
                          className="flex items-center gap-2"
                        >
                          <ChevronDown className="h-4 w-4" />
                          Show {Math.min(10, evaluationSet.evaluations.length - getShowCount(evaluationSet.id))} more matches
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="w-full">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Sparkles className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No Evaluations Yet</h3>
              <p className="text-muted-foreground text-center mb-4">
                Run your first job evaluation to see how well your profile matches available opportunities.
              </p>
              <Button onClick={handleRegenerate} disabled={!profile?.id}>
                <Sparkles className="h-4 w-4 mr-2" />
                Run First Evaluation
              </Button>
            </CardContent>
          </Card>
        )}
    </PageContainer>
  )
}
