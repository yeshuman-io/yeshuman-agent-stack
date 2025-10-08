import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { useOrganisationOpportunities, OrganisationOpportunity } from '../hooks/use-organisation-opportunities'
import { Briefcase, Plus, Edit, Trash2, Calendar, Loader2 } from 'lucide-react'

interface OrganisationOpportunitiesProps {
  organisationSlug: string
  organisationName: string
  onCreateOpportunity?: () => void
  onEditOpportunity?: (opportunity: OrganisationOpportunity) => void
}

export function OrganisationOpportunities({
  organisationSlug,
  organisationName,
  onCreateOpportunity,
  onEditOpportunity
}: OrganisationOpportunitiesProps) {
  const {
    opportunities,
    isLoading,
    error,
    deleteOpportunity,
    isDeleting
  } = useOrganisationOpportunities(organisationSlug)

  const handleDelete = async (opportunityId: string, opportunityTitle: string) => {
    if (window.confirm(`Are you sure you want to delete "${opportunityTitle}"?`)) {
      try {
        await deleteOpportunity(opportunityId)
      } catch (error) {
        console.error('Failed to delete opportunity:', error)
        alert('Failed to delete opportunity. Please try again.')
      }
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading opportunities...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center text-destructive">
        <p>Failed to load opportunities: {error.message}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Job Opportunities</h2>
          <p className="text-muted-foreground">
            Manage job postings for {organisationName}
          </p>
        </div>
        <Button onClick={onCreateOpportunity} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Post New Job
        </Button>
      </div>

      {/* Opportunities List */}
      {opportunities.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center h-64">
            <Briefcase className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No job opportunities yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Create your first job posting to start attracting talent to your organization.
            </p>
            <Button onClick={onCreateOpportunity} variant="outline">
              <Plus className="h-4 w-4 mr-2" />
              Post Your First Job
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {opportunities.map((opportunity) => (
            <Card key={opportunity.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-xl">{opportunity.title}</CardTitle>
                    <CardDescription className="mt-2">
                      {opportunity.description}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onEditOpportunity?.(opportunity)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(opportunity.id, opportunity.title)}
                      disabled={isDeleting}
                    >
                      {isDeleting ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    Posted {new Date(opportunity.created_at).toLocaleDateString()}
                  </div>
                  {opportunity.skills.length > 0 && (
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
                  {opportunity.experiences.length > 0 && (
                    <div>
                      {opportunity.experiences.length} experience requirement{opportunity.experiences.length !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
