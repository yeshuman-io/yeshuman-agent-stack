"use client"

import { useState, useEffect, useMemo } from 'react'
import { useEvaluations } from '../../hooks/use-evaluations'
import { useProfile } from '../../hooks/use-profile'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { PageContainer } from '../ui/page-container'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog'
import { Label } from '../ui/label'
import { Input } from '../ui/input'
import { Textarea } from '../ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { Sparkles, RefreshCw, ChevronDown, Send } from 'lucide-react'
import { toast } from 'sonner'

export function CandidateEvaluations() {
  const { profile, isLoading: profileLoading, error: profileError } = useProfile()
  const { evaluations, isLoading, error, regenerate, isRegenerating } = useEvaluations(profile?.id)
  const [showCounts, setShowCounts] = useState<Record<string, number>>({})

  // Fetch user's applications to check application status
  const applicationsQuery = useQuery({
    queryKey: ['my-applications'],
    queryFn: async () => {
      const token = localStorage.getItem('auth_token')
      if (!token) throw new Error('Not authenticated')

      const response = await fetch('/api/applications/my', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) throw new Error('Failed to fetch applications')
      return response.json()
    },
    enabled: !!profile?.id,
  })

  // Create a map of opportunity IDs to application status
  const applicationStatusMap = useMemo(() => {
    const map: Record<string, { status: string; applied_at: string }> = {}
    if (applicationsQuery.data) {
      console.log('Applications data:', applicationsQuery.data)
      applicationsQuery.data.forEach((app: any) => {
        console.log('Processing application:', app.opportunity_id, app.status)
        map[app.opportunity_id] = {
          status: app.status,
          applied_at: app.applied_at
        }
      })
      console.log('Application status map:', map)
    }
    return map
  }, [applicationsQuery.data])

  // Apply modal state
  const [applyModalOpen, setApplyModalOpen] = useState(false)
  const [selectedOpportunityId, setSelectedOpportunityId] = useState<string>('')
  const [screeningQuestions, setScreeningQuestions] = useState<any[]>([])
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

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

  const handleApplyClick = async (opportunityId: string) => {
    // Don't allow applying if already applied
    if (applicationStatusMap[opportunityId]) {
      return
    }

    setSelectedOpportunityId(opportunityId)
    setAnswers({})

    // Fetch screening questions for this opportunity
    try {
      const token = localStorage.getItem('auth_token')
      console.log('Fetching questions for opportunity:', opportunityId)
      const response = await fetch(`/api/opportunities/${opportunityId}/questions`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const questions = await response.json()
        console.log('Questions loaded:', questions)
        setScreeningQuestions(questions)
      } else {
        console.log('Questions endpoint returned:', response.status)
        setScreeningQuestions([])
      }
    } catch (error) {
      console.error('Failed to fetch screening questions:', error)
      setScreeningQuestions([])
    }

    setApplyModalOpen(true)
  }

  const handleAnswerChange = (questionId: string, value: any) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }))
  }

  const validateAnswers = () => {
    for (const question of screeningQuestions) {
      if (question.is_required) {
        const answer = answers[question.id]
        if (answer === undefined || answer === null || answer === '') {
          return false
        }
        if (Array.isArray(answer) && answer.length === 0) {
          return false
        }
      }
    }
    return true
  }

  const handleSubmitApplication = async () => {
    if (!selectedOpportunityId) return

    // Validate required answers
    if (screeningQuestions.length > 0 && !validateAnswers()) {
      toast.error('Please answer all required questions')
      return
    }

    setIsSubmitting(true)
    try {
      const token = localStorage.getItem('auth_token')
      console.log('Submitting application:', {
        opportunityId: selectedOpportunityId,
        hasToken: !!token,
        tokenPrefix: token ? token.substring(0, 20) + '...' : 'none',
        screeningQuestionsCount: screeningQuestions.length,
        answersCount: Object.keys(answers).length
      })
      const requestBody: any = {
        opportunity_id: selectedOpportunityId
      }

      if (screeningQuestions.length > 0) {
        requestBody.answers = Object.entries(answers).map(([questionId, value]) => ({
          question_id: questionId,
          answer_text: typeof value === 'string' ? value : typeof value === 'boolean' ? (value ? 'true' : 'false') : '',
          answer_options: Array.isArray(value) ? value : []
        }))
      }

      const response = await fetch('/api/applications/apply', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (response.ok) {
        toast.success('Application submitted successfully!')
        setApplyModalOpen(false)
        // Could refresh evaluations here if needed
      } else {
        const error = await response.json()
        console.error('Application submission error:', error)
        toast.error(error.error || 'Failed to submit application')
      }
    } catch (error) {
      toast.error('Failed to submit application')
    } finally {
      setIsSubmitting(false)
    }
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
                          <div className="flex items-center gap-2">
                            {evaluation.was_llm_judged && (
                              <Badge variant="outline" className="text-xs">
                                AI Reviewed
                              </Badge>
                            )}
                            {(() => {
                              const status = applicationStatusMap[evaluation.opportunity_id]
                              console.log(`Button for opportunity ${evaluation.opportunity_id}:`, status ? 'applied' : 'not applied')
                              return status ? (
                                <Button
                                  size="sm"
                                  disabled
                                  className="h-8 px-3 bg-green-100 text-green-800 hover:bg-green-100"
                                >
                                  <Send className="h-3 w-3 mr-1" />
                                  Applied
                                </Button>
                              ) : (
                                <Button
                                  size="sm"
                                  onClick={() => handleApplyClick(evaluation.opportunity_id)}
                                  className="h-8 px-3"
                                >
                                  <Send className="h-3 w-3 mr-1" />
                                  Apply
                                </Button>
                              )
                            })()}
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

        {/* Apply Modal */}
        <Dialog open={applyModalOpen} onOpenChange={setApplyModalOpen}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Apply to Job Opportunity</DialogTitle>
              <DialogDescription>
                Submit your application with the required information below.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6">
              {screeningQuestions.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">Screening Questions</h3>
                  {screeningQuestions.map((question: any) => (
                    <div key={question.id} className="space-y-2">
                      <Label className="text-sm font-medium">
                        {question.question_text}
                        {question.is_required && <span className="text-destructive ml-1">*</span>}
                      </Label>

                      {question.question_type === 'text' && (
                        <Textarea
                          placeholder="Enter your answer..."
                          value={answers[question.id] || ''}
                          onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                          className="min-h-[80px]"
                        />
                      )}

                      {question.question_type === 'number' && (
                        <Input
                          type="number"
                          placeholder="Enter a number..."
                          value={answers[question.id] || ''}
                          onChange={(e) => handleAnswerChange(question.id, parseInt(e.target.value) || 0)}
                          min={question.config?.validation?.min_value}
                          max={question.config?.validation?.max_value}
                        />
                      )}

                      {question.question_type === 'single_choice' && question.config?.options && (
                        <Select
                          value={answers[question.id] || ''}
                          onValueChange={(value) => handleAnswerChange(question.id, value)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select an option..." />
                          </SelectTrigger>
                          <SelectContent>
                            {question.config.options.map((option: string) => (
                              <SelectItem key={option} value={option}>
                                {option}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}

                      {question.question_type === 'multiple_choice' && question.config?.options && (
                        <div className="space-y-2">
                          {question.config.options.map((option: string) => (
                            <div key={option} className="flex items-center space-x-2">
                              <input
                                type="checkbox"
                                id={`${question.id}-${option}`}
                                checked={(answers[question.id] || []).includes(option)}
                                onChange={(e) => {
                                  const currentAnswers = answers[question.id] || []
                                  if (e.target.checked) {
                                    handleAnswerChange(question.id, [...currentAnswers, option])
                                  } else {
                                    handleAnswerChange(question.id, currentAnswers.filter((a: string) => a !== option))
                                  }
                                }}
                                className="rounded"
                              />
                              <Label htmlFor={`${question.id}-${option}`} className="text-sm">
                                {option}
                              </Label>
                            </div>
                          ))}
                        </div>
                      )}

                      {question.question_type === 'boolean' && (
                        <Select
                          value={answers[question.id] === true ? 'true' : answers[question.id] === false ? 'false' : ''}
                          onValueChange={(value) => handleAnswerChange(question.id, value === 'true')}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select yes or no..." />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="true">Yes</SelectItem>
                            <SelectItem value="false">No</SelectItem>
                          </SelectContent>
                        </Select>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => setApplyModalOpen(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSubmitApplication}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Submit Application
                    </>
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
    </PageContainer>
  )
}
