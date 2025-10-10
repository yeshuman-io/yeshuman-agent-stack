"use client"

import { useState, useEffect } from 'react'
import { useOpportunities } from '../../hooks/use-opportunities'
import { useProfile } from '../../hooks/use-profile'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { Input } from '../ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { PageContainer } from '../ui/page-container'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog'
import { Label } from '../ui/label'
import { Textarea } from '../ui/textarea'
import { Search, Send, RefreshCw, ChevronDown } from 'lucide-react'
import { toast } from 'sonner'

export function BrowseOpportunities() {
  const { profile } = useProfile()
  const [filters, setFilters] = useState({
    q: '',
    organisation: '',
    location: '',
    mode: 'hybrid' as 'keyword' | 'semantic' | 'hybrid',
    page: 1,
    page_size: 20
  })

  const { opportunities, pagination, isLoading, error, loadMore } = useOpportunities(filters)

  // Apply modal state
  const [applyModalOpen, setApplyModalOpen] = useState(false)
  const [selectedOpportunity, setSelectedOpportunity] = useState<any>(null)
  const [screeningQuestions, setScreeningQuestions] = useState<any[]>([])
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

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
  const [applicationStatusMap, setApplicationStatusMap] = useState<Record<string, { status: string; applied_at: string }>>({})

  useEffect(() => {
    const map: Record<string, { status: string; applied_at: string }> = {}

    if (applicationsQuery.data && Array.isArray(applicationsQuery.data)) {
      applicationsQuery.data.forEach((app: any) => {
        if (app.opportunity_id) {
          map[app.opportunity_id] = {
            status: app.status,
            applied_at: app.applied_at
          }
        }
      })
    }

    setApplicationStatusMap(map)
  }, [applicationsQuery.data])

  const handleSearch = (newFilters: Partial<typeof filters>) => {
    setFilters(prev => ({
      ...prev,
      ...newFilters,
      page: 1 // Reset to first page when filters change
    }))
  }

  const handleApplyClick = async (opportunity: any) => {
    // Don't allow applying if already applied
    if (applicationStatusMap[opportunity.id]) {
      return
    }

    setSelectedOpportunity(opportunity)
    setAnswers({})

    // Fetch screening questions for this opportunity
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`/api/opportunities/${opportunity.id}/questions`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const questions = await response.json()
        setScreeningQuestions(questions)
      } else {
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
    if (!selectedOpportunity) return

    // Validate required answers
    if (screeningQuestions.length > 0 && !validateAnswers()) {
      toast.error('Please answer all required questions')
      return
    }

    setIsSubmitting(true)
    try {
      const token = localStorage.getItem('auth_token')
      const requestBody: any = {
        opportunity_id: selectedOpportunity.id
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
        // Refresh applications
        applicationsQuery.refetch()
      } else {
        const error = await response.json()
        toast.error(error.error || 'Failed to submit application')
      }
    } catch (error) {
      toast.error('Failed to submit application')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleLoadMore = () => {
    if (pagination.has_next) {
      setFilters(prev => ({ ...prev, page: prev.page + 1 }))
    }
  }

  return (
    <PageContainer maxWidth="6xl">
      <div className="space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold">Browse Opportunities</h1>
          <p className="text-muted-foreground">
            Discover job opportunities that match your profile and interests.
          </p>
        </div>

        {/* Search and Filters */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              Search & Filter
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="search">Keywords</Label>
                <Input
                  id="search"
                  placeholder="Search job titles, descriptions..."
                  value={filters.q}
                  onChange={(e) => handleSearch({ q: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="organisation">Organisation</Label>
                <Input
                  id="organisation"
                  placeholder="Filter by organisation..."
                  value={filters.organisation}
                  onChange={(e) => handleSearch({ organisation: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="location">Location</Label>
                <Input
                  id="location"
                  placeholder="Filter by location..."
                  value={filters.location}
                  onChange={(e) => handleSearch({ location: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="mode">Search Mode</Label>
                <Select
                  value={filters.mode}
                  onValueChange={(value: 'keyword' | 'semantic' | 'hybrid') => handleSearch({ mode: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="hybrid">Hybrid (Recommended)</SelectItem>
                    <SelectItem value="keyword">Keyword Only</SelectItem>
                    <SelectItem value="semantic">Semantic Only</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Results */}
        {isLoading && opportunities.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
              <p className="text-muted-foreground">Searching opportunities...</p>
            </div>
          </div>
        ) : error ? (
          <Card className="w-full">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <h3 className="text-lg font-medium mb-2 text-destructive">Error Loading Opportunities</h3>
              <p className="text-muted-foreground text-center">{error.message}</p>
            </CardContent>
          </Card>
        ) : opportunities.length === 0 ? (
          <Card className="w-full">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Search className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No Opportunities Found</h3>
              <p className="text-muted-foreground text-center">
                Try adjusting your search criteria to find more opportunities.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-muted-foreground">
                Showing {opportunities.length} of {pagination.total} opportunities
              </p>
            </div>

            <div className="grid gap-4">
              {opportunities.map((opportunity) => (
                <Card key={opportunity.id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <CardTitle className="text-xl">{opportunity.title}</CardTitle>
                        <CardDescription className="text-base">
                          {opportunity.organisation_name}
                        </CardDescription>
                      </div>
                      <div className="flex gap-2">
                        {(() => {
                          const status = applicationStatusMap[opportunity.id]
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
                              onClick={() => handleApplyClick(opportunity)}
                              className="h-8 px-3"
                            >
                              <Send className="h-3 w-3 mr-1" />
                              Apply
                            </Button>
                          )
                        })()}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground mb-4 line-clamp-3">
                      {opportunity.description}
                    </p>

                    {opportunity.skills.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-3">
                        {opportunity.skills.slice(0, 5).map((skill) => (
                          <Badge key={skill.id} variant="secondary" className="text-xs">
                            {skill.skill_name}
                          </Badge>
                        ))}
                        {opportunity.skills.length > 5 && (
                          <Badge variant="outline" className="text-xs">
                            +{opportunity.skills.length - 5} more
                          </Badge>
                        )}
                      </div>
                    )}

                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>{opportunity.experiences.length} experience requirements</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {pagination.has_next && (
              <div className="text-center pt-4">
                <Button
                  variant="outline"
                  onClick={handleLoadMore}
                  disabled={isLoading}
                  className="flex items-center gap-2"
                >
                  {isLoading ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                  Load More Opportunities
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Apply Modal */}
        <Dialog open={applyModalOpen} onOpenChange={setApplyModalOpen}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Apply to Job Opportunity</DialogTitle>
              <DialogDescription>
                {selectedOpportunity && (
                  <>Submit your application for <strong>{selectedOpportunity.title}</strong> at <strong>{selectedOpportunity.organisation_name}</strong>.</>
                )}
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
      </div>
    </PageContainer>
  )
}
