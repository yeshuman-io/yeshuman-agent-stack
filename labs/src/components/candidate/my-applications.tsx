"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { PageContainer } from '../ui/page-container'
import { FileText, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

interface Application {
  id: string
  profile_id: string
  opportunity_title: string
  organisation_name: string
  status: 'applied' | 'invited' | 'in_review' | 'interview' | 'offer' | 'hired' | 'rejected' | 'withdrawn'
  source: string
  applied_at: string
  current_stage?: {
    id: string
    stage_name: string
    entered_at: string
    is_open: boolean
  }
}

export function MyApplications() {
  const [applications, setApplications] = useState<Application[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchApplications()
  }, [])

  const fetchApplications = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      if (!token) {
        setError('Not authenticated')
        setIsLoading(false)
        return
      }

      const response = await fetch('/api/applications/my', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error('Failed to fetch applications')
      }

      const data = await response.json()
      setApplications(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load applications')
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'applied':
        return <Clock className="h-4 w-4" />
      case 'invited':
        return <AlertCircle className="h-4 w-4" />
      case 'in_review':
        return <FileText className="h-4 w-4" />
      case 'interview':
        return <CheckCircle className="h-4 w-4" />
      case 'offer':
        return <CheckCircle className="h-4 w-4" />
      case 'hired':
        return <CheckCircle className="h-4 w-4" />
      case 'rejected':
        return <XCircle className="h-4 w-4" />
      case 'withdrawn':
        return <XCircle className="h-4 w-4" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'applied':
        return 'default'
      case 'invited':
        return 'secondary'
      case 'in_review':
        return 'default'
      case 'interview':
        return 'default'
      case 'offer':
        return 'default'
      case 'hired':
        return 'default'
      case 'rejected':
        return 'destructive'
      case 'withdrawn':
        return 'secondary'
      default:
        return 'default'
    }
  }

  const formatStatus = (status: string) => {
    return status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading your applications...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{error}</p>
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
            <h1 className="text-2xl font-bold">My Applications</h1>
            <p className="text-muted-foreground">Track your job applications and invitations</p>
          </div>
        </div>

        {applications.length > 0 ? (
          <div className="space-y-4">
            {applications.map((application) => (
              <Card key={application.id} className="w-full">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-lg">{application.opportunity_title}</CardTitle>
                      <CardDescription>{application.organisation_name}</CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(application.status)}
                      <Badge variant={getStatusColor(application.status)}>
                        {formatStatus(application.status)}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <div>
                      Applied: {formatDate(application.applied_at)}
                      {application.current_stage && (
                        <span className="ml-4">
                          Current Stage: {application.current_stage.stage_name}
                        </span>
                      )}
                    </div>
                    <div className="text-xs">
                      Source: {formatStatus(application.source)}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="w-full">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FileText className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No Applications Yet</h3>
              <p className="text-muted-foreground text-center mb-4">
                You haven't applied to any jobs yet. Browse opportunities and start applying!
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </PageContainer>
  )
}
