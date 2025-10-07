import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Building2, Edit, Trash2, Plus, ExternalLink } from 'lucide-react'
import { useOrganisations, Organisation } from '../hooks/use-organisations'
import { OrganisationForm } from './organisation-form'

interface OrganisationListProps {
  onStartConversation?: (message: string) => void
}

export function OrganisationList({ onStartConversation }: OrganisationListProps) {
  const navigate = useNavigate()
  const {
    organisations,
    isLoading,
    error,
    deleteOrganisation,
    isDeleting
  } = useOrganisations()

  const [editingOrg, setEditingOrg] = useState<Organisation | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)

  const handleDelete = async (slug: string, name: string) => {
    if (window.confirm(`Are you sure you want to delete "${name}"? This action cannot be undone.`)) {
      try {
        await deleteOrganisation(slug)
      } catch (error) {
        console.error('Failed to delete organisation:', error)
      }
    }
  }

  const handleManageOpportunities = (org: Organisation) => {
    onStartConversation?.(`Help me manage opportunities for ${org.name}`)
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Building2 className="h-5 w-5" />
            <span>My Organisations</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-muted-foreground">Loading organisations...</div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Building2 className="h-5 w-5" />
            <span>My Organisations</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-destructive">Failed to load organisations</div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <Building2 className="h-5 w-5" />
                <span>My Organisations</span>
              </CardTitle>
              <CardDescription>
                Manage your organisations and their opportunities
              </CardDescription>
            </div>
            <Button onClick={() => setShowCreateForm(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Organisation
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {organisations.length === 0 ? (
            <div className="text-center py-8">
              <Building2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No organisations yet</h3>
              <p className="text-muted-foreground mb-4">
                Create your first organisation to start posting opportunities
              </p>
              <Button onClick={() => setShowCreateForm(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Organisation
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {organisations.map((org) => (
                <Card
                  key={org.id}
                  className="hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => navigate(`/employer/organisation/${org.slug}`)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-lg">{org.name}</CardTitle>
                        <CardDescription className="flex items-center space-x-1 mt-1">
                          <span>/{org.slug}</span>
                        </CardDescription>
                      </div>
                      <Badge variant="secondary" className="ml-2">
                        {org.industry || 'General'}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {org.description && (
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {org.description}
                      </p>
                    )}

                    {org.website && (
                      <div className="flex items-center space-x-1">
                        <ExternalLink className="h-3 w-3 text-muted-foreground" />
                        <a
                          href={org.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-primary hover:underline"
                        >
                          {org.website}
                        </a>
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-2">
                      <div className="flex space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleManageOpportunities(org)}
                        >
                          Manage Opportunities
                        </Button>
                      </div>

                      <div className="flex space-x-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditingOrg(org)}
                        >
                          <Edit className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(org.slug, org.name)}
                          disabled={isDeleting}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Organisation Form */}
      {showCreateForm && (
        <OrganisationForm
          onClose={() => setShowCreateForm(false)}
          onSuccess={() => setShowCreateForm(false)}
        />
      )}

      {/* Edit Organisation Form */}
      {editingOrg && (
        <OrganisationForm
          organisation={editingOrg}
          onClose={() => setEditingOrg(null)}
          onSuccess={() => setEditingOrg(null)}
        />
      )}
    </div>
  )
}
