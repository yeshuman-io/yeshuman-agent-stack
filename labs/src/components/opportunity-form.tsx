import { useState, useEffect } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Textarea } from './ui/textarea'
import { Label } from './ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { ArrowLeft, Save, Loader2 } from 'lucide-react'
import { useOrganisationOpportunities, OrganisationOpportunity, CreateOrganisationOpportunityData, UpdateOrganisationOpportunityData } from '../hooks/use-organisation-opportunities'
import { OpportunitySkillsEditor, OpportunitySkill } from './opportunity-skills-editor'

interface OpportunityFormProps {
  organisationSlug: string
  organisationName: string
  opportunity?: OrganisationOpportunity
  onClose: () => void
}

export function OpportunityForm({
  organisationSlug,
  organisationName,
  opportunity,
  onClose
}: OpportunityFormProps) {
  const { createOpportunity, updateOpportunity, isCreating, isUpdating } = useOrganisationOpportunities(organisationSlug)

  const [formData, setFormData] = useState({
    title: '',
    description: ''
  })
  const [skills, setSkills] = useState<OpportunitySkill[]>([])

  const isEditing = !!opportunity
  const isLoading = isCreating || isUpdating

  useEffect(() => {
    if (opportunity) {
      setFormData({
        title: opportunity.title,
        description: opportunity.description
      })
      setSkills(opportunity.skills.map(s => ({
        skill_id: s.id,
        skill_name: s.skill_name,
        requirement_type: s.requirement_type as 'required' | 'preferred'
      })))
    }
  }, [opportunity])

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.title.trim() || !formData.description.trim()) {
      alert('Please fill in all required fields')
      return
    }

    try {
      if (isEditing && opportunity) {
        const updateData: UpdateOrganisationOpportunityData = {
          title: formData.title,
          description: formData.description
        }
        await updateOpportunity({ id: opportunity.id, data: updateData })
      } else {
        const createData: CreateOrganisationOpportunityData = {
          title: formData.title,
          description: formData.description,
          skills: skills.map(s => ({
            skill_id: s.skill_id,
            requirement_type: s.requirement_type
          }))
        }
        await createOpportunity(createData)
      }
      onClose()
    } catch (error) {
      console.error('Failed to save opportunity:', error)
      alert('Failed to save opportunity. Please try again.')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" onClick={onClose}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <div>
          <h1 className="text-3xl font-bold">
            {isEditing ? 'Edit Job Opportunity' : 'Post New Job'}
          </h1>
          <p className="text-muted-foreground">
            {isEditing ? 'Update the job details' : `Create a job opportunity for ${organisationName}`}
          </p>
        </div>
      </div>

      {/* Form */}
      <Card>
        <CardHeader>
          <CardTitle>Job Details</CardTitle>
          <CardDescription>
            Provide clear and compelling information about this opportunity
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="title">Job Title *</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => handleInputChange('title', e.target.value)}
                placeholder="e.g., Senior Software Engineer"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Job Description *</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                placeholder="Describe the role, responsibilities, requirements, and what makes this opportunity exciting..."
                rows={8}
                required
              />
            </div>

            {/* Form Actions */}
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    {isEditing ? 'Updating...' : 'Posting...'}
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    {isEditing ? 'Update Job' : 'Post Job'}
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Skills Section */}
      <OpportunitySkillsEditor
        skills={skills}
        onSkillsChange={setSkills}
      />
    </div>
  )
}
