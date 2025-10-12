import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { PageContainer } from './ui/page-container'
import { Button } from './ui/button'
import { FocusHeading } from './focus-heading'
import { useOrganisations } from '../hooks/use-organisations'
import { useOrganisationOpportunities } from '../hooks/use-organisation-opportunities'
import { FileText } from 'lucide-react'

interface FocusDashboardProps {
  focus: string
  onStartConversation?: (message: string) => void
}

function CandidateDashboard({ onStartConversation: _onStartConversation }: { onStartConversation?: (message: string) => void }) {
  const [applications, setApplications] = useState<any[]>([])
  const [isLoadingApplications, setIsLoadingApplications] = useState(true)
  const [applicationsError, setApplicationsError] = useState<string | null>(null)

  useEffect(() => {
    fetchApplications()
  }, [])

  const fetchApplications = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      if (!token) {
        setApplicationsError('Not authenticated')
        setIsLoadingApplications(false)
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
      setApplicationsError(err instanceof Error ? err.message : 'Failed to load applications')
    } finally {
      setIsLoadingApplications(false)
    }
  }

  const getApplicationCounts = () => {
    const counts = {
      applied: 0,
      in_review: 0,
      interview: 0,
      offer: 0,
      hired: 0,
      rejected: 0,
      total: applications.length
    }

    applications.forEach((app: any) => {
      const status = app.status as keyof typeof counts
      if (status in counts && status !== 'total') {
        counts[status]++
      }
    })

    return counts
  }

  return (
    <PageContainer maxWidth="6xl" padding="p-6" className="space-y-6">
      <FocusHeading
        focus="candidate"
        subtitle="Find your next opportunity and advance your career"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>What you can do now</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              <li>• Browse job opportunities and apply to positions</li>
              <li>• Track your application status and history</li>
              <li>• Run AI-powered matching and evaluations</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Coming soon</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Resume builder and optimization</li>
              <li>• Interview practice and coaching</li>
              <li>• Personalized career recommendations</li>
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <FileText className="h-5 w-5" />
            <span>Application Summary</span>
          </CardTitle>
          <CardDescription>
            Your job application activity and status
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingApplications ? (
            <div className="text-center py-4 text-muted-foreground">
              <p>Loading applications...</p>
            </div>
          ) : applicationsError ? (
            <div className="text-center py-4 text-muted-foreground">
              <p>Unable to load application data</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">{getApplicationCounts().total}</div>
                <p className="text-sm text-muted-foreground">Total Applications</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{getApplicationCounts().applied}</div>
                <p className="text-sm text-muted-foreground">Applied</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">{getApplicationCounts().in_review}</div>
                <p className="text-sm text-muted-foreground">In Review</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{getApplicationCounts().interview}</div>
                <p className="text-sm text-muted-foreground">Interviews</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  )
}

function EmployerDashboard({ onStartConversation: _onStartConversation }: { onStartConversation?: (message: string) => void }) {
  const { organisations, isLoading: orgsLoading, error: orgsError } = useOrganisations()
  const [selectedOrganisation, setSelectedOrganisation] = useState<string>('')
  const { opportunities, isLoading: oppsLoading } = useOrganisationOpportunities(selectedOrganisation)

  // Auto-select first org when available
  useEffect(() => {
    if (organisations && organisations.length > 0 && !selectedOrganisation) {
      setSelectedOrganisation(organisations[0].slug)
    }
  }, [organisations, selectedOrganisation])

  return (
    <PageContainer maxWidth="6xl" padding="p-6" className="space-y-6">
      <FocusHeading
        focus="employer"
        subtitle="Manage your organisations and find the best talent"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>What you can do now</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              <li>• Manage your organisations and teams</li>
              <li>• Post and manage job opportunities</li>
              <li>• Evaluate candidates with AI-powered matching</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Coming soon</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Advanced hiring pipeline analytics</li>
              <li>• Interview scheduling and coordination</li>
              <li>• Team roles and permissions management</li>
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Organization and Opportunity Analytics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Your Organisations</CardTitle>
            <CardDescription>
              Manage your company profiles and teams
            </CardDescription>
          </CardHeader>
          <CardContent>
            {orgsLoading ? (
              <div className="text-center py-4 text-muted-foreground">
                <p>Loading organisations...</p>
              </div>
            ) : orgsError ? (
              <div className="text-center py-4 text-muted-foreground">
                <p>Unable to load organisations</p>
              </div>
            ) : organisations.length > 0 ? (
              <div className="space-y-3">
                <div className="text-2xl font-bold text-primary">{organisations.length}</div>
                <p className="text-sm text-muted-foreground">
                  {organisations.length === 1 ? 'Organisation' : 'Organisations'} managed
                </p>
                {organisations.length > 1 && (
                  <div className="pt-2">
                    <select
                      value={selectedOrganisation}
                      onChange={(e) => setSelectedOrganisation(e.target.value)}
                      className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                    >
                      {organisations.map((org) => (
                        <option key={org.slug} value={org.slug}>
                          {org.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                <p>No organisations found</p>
                <Button variant="link" className="mt-2" size="sm">
                  Create your first organisation
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Job Opportunities</CardTitle>
            <CardDescription>
              Active job postings for your organisations
            </CardDescription>
          </CardHeader>
          <CardContent>
            {selectedOrganisation ? (
              oppsLoading ? (
                <div className="text-center py-4 text-muted-foreground">
                  <p>Loading opportunities...</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="text-2xl font-bold text-primary">{opportunities.length}</div>
                  <p className="text-sm text-muted-foreground">
                    {opportunities.length === 1 ? 'Opportunity' : 'Opportunities'} posted
                  </p>
                  {opportunities.length > 0 && (
                    <div className="pt-2">
                      <Button variant="outline" size="sm" className="w-full">
                        Manage Opportunities
                      </Button>
                    </div>
                  )}
                </div>
              )
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                <p>Select an organisation to view opportunities</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  )
}

function RecruiterDashboard({ onStartConversation: _onStartConversation }: { onStartConversation?: (message: string) => void }) {
  return (
    <PageContainer maxWidth="6xl" padding="p-6" className="space-y-6">
      <FocusHeading
        focus="recruiter"
        subtitle="Connect the right talent with the right opportunities"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>What you can do now</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              <li>• Access your profile and account settings</li>
              <li>• Use AI-powered conversation to assist with tasks</li>
              <li>• Navigate between different focus modes</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Coming soon</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Comprehensive talent pipeline management</li>
              <li>• Client brief creation and management</li>
              <li>• Placement tracking and success metrics</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  )
}

function AdminDashboard({ onStartConversation: _onStartConversation }: { onStartConversation?: (message: string) => void }) {
  return (
    <PageContainer maxWidth="6xl" padding="p-6" className="space-y-6">
      <FocusHeading
        focus="administrator"
        subtitle="Manage and monitor the platform"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>What you can do now</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              <li>• Access your profile and account settings</li>
              <li>• Use AI-powered conversation to assist with tasks</li>
              <li>• Navigate between different focus modes</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Coming soon</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• Comprehensive user account management</li>
              <li>• Active session monitoring and control</li>
              <li>• API usage analytics and rate limiting</li>
              <li>• Platform health monitoring and alerts</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  )
}

export function FocusDashboard({ focus, onStartConversation }: FocusDashboardProps) {
  switch (focus) {
    case 'candidate':
      return <CandidateDashboard onStartConversation={onStartConversation} />
    case 'employer':
      return <EmployerDashboard onStartConversation={onStartConversation} />
    case 'recruiter':
      return <RecruiterDashboard onStartConversation={onStartConversation} />
    case 'admin':
    case 'administrator':
      return <AdminDashboard onStartConversation={onStartConversation} />
    default:
      return (
        <div className="h-full flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <p className="text-lg font-medium mb-2">Welcome to YesHuman</p>
            <p className="text-sm">Please select a focus to get started</p>
          </div>
        </div>
      )
  }
}
