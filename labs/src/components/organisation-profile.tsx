import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ArrowLeft, Building, Globe, Briefcase, Save, Loader2, Edit, X } from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'
import { API_BASE_URL } from '@/constants'
import { OrganisationOpportunities } from './organisation-opportunities'
import { OpportunityForm } from './opportunity-form'
import { OrganisationOpportunity } from '@/hooks/use-organisation-opportunities'

interface Organisation {
  id: string
  name: string
  slug: string
  description: string
  website: string
  industry: string
  created_at: string
  updated_at: string
}

export function OrganisationProfile() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { token } = useAuth()
  const API_URL = API_BASE_URL || '/api'

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    website: '',
    industry: ''
  })
  const [isUpdating, setIsUpdating] = useState(false)
  const [isEditing, setIsEditing] = useState(false)

  // Opportunity management state
  const [activeTab, setActiveTab] = useState('details')
  const [showOpportunityForm, setShowOpportunityForm] = useState(false)
  const [editingOpportunity, setEditingOpportunity] = useState<OrganisationOpportunity | null>(null)

  // Fetch organization data
  const { data: organisation, isLoading, error } = useQuery({
    queryKey: ['organisation', slug],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/organisations/managed/${slug}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      if (!response.ok) {
        throw new Error('Failed to fetch organisation')
      }
      return response.json() as Promise<Organisation>
    },
    enabled: !!slug && !!token
  })

  // Update form when organization data loads
  useEffect(() => {
    if (organisation) {
      setFormData({
        name: organisation.name,
        description: organisation.description,
        website: organisation.website,
        industry: organisation.industry
      })
    }
  }, [organisation])

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleEdit = () => {
    setIsEditing(true)
  }

  const handleCancel = () => {
    // Reset form data to original values
    if (organisation) {
      setFormData({
        name: organisation.name,
        description: organisation.description,
        website: organisation.website,
        industry: organisation.industry
      })
    }
    setIsEditing(false)
  }

  // Opportunity management handlers
  const handleCreateOpportunity = () => {
    setEditingOpportunity(null)
    setShowOpportunityForm(true)
    setActiveTab('opportunities')
  }

  const handleEditOpportunity = (opportunity: OrganisationOpportunity) => {
    setEditingOpportunity(opportunity)
    setShowOpportunityForm(true)
    setActiveTab('opportunities')
  }

  const handleCloseOpportunityForm = () => {
    setShowOpportunityForm(false)
    setEditingOpportunity(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!slug) return

    setIsUpdating(true)
    try {
      const response = await fetch(`${API_URL}/api/organisations/managed/${slug}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to update organisation')
      }

      const updatedOrg = await response.json()

      // Update the cache
      queryClient.setQueryData(['organisation', slug], updatedOrg)
      queryClient.invalidateQueries({ queryKey: ['managed-organisations'] })

      console.log('✅ Organisation updated successfully')
      setIsEditing(false) // Exit edit mode on successful save

    } catch (error) {
      console.error('Failed to update organisation:', error)
      // Could show an alert or error message in the UI here
      alert(error instanceof Error ? error.message : "Failed to update organisation")
    } finally {
      setIsUpdating(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin" />
            <span className="ml-2">Loading organisation...</span>
          </div>
        </div>
      </div>
    )
  }

  if (error || !organisation) {
    return (
      <div className="min-h-screen bg-background p-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-4">Organisation Not Found</h1>
            <p className="text-muted-foreground mb-6">
              The organisation you're looking for doesn't exist or you don't have access to it.
            </p>
            <Button onClick={() => navigate('/employer')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Show opportunity form if requested
  if (showOpportunityForm) {
    return (
      <div className="min-h-screen bg-background p-6">
        <div className="max-w-4xl mx-auto">
          <OpportunityForm
            organisationSlug={slug!}
            organisationName={organisation.name}
            opportunity={editingOpportunity || undefined}
            onClose={handleCloseOpportunityForm}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/employer')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{organisation.name}</h1>
            <p className="text-muted-foreground">Manage your organisation and job opportunities</p>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="details">Organisation Details</TabsTrigger>
            <TabsTrigger value="opportunities">Job Opportunities</TabsTrigger>
          </TabsList>

          <TabsContent value="details" className="space-y-6">
            {/* Organisation Details Form */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Building className="h-5 w-5" />
                      Organisation Details
                    </CardTitle>
                    <CardDescription>
                      {isEditing
                        ? "Update your organisation information. Changes will be reflected across all job postings and communications."
                        : "View your organisation details. Click edit to make changes."
                      }
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    {!isEditing ? (
                      <Button onClick={handleEdit} variant="outline" size="sm">
                        <Edit className="h-4 w-4" />
                      </Button>
                    ) : (
                      <>
                        <Button
                          onClick={handleCancel}
                          variant="outline"
                          size="sm"
                          disabled={isUpdating}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                        <Button
                          onClick={handleSubmit}
                          size="sm"
                          disabled={isUpdating}
                        >
                          {isUpdating ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Save className="h-4 w-4" />
                          )}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {isEditing ? (
                  <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <Label htmlFor="name">Organisation Name</Label>
                        <Input
                          id="name"
                          value={formData.name}
                          onChange={(e) => handleInputChange('name', e.target.value)}
                          placeholder="Enter organisation name"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="industry">Industry</Label>
                        <Input
                          id="industry"
                          value={formData.industry}
                          onChange={(e) => handleInputChange('industry', e.target.value)}
                          placeholder="e.g., Technology, Healthcare, Finance"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="website">Website</Label>
                      <div className="flex">
                        <div className="flex items-center px-3 border border-r-0 border-input bg-muted rounded-l-md">
                          <Globe className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <Input
                          id="website"
                          type="url"
                          value={formData.website}
                          onChange={(e) => handleInputChange('website', e.target.value)}
                          placeholder="https://www.example.com"
                          className="rounded-l-none"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="description">Description</Label>
                      <Textarea
                        id="description"
                        value={formData.description}
                        onChange={(e) => handleInputChange('description', e.target.value)}
                        placeholder="Describe your organisation, its mission, values, and what makes it unique..."
                        rows={4}
                      />
                    </div>
                  </form>
                ) : (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <Label>Organisation Name</Label>
                        <div className="text-sm font-medium p-3 bg-muted rounded-md">
                          {organisation.name}
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label>Industry</Label>
                        <div className="text-sm font-medium p-3 bg-muted rounded-md">
                          {organisation.industry || 'Not specified'}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Website</Label>
                      <div className="flex">
                        <div className="flex items-center px-3 border border-r-0 border-input bg-muted rounded-l-md">
                          <Globe className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <div className="text-sm font-medium p-3 bg-muted rounded-r-md flex-1">
                          {organisation.website ? (
                            <a
                              href={organisation.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary hover:underline"
                            >
                              {organisation.website}
                            </a>
                          ) : (
                            'Not specified'
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Description</Label>
                      <div className="text-sm font-medium p-3 bg-muted rounded-md whitespace-pre-wrap">
                        {organisation.description || 'No description provided.'}
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Organisation Info */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Briefcase className="h-5 w-5" />
                  Organisation Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Slug:</span> {organisation.slug}
                  </div>
                  <div>
                    <span className="font-medium">Created:</span> {new Date(organisation.created_at).toLocaleDateString()}
                  </div>
                  <div>
                    <span className="font-medium">Last Updated:</span> {new Date(organisation.updated_at).toLocaleDateString()}
                  </div>
                  <div>
                    <span className="font-medium">ID:</span> {organisation.id}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="opportunities">
            <OrganisationOpportunities
              organisationSlug={slug!}
              organisationName={organisation.name}
              onCreateOpportunity={handleCreateOpportunity}
              onEditOpportunity={handleEditOpportunity}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
