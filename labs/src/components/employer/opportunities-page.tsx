import { useState, useEffect } from 'react'
import { useSearchParams, useParams } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { Badge } from '../ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog'
import { PageContainer } from '../ui/page-container'
import { useOpportunities } from '../../hooks/use-opportunities'
import { useOrganisations } from '../../hooks/use-organisations'
import { OpportunityForm } from '../opportunity-form'
import { OrganisationOpportunity } from '../../hooks/use-organisation-opportunities'
import { Plus, Search, Filter, Edit, Briefcase, Building2, Calendar } from 'lucide-react'

interface EmployerOpportunitiesPageProps {
  onStartConversation?: (message: string) => void
}

export function EmployerOpportunitiesPage({}: EmployerOpportunitiesPageProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const { slug: orgSlug } = useParams<{ slug: string }>()

  // Filters
  const [filters, setFilters] = useState({
    q: searchParams.get('q') || '',
    organisation: orgSlug || searchParams.get('organisation') || '',
    page: parseInt(searchParams.get('page') || '1'),
    page_size: 20,
  })

  // Modal state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingOpportunity, setEditingOpportunity] = useState<OrganisationOpportunity | null>(null)

  // Data
  const { opportunities, pagination, isLoading, error } = useOpportunities(filters)
  const { organisations } = useOrganisations()

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams()
    if (filters.q) params.set('q', filters.q)
    if (filters.organisation) params.set('organisation', filters.organisation)
    if (filters.page > 1) params.set('page', filters.page.toString())
    setSearchParams(params)
  }, [filters, setSearchParams])

  const handleFilterChange = (key: string, value: string | number): void => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: 1, // Reset to first page when filters change
    }))
  }

  const handleCreateOpportunity = (): void => {
    setShowCreateModal(true)
  }

  const handleEditOpportunity = (opportunity: any): void => {
    // Convert to OrganisationOpportunity format for the form
    const orgOpportunity: OrganisationOpportunity = {
      id: opportunity.id,
      title: opportunity.title,
      description: opportunity.description,
      skills: opportunity.skills,
      experiences: opportunity.experiences,
      created_at: opportunity.created_at,
      updated_at: opportunity.updated_at,
    }
    setEditingOpportunity(orgOpportunity)
  }

  const handleCloseModal = (): void => {
    setShowCreateModal(false)
    setEditingOpportunity(null)
  }

  const getOrganisationName = (orgSlug: string): string => {
    const org = organisations.find(o => o.slug === orgSlug)
    return org?.name || orgSlug
  }

  return (
    <PageContainer maxWidth="7xl" padding="p-6" className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Briefcase className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Job Opportunities</h1>
            <p className="text-muted-foreground">
              {orgSlug
                ? `Manage jobs for ${getOrganisationName(orgSlug)}`
                : 'Manage all your job postings'
              }
            </p>
          </div>
        </div>
        <Button onClick={handleCreateOpportunity} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Post New Job
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search job titles..."
                  value={filters.q}
                  onChange={(e) => handleFilterChange('q', e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="organisation">Organisation</Label>
              <Select
                value={filters.organisation}
                onValueChange={(value) => handleFilterChange('organisation', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All organisations" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All organisations</SelectItem>
                  {organisations.map((org) => (
                    <SelectItem key={org.slug} value={org.slug}>
                      {org.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select defaultValue="">
                <SelectTrigger>
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All statuses</SelectItem>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="published">Published</SelectItem>
                  <SelectItem value="closed">Closed</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Opportunities Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            Jobs ({pagination.total})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-muted-foreground">Loading opportunities...</div>
            </div>
          ) : error ? (
            <div className="text-center text-destructive">
              <p>Failed to load opportunities: {error.message}</p>
            </div>
          ) : opportunities.length === 0 ? (
            <div className="text-center py-12">
              <Briefcase className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No job opportunities found</h3>
              <p className="text-muted-foreground mb-4">
                {filters.q || filters.organisation
                  ? 'Try adjusting your filters or create a new job posting.'
                  : 'Create your first job posting to start attracting talent.'
                }
              </p>
              <Button onClick={handleCreateOpportunity} variant="outline">
                <Plus className="h-4 w-4 mr-2" />
                Post Your First Job
              </Button>
            </div>
          ) : (
            <div className="grid gap-4">
              {opportunities.map((opportunity) => (
                <Card key={opportunity.id}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-xl">{opportunity.title}</CardTitle>
                        <CardDescription className="mt-2 line-clamp-2">
                          {opportunity.description}
                        </CardDescription>
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <Badge variant="secondary">Published</Badge>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEditOpportunity(opportunity)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Building2 className="h-4 w-4" />
                        {opportunity.organisation_name}
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        Active job posting
                      </div>
                      {opportunity.skills && opportunity.skills.length > 0 && (
                        <div className="flex items-center gap-2">
                          <span>Skills:</span>
                          <div className="flex gap-1">
                            {opportunity.skills.slice(0, 3).map((skill) => (
                              <Badge key={skill.id} variant="secondary" className="text-xs">
                                {skill.skill_name}
                              </Badge>
                            ))}
                            {opportunity.skills.length > 3 && (
                              <Badge variant="secondary" className="text-xs">
                                +{opportunity.skills.length - 3} more
                              </Badge>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Modal */}
      <Dialog open={showCreateModal || !!editingOpportunity} onOpenChange={handleCloseModal}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingOpportunity ? 'Edit Job Opportunity' : 'Post New Job'}
            </DialogTitle>
          </DialogHeader>
          <OpportunityForm
            organisationSlug={filters.organisation || organisations[0]?.slug || ''}
            organisationName={filters.organisation ? getOrganisationName(filters.organisation) : organisations[0]?.name || ''}
            opportunity={editingOpportunity || undefined}
            onClose={handleCloseModal}
          />
        </DialogContent>
      </Dialog>
    </PageContainer>
  )
}
