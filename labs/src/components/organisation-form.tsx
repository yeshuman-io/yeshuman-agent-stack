import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Textarea } from './ui/textarea'
import { Label } from './ui/label'
import { Building2, X, Loader2 } from 'lucide-react'
import { useOrganisations, Organisation, CreateOrganisationData, UpdateOrganisationData } from '../hooks/use-organisations'

interface OrganisationFormProps {
  organisation?: Organisation | null
  onClose: () => void
  onSuccess: () => void
}

export function OrganisationForm({ organisation, onClose, onSuccess }: OrganisationFormProps) {
  const { createOrganisation, updateOrganisation, isCreating, isUpdating } = useOrganisations()

  const [formData, setFormData] = useState({
    name: organisation?.name || '',
    description: organisation?.description || '',
    website: organisation?.website || '',
    industry: organisation?.industry || '',
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  const isEditing = !!organisation
  const isLoading = isCreating || isUpdating

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Organisation name is required'
    }

    if (formData.website && !formData.website.match(/^https?:\/\/.+/)) {
      newErrors.website = 'Website must be a valid URL (include http:// or https://)'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    try {
      if (isEditing && organisation) {
        const updateData: UpdateOrganisationData = {
          name: formData.name,
          description: formData.description,
          website: formData.website,
          industry: formData.industry,
        }
        await updateOrganisation({ slug: organisation.slug, data: updateData })
      } else {
        const createData: CreateOrganisationData = {
          name: formData.name,
          description: formData.description,
          website: formData.website,
          industry: formData.industry,
        }
        await createOrganisation(createData)
      }
      onSuccess()
    } catch (error) {
      console.error('Failed to save organisation:', error)
      // Error handling is done in the hook
    }
  }

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }))
    }
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Building2 className="h-5 w-5" />
            <CardTitle>
              {isEditing ? 'Edit Organisation' : 'Create Organisation'}
            </CardTitle>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <CardDescription>
          {isEditing
            ? 'Update your organisation details'
            : 'Create a new organisation to manage opportunities'
          }
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Organisation Name *</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="Enter organisation name"
              className={errors.name ? 'border-destructive' : ''}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder="Describe your organisation"
              rows={3}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="website">Website</Label>
              <Input
                id="website"
                type="url"
                value={formData.website}
                onChange={(e) => handleChange('website', e.target.value)}
                placeholder="https://example.com"
                className={errors.website ? 'border-destructive' : ''}
              />
              {errors.website && (
                <p className="text-sm text-destructive">{errors.website}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="industry">Industry</Label>
              <Input
                id="industry"
                value={formData.industry}
                onChange={(e) => handleChange('industry', e.target.value)}
                placeholder="e.g., Technology, Healthcare"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {isEditing ? 'Update Organisation' : 'Create Organisation'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
