import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Textarea } from './ui/textarea'
import { Badge } from './ui/badge'
import { DatePicker } from './ui/date-picker'
import { PageContainer } from './ui/page-container'
import { useProfile, ProfileData, Experience } from '../hooks/use-profile'
import { User, MapPin, Plus, X, Edit, Save, Loader2, Trash2 } from 'lucide-react'

export function Profile() {
  const { profile, isLoading, error, updateProfile, isUpdating, updateError, addExperience, updateExperience, deleteExperience, addExperienceSkill, removeExperienceSkill } = useProfile()
  const [editing, setEditing] = useState(false)
  const [formData, setFormData] = useState<ProfileData>({})
  const [highlightedFields, setHighlightedFields] = useState<Set<string>>(new Set())
  const [previousProfile, setPreviousProfile] = useState<ProfileData | null>(null)

  // Experience UI state
  const [newExperience, setNewExperience] = useState<Partial<Experience>>({ title: '', company: '', start_date: '' })
  const [newExperienceStartDate, setNewExperienceStartDate] = useState<Date>()
  const [newExperienceEndDate, setNewExperienceEndDate] = useState<Date>()
  const [experienceError, setExperienceError] = useState<string | null>(null)
  const [editingExperienceId, setEditingExperienceId] = useState<string | null>(null)
  const [editingExperienceForm, setEditingExperienceForm] = useState<Partial<Experience>>({})
  const [editingStartDate, setEditingStartDate] = useState<Date>()
  const [editingEndDate, setEditingEndDate] = useState<Date>()

  // Experience skills UI state
  const [newSkillInputs, setNewSkillInputs] = useState<Record<string, string>>({}) // experienceId -> skill name input

  // Track profile changes and highlight differences
  React.useEffect(() => {
    if (profile && previousProfile) {
      const changedFields = new Set<string>()

      // Compare each field
      const fieldsToCompare = ['first_name', 'last_name', 'bio', 'city', 'country', 'skills']
      for (const field of fieldsToCompare) {
        const oldValue = previousProfile[field as keyof ProfileData]
        const newValue = profile[field as keyof ProfileData]

        // Handle array comparison for skills
        if (field === 'skills') {
          const oldSkills = Array.isArray(oldValue) ? oldValue : []
          const newSkills = Array.isArray(newValue) ? newValue : []
          if (JSON.stringify(oldSkills.sort()) !== JSON.stringify(newSkills.sort())) {
            changedFields.add('skills')
          }
        } else if (oldValue !== newValue) {
          changedFields.add(field)
        }
      }

      // Highlight changed fields
      if (changedFields.size > 0) {
        setHighlightedFields(changedFields)
        // Fade out highlights after 3 seconds
        setTimeout(() => {
          setHighlightedFields(new Set())
        }, 3000)
      }
    }

    // Update previous profile for next comparison
    if (profile) {
      setPreviousProfile(profile)
    }
  }, [profile, previousProfile])

  // Initialize form data when profile loads
  React.useEffect(() => {
    if (profile) {
      setFormData(profile)
    }
  }, [profile])

  // Note: Profile updates are handled automatically by the useProfile hook
  // through TanStack Query invalidation

  const validateForm = () => {
    if (!formData.first_name?.trim()) {
      return { isValid: false, error: 'First name is required' }
    }
    if (!formData.last_name?.trim()) {
      return { isValid: false, error: 'Last name is required' }
    }
    return { isValid: true, error: null }
  }

  const handleSave = () => {
    const validation = validateForm()
    if (!validation.isValid) {
      // Handle validation error - could show a toast or alert
      console.error('Validation error:', validation.error)
      return
    }

    updateProfile(formData, {
      onSuccess: () => {
        setEditing(false)
      },
    })
  }

  const formatDateRange = (start?: string, end?: string | null) => {
    if (!start) return 'Unknown'
    const startStr = start.slice(0, 7) // YYYY-MM
    const endStr = end ? end.slice(0, 7) : 'Present'
    return `${startStr} - ${endStr}`
  }

  const resetNewExperience = () => {
    setNewExperience({ title: '', company: '', start_date: '', description: '', end_date: '' })
    setNewExperienceStartDate(undefined)
    setNewExperienceEndDate(undefined)
    setExperienceError(null)
  }

  const handleAddExperience = () => {
    setExperienceError(null)
    const { title, company } = newExperience
    if (!title?.trim() || !company?.trim() || !newExperienceStartDate) {
      setExperienceError('Title, company, and start date are required')
      return
    }

    const startDateStr = newExperienceStartDate.toISOString().split('T')[0]
    const endDateStr = newExperienceEndDate ? newExperienceEndDate.toISOString().split('T')[0] : undefined

    addExperience({
      title: title.trim(),
      company: company.trim(),
      start_date: startDateStr,
      description: newExperience.description?.trim() || '',
      end_date: endDateStr,
    })
    resetNewExperience()
  }

  const startEditingExperience = (exp: Experience) => {
    setEditingExperienceId(exp.id)
    setEditingExperienceForm({
      title: exp.title,
      company: exp.company,
      start_date: exp.start_date,
      end_date: exp.end_date || '',
      description: exp.description || '',
    })
    setEditingStartDate(exp.start_date ? new Date(exp.start_date) : undefined)
    setEditingEndDate(exp.end_date ? new Date(exp.end_date) : undefined)
  }

  const cancelEditingExperience = () => {
    setEditingExperienceId(null)
    setEditingExperienceForm({})
    setEditingStartDate(undefined)
    setEditingEndDate(undefined)
  }

  const handleUpdateExperience = (id: string) => {
    const updates: Partial<Experience> = {}
    if (editingExperienceForm.title !== undefined) updates.title = editingExperienceForm.title || ''
    if (editingExperienceForm.company !== undefined) updates.company = editingExperienceForm.company || ''
    if (editingStartDate !== undefined) updates.start_date = editingStartDate ? editingStartDate.toISOString().split('T')[0] : ''
    if (editingEndDate !== undefined) updates.end_date = editingEndDate ? editingEndDate.toISOString().split('T')[0] : undefined
    if (editingExperienceForm.description !== undefined) updates.description = editingExperienceForm.description || ''

    if (!updates.title?.trim() || !updates.company?.trim() || !updates.start_date?.trim()) {
      setExperienceError('Title, company, and start date are required')
      return
    }

    updateExperience({ id, updates })
    cancelEditingExperience()
  }

  const handleDeleteExperience = (id: string) => {
    deleteExperience(id)
  }

  const handleAddExperienceSkill = (experienceId: string) => {
    const skillName = newSkillInputs[experienceId]?.trim()
    if (!skillName) return

    addExperienceSkill({ experienceId, skillName })
    setNewSkillInputs(prev => ({ ...prev, [experienceId]: '' }))
  }

  const handleRemoveExperienceSkill = (experienceId: string, skillName: string) => {
    removeExperienceSkill({ experienceId, skillName })
  }

  const updateSkillInput = (experienceId: string, value: string) => {
    setNewSkillInputs(prev => ({ ...prev, [experienceId]: value }))
  }

  const addSkill = (skill: string) => {
    if (skill.trim() && !formData.skills?.includes(skill.trim())) {
      setFormData((prev: ProfileData) => ({
        ...prev,
        skills: [...(prev.skills || []), skill.trim()]
      }))
    }
  }

  const removeSkill = (skillToRemove: string) => {
    setFormData((prev: ProfileData) => ({
      ...prev,
      skills: prev.skills?.filter((skill: string) => skill !== skillToRemove) || []
    }))
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading profile...</p>
        </div>
      </div>
    )
  }

  return (
    <PageContainer maxWidth="4xl">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">My Profile</h1>
            <p className="text-muted-foreground">Manage your professional information</p>
          </div>
          <div className="flex gap-2">
            {!editing ? (
              <Button
                onClick={() => setEditing(true)}
                variant="default"
              >
                <Edit className="h-4 w-4" />
              </Button>
            ) : (
              <>
                <Button
                  onClick={() => setEditing(false)}
                  variant="outline"
                >
                  <X className="h-4 w-4" />
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={isUpdating}
                >
                  {isUpdating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Messages */}
        {(error || updateError) && (
          <div className="bg-destructive/15 border border-destructive/20 rounded-lg p-4">
            <p className="text-sm text-destructive font-medium">
              {error?.message || updateError?.message || 'An error occurred'}
            </p>
          </div>
        )}

        {/* Personal Information */}
        <Card className={`transition-all duration-300 ${highlightedFields.has('first_name') || highlightedFields.has('last_name') || highlightedFields.has('bio') || highlightedFields.has('city') || highlightedFields.has('country') ? 'ring-2 ring-green-500/50 bg-green-50/10' : ''}`}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Personal Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {editing ? (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="first_name">First Name *</Label>
                    <Input
                      id="first_name"
                      value={formData.first_name || ''}
                      onChange={(e) => setFormData((prev: ProfileData) => ({ ...prev, first_name: e.target.value }))}
                      placeholder="Enter your first name"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name">Last Name *</Label>
                    <Input
                      id="last_name"
                      value={formData.last_name || ''}
                      onChange={(e) => setFormData((prev: ProfileData) => ({ ...prev, last_name: e.target.value }))}
                      placeholder="Enter your last name"
                      required
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="city">City</Label>
                    <Input
                      id="city"
                      value={formData.city || ''}
                      onChange={(e) => setFormData((prev: ProfileData) => ({ ...prev, city: e.target.value }))}
                      placeholder="Enter city"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="country">Country</Label>
                    <Input
                      id="country"
                      value={formData.country || ''}
                      onChange={(e) => setFormData((prev: ProfileData) => ({ ...prev, country: e.target.value }))}
                      placeholder="Enter country"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="bio">Bio</Label>
                  <Textarea
                    id="bio"
                    value={formData.bio || ''}
                    onChange={(e) => setFormData((prev: ProfileData) => ({ ...prev, bio: e.target.value }))}
                    placeholder="Tell us about yourself..."
                    rows={3}
                  />
                </div>
              </>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{profile?.full_name || 'Not set'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">@</span>
                  <span>{profile?.email || 'Not set'}</span>
                </div>
                {(profile?.city || profile?.country) && (
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <span>
                      {[profile.city, profile.country].filter(Boolean).join(', ')}
                    </span>
                  </div>
                )}
                {profile?.bio && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium">About</p>
                    <p className="text-sm text-muted-foreground">{profile.bio}</p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Skills */}
        <Card className={`transition-all duration-300 ${highlightedFields.has('skills') ? 'ring-2 ring-green-500/50 bg-green-50/10' : ''}`}>
          <CardHeader>
            <CardTitle>Skills & Expertise</CardTitle>
            <CardDescription>Showcase your professional skills and technical expertise</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {editing ? (
              <>
                <div className="space-y-3">
                  <div className="flex gap-2">
                    <Input
                      placeholder="e.g., JavaScript, Python, React..."
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          addSkill(e.currentTarget.value)
                          e.currentTarget.value = ''
                        }
                      }}
                      className="flex-1"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={(e) => {
                        const input = e.currentTarget.previousElementSibling as HTMLInputElement
                        if (input.value.trim()) {
                          addSkill(input.value)
                          input.value = ''
                        }
                      }}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Press Enter or click + to add skills. Click X to remove them.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Your Skills</Label>
                  <div className="flex flex-wrap gap-2 min-h-[2rem] p-3 border rounded-md bg-muted/20">
                    {formData.skills && formData.skills.length > 0 ? (
                      formData.skills.map((skill: string) => (
                        <Badge key={skill} variant="secondary" className="flex items-center gap-1 px-3 py-1">
                          {skill}
                          <span title={`Remove ${skill}`}>
                            <X
                              className="h-3 w-3 cursor-pointer hover:text-destructive transition-colors"
                              onClick={() => removeSkill(skill)}
                            />
                          </span>
                        </Badge>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground self-center">No skills added yet</p>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {profile?.skills && profile.skills.length > 0 ? (
                    profile.skills.map((skill) => (
                      <Badge key={skill} variant="outline" className="px-3 py-1">
                        {skill}
                      </Badge>
                    ))
                  ) : (
                    <p className="text-muted-foreground text-sm">No skills added yet</p>
                  )}
                </div>
                {profile?.skills && profile.skills.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {profile.skills.length} skill{profile.skills.length !== 1 ? 's' : ''} listed
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Experience */}
        <Card>
          <CardHeader>
            <CardTitle>Experience</CardTitle>
            <CardDescription>Add and manage your work experience</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {editing ? (
              <>
                {/* Add form */}
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="exp_title">Title *</Label>
                      <Input id="exp_title" value={newExperience.title || ''} onChange={(e) => setNewExperience(prev => ({ ...prev, title: e.target.value }))} placeholder="e.g., Software Engineer" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="exp_company">Company *</Label>
                      <Input id="exp_company" value={newExperience.company || ''} onChange={(e) => setNewExperience(prev => ({ ...prev, company: e.target.value }))} placeholder="e.g., Talentco" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Start Date *</Label>
                      <DatePicker
                        date={newExperienceStartDate}
                        onSelect={setNewExperienceStartDate}
                        placeholder="Select start date"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>End Date (optional)</Label>
                      <DatePicker
                        date={newExperienceEndDate}
                        onSelect={setNewExperienceEndDate}
                        placeholder="Select end date (leave empty for current)"
                        showClearButton={true}
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="exp_desc">Description</Label>
                    <Textarea id="exp_desc" rows={3} value={newExperience.description || ''} onChange={(e) => setNewExperience(prev => ({ ...prev, description: e.target.value }))} placeholder="What did you do?" />
                  </div>
                  {experienceError && (
                    <p className="text-sm text-destructive">{experienceError}</p>
                  )}
                  <div className="flex gap-2">
                    <Button type="button" onClick={handleAddExperience}><Plus className="h-4 w-4 mr-1" /> Add experience</Button>
                    <Button type="button" variant="outline" onClick={resetNewExperience}><X className="h-4 w-4 mr-1" /> Reset</Button>
                  </div>
                </div>

                {/* List with inline edit */}
                <div className="space-y-3">
                  {(profile?.experiences || []).map((exp) => (
                    <div key={exp.id} className="p-3 border rounded-md">
                      {editingExperienceId === exp.id ? (
                        <div className="space-y-3">
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>Title *</Label>
                              <Input value={editingExperienceForm.title || ''} onChange={(e) => setEditingExperienceForm(prev => ({ ...prev, title: e.target.value }))} />
                            </div>
                            <div className="space-y-2">
                              <Label>Company *</Label>
                              <Input value={editingExperienceForm.company || ''} onChange={(e) => setEditingExperienceForm(prev => ({ ...prev, company: e.target.value }))} />
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>Start Date *</Label>
                              <DatePicker
                                date={editingStartDate}
                                onSelect={setEditingStartDate}
                                placeholder="Select start date"
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>End Date</Label>
                              <DatePicker
                                date={editingEndDate}
                                onSelect={setEditingEndDate}
                                placeholder="Select end date (leave empty for current)"
                                showClearButton={true}
                              />
                            </div>
                          </div>
                          <div className="space-y-2">
                            <Label>Description</Label>
                            <Textarea rows={3} value={editingExperienceForm.description || ''} onChange={(e) => setEditingExperienceForm(prev => ({ ...prev, description: e.target.value }))} />
                          </div>
                          {/* Skills management */}
                          <div className="space-y-2">
                            <Label>Skills</Label>
                            <div className="flex flex-wrap gap-2 min-h-[2rem]">
                              {(exp.skills || []).map((skill) => (
                                <Badge key={skill} variant="secondary" className="flex items-center gap-1 px-3 py-1">
                                  {skill}
                                  <span title={`Remove ${skill}`}>
                                    <X
                                      className="h-3 w-3 cursor-pointer hover:text-destructive transition-colors"
                                      onClick={() => handleRemoveExperienceSkill(exp.id, skill)}
                                    />
                                  </span>
                                </Badge>
                              ))}
                            </div>
                            <div className="flex gap-2">
                              <Input
                                placeholder="Add a skill..."
                                value={newSkillInputs[exp.id] || ''}
                                onChange={(e) => updateSkillInput(exp.id, e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    e.preventDefault()
                                    handleAddExperienceSkill(exp.id)
                                  }
                                }}
                                className="flex-1"
                              />
                              <Button
                                type="button"
                                variant="outline"
                                size="icon"
                                onClick={() => handleAddExperienceSkill(exp.id)}
                              >
                                <Plus className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button type="button" onClick={() => handleUpdateExperience(exp.id)}><Save className="h-4 w-4 mr-1" /> Save</Button>
                            <Button type="button" variant="outline" onClick={cancelEditingExperience}><X className="h-4 w-4 mr-1" /> Cancel</Button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-start justify-between gap-3">
                          <div className="space-y-1">
                            <p className="font-medium">{exp.title} <span className="text-muted-foreground">@ {exp.company}</span></p>
                            <p className="text-xs text-muted-foreground">{formatDateRange(exp.start_date, exp.end_date)}</p>
                            {exp.description && (
                              <p className="text-sm text-muted-foreground mt-1">{exp.description}</p>
                            )}
                            {/* Skills display */}
                            {(exp.skills || []).length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {(exp.skills || []).map((skill) => (
                                  <Badge key={skill} variant="outline" className="text-xs px-2 py-0">
                                    {skill}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                          <div className="flex gap-2">
                            <Button type="button" size="icon" variant="outline" onClick={() => startEditingExperience(exp)}><Edit className="h-4 w-4" /></Button>
                            <Button type="button" size="icon" variant="destructive" onClick={() => handleDeleteExperience(exp.id)}><Trash2 className="h-4 w-4" /></Button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                  {(!profile?.experiences || profile.experiences.length === 0) && (
                    <p className="text-sm text-muted-foreground">No experiences added yet</p>
                  )}
                </div>
              </>
            ) : (
              <div className="space-y-3">
                {(profile?.experiences || []).map((exp) => (
                  <div key={exp.id} className="p-3 border rounded-md">
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <p className="font-medium">{exp.title} <span className="text-muted-foreground">@ {exp.company}</span></p>
                        <p className="text-xs text-muted-foreground">{formatDateRange(exp.start_date, exp.end_date)}</p>
                        {exp.description && (
                          <p className="text-sm text-muted-foreground mt-1">{exp.description}</p>
                        )}
                        {/* Skills display */}
                        {(exp.skills || []).length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {(exp.skills || []).map((skill) => (
                              <Badge key={skill} variant="outline" className="text-xs px-2 py-0">
                                {skill}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {(!profile?.experiences || profile.experiences.length === 0) && (
                  <p className="text-sm text-muted-foreground">No experiences added yet</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
    </PageContainer>
  )
}
