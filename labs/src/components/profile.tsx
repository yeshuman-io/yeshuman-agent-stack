import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Textarea } from './ui/textarea'
import { Badge } from './ui/badge'
import { useProfile, ProfileData } from '../hooks/use-profile'
import { User, MapPin, Plus, X } from 'lucide-react'

export function Profile() {
  const { profile, isLoading, error, updateProfile, isUpdating, updateError } = useProfile()
  const [editing, setEditing] = useState(false)
  const [formData, setFormData] = useState<ProfileData>({})
  const [highlightedFields, setHighlightedFields] = useState<Set<string>>(new Set())
  const [previousProfile, setPreviousProfile] = useState<ProfileData | null>(null)

  // Initialize form data when profile loads
  React.useEffect(() => {
    if (profile) {
      setFormData(profile)
    }
  }, [profile])

  // Track profile changes and highlight card when fields change
  React.useEffect(() => {
    if (profile && previousProfile) {
      const changedFields = new Set<string>()

      // Compare each field in the Personal Information card
      const personalInfoFields = ['first_name', 'last_name', 'bio', 'city', 'country']
      for (const field of personalInfoFields) {
        const oldValue = previousProfile[field as keyof ProfileData]
        const newValue = profile[field as keyof ProfileData]
        if (oldValue !== newValue) {
          changedFields.add(field)
        }
      }

      // Highlight card if any personal info fields changed
      if (changedFields.size > 0) {
        // Add all personal info fields to highlight set to trigger card highlighting
        personalInfoFields.forEach(field => changedFields.add(field))
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
    <div className="h-full overflow-auto p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">My Profile</h1>
            <p className="text-muted-foreground">Manage your professional information</p>
          </div>
          <Button
            onClick={() => {
              setEditing(!editing)
            }}
            variant={editing ? "outline" : "default"}
          >
            {editing ? "Cancel" : "Edit Profile"}
          </Button>
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
        <Card>
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

        {/* Coming Soon */}
        <Card>
          <CardHeader>
            <CardTitle>Coming Soon</CardTitle>
            <CardDescription>Experience, education, and advanced profile features</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              More profile features like work experience, education, and detailed skills will be available soon.
            </p>
          </CardContent>
        </Card>

        {/* Save Button */}
        {editing && (
          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={isUpdating}>
              {isUpdating ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
