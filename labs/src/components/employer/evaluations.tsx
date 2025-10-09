"use client"

import { useState, useEffect } from 'react'
import { useEvaluations } from '../../hooks/use-evaluations'
import { useOrganisations } from '../../hooks/use-organisations'
import { useOrganisationOpportunities } from '../../hooks/use-organisation-opportunities'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { PageContainer } from '../ui/page-container'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import { Sparkles, RefreshCw, ChevronDown, Users, UserPlus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

export function EmployerEvaluations() {
  const navigate = useNavigate()
  const { organisations, isLoading: orgsLoading, error: orgsError } = useOrganisations()
  const [selectedOrganisation, setSelectedOrganisation] = useState<string>('')
  const [selectedOpportunity, setSelectedOpportunity] = useState<string>('')
  const { opportunities, isLoading: oppsLoading } = useOrganisationOpportunities(selectedOrganisation)
  const { evaluations, regenerateForOpportunity, isRegenerating } = useEvaluations(undefined, selectedOpportunity)
  const [showCounts, setShowCounts] = useState<Record<string, number>>({})
  const [appliedFilter, setAppliedFilter] = useState<'all' | 'applied' | 'not_applied'>('all')

  // Reset show counts when evaluations data changes
  useEffect(() => {
    setShowCounts({})
  }, [evaluations])

  // Auto-select first org and first opportunity
  useEffect(() => {
    if (organisations && organisations.length > 0 && !selectedOrganisation) {
      setSelectedOrganisation(organisations[0].slug)
    }
  }, [organisations, selectedOrganisation])

  useEffect(() => {
    if (opportunities && opportunities.length > 0 && !selectedOpportunity) {
      setSelectedOpportunity(opportunities[0].id)
    }
  }, [opportunities, selectedOpportunity])

  const getShowCount = (evaluationSetId: string) => showCounts[evaluationSetId] ?? 5

  const increaseShowCount = (evaluationSetId: string) => {
    setShowCounts(prev => ({
      ...prev,
      [evaluationSetId]: getShowCount(evaluationSetId) + 10
    }))
  }

  const handleRunEvaluation = () => {
    if (selectedOpportunity) {
      regenerateForOpportunity({
        opportunityId: selectedOpportunity,
        threshold: 0.7,
        limit: 10,
        appliedFilter: appliedFilter === 'all' ? undefined : appliedFilter
      })
    }
  }

  const handleInviteCandidate = async (profileId: string, opportunityId: string) => {
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch('/api/applications/invite', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          profile_id: profileId,
          opportunity_id: opportunityId
        }),
      })

      if (response.ok) {
        toast.success('Candidate invited successfully!')
        // Could refresh evaluations here if needed
      } else {
        const error = await response.json()
        toast.error(error.error || 'Failed to invite candidate')
      }
    } catch (error) {
      toast.error('Failed to invite candidate')
    }
  }

  // Filter evaluations to show only those for the selected opportunity
  const filteredEvaluations = evaluations?.filter(evalSet =>
    evalSet.opportunity_id === selectedOpportunity
  )

  // Loading states
  if (orgsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading organisations...</p>
        </div>
      </div>
    )
  }

  if (orgsError) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Failed to load organisations</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Evaluate Candidates</h1>
            <p className="text-muted-foreground">Run AI-powered evaluations for your job opportunities</p>
          </div>
        </div>

        {/* Organisation and Opportunity Selection */}
        <Card>
          <CardHeader>
            <CardTitle>Select Job Opportunity</CardTitle>
            <CardDescription>Choose an organisation and job to evaluate candidates for</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Organisation Selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Organisation</label>
              <Select
                value={selectedOrganisation}
                onValueChange={(value) => {
                  setSelectedOrganisation(value)
                  setSelectedOpportunity('') // Reset opportunity when org changes
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select organisation..." />
                </SelectTrigger>
                <SelectContent>
                  {organisations?.map(org => (
                    <SelectItem key={org.slug} value={org.slug}>{org.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Opportunity Selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Job Opportunity</label>
              {selectedOrganisation && oppsLoading ? (
                <div className="text-sm text-muted-foreground">Loading opportunities...</div>
              ) : opportunities && opportunities.length > 0 ? (
                <Select
                  value={selectedOpportunity}
                  onValueChange={setSelectedOpportunity}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select opportunity..." />
                  </SelectTrigger>
                  <SelectContent>
                    {opportunities.map(opp => (
                      <SelectItem key={opp.id} value={opp.id}>{opp.title}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : selectedOrganisation ? (
                <div className="text-sm text-muted-foreground">
                  No opportunities found.{' '}
                  <button
                    onClick={() => navigate(`/employer/organisation/${selectedOrganisation}`)}
                    className="text-primary hover:underline"
                  >
                    Create your first job opportunity
                  </button>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">Select an organisation first</div>
              )}
            </div>

            {/* Applied Filter Toggle */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Filter Candidates</label>
              <Select
                value={appliedFilter}
                onValueChange={(value: 'all' | 'applied' | 'not_applied') => setAppliedFilter(value)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Filter candidates..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Candidates</SelectItem>
                  <SelectItem value="applied">Applied Candidates</SelectItem>
                  <SelectItem value="not_applied">Not Applied Candidates</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Filter to see only candidates who have or haven't applied to this job
              </p>
            </div>

            {/* Run Evaluation Button */}
            <Button
              onClick={handleRunEvaluation}
              disabled={!selectedOpportunity || isRegenerating}
              className="w-full"
            >
              {isRegenerating ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Running Evaluation...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Run Candidate Evaluation
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Evaluation Results */}
        {filteredEvaluations && filteredEvaluations.length > 0 ? (
          <div className="space-y-4">
            {filteredEvaluations.map((evaluationSet) => (
              <Card key={evaluationSet.id} className="w-full">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg">
                        Evaluation Set #{evaluationSet.id.slice(-8)}
                      </CardTitle>
                      <CardDescription>
                        Completed {new Date(evaluationSet.created_at).toLocaleDateString()} •
                        Evaluated {evaluationSet.total_evaluated} candidates •
                        {evaluationSet.llm_judged_count} AI analyzed
                      </CardDescription>
                    </div>
                    <Badge variant="secondary">
                      Employer Evaluation
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
                            <div className="font-medium">{evaluation.candidate_name || 'Unknown Candidate'}</div>
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
                          <div className="flex items-center gap-2">
                            {evaluation.was_llm_judged && (
                              <Badge variant="outline" className="text-xs">
                                AI Reviewed
                              </Badge>
                            )}
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleInviteCandidate(evaluation.profile_id, selectedOpportunity)}
                              className="h-7 px-2"
                            >
                              <UserPlus className="h-3 w-3 mr-1" />
                              Invite
                            </Button>
                          </div>
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
                          Show {Math.min(10, evaluationSet.evaluations.length - getShowCount(evaluationSet.id))} more candidates
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
              <Users className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No Evaluations Yet</h3>
              <p className="text-muted-foreground text-center mb-4">
                Select an opportunity and run your first candidate evaluation to see how well profiles match your job requirements.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </PageContainer>
  )
}
