import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Textarea } from './ui/textarea'
import { Badge } from './ui/badge'
import { useAuth } from '../hooks/use-auth'
import { User, MapPin, Plus, X } from 'lucide-react'

interface ProfileData {
  id?: string
  full_name?: string
  email?: string
  bio?: string
  city?: string
  country?: string
  location?: string
  skills?: string[]
  first_name?: string
  last_name?: string
}

export function Profile() {
  const { token } = useAuth()
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(false)
  const [formData, setFormData] = useState<ProfileData>({})
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchProfile()
  }, [token])

  const fetchProfile = async () => {
    if (!token) return

    try {
      setError(null)
      const response = await fetch('/api/profiles/my', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const data = await response.json()
        setProfile(data)
        setFormData(data)
      } else if (response.status === 401) {
        setError('Authentication required. Please log in again.')
      } else {
        setError('Failed to load profile. Please try again.')
      }
    } catch (error) {
      console.error('Failed to fetch profile:', error)
      setError('Network error. Please check your connection.')
    } finally {
      setLoading(false)
    }
  }

  const validateForm = () => {
    if (!formData.first_name?.trim()) {
      setError('First name is required')
      return false
    }
    if (!formData.last_name?.trim()) {
      setError('Last name is required')
      return false
    }
    return true
  }

  const handleSave = async () => {
    if (!token) return

    if (!validateForm()) return

    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch('/api/profiles/my', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })

      if (response.ok) {
        const updatedProfile = await response.json()
        setProfile(updatedProfile)
        setEditing(false)
        setSuccess('Profile updated successfully!')
        // Clear success message after 3 seconds
        setTimeout(() => setSuccess(null), 3000)
      } else if (response.status === 401) {
        setError('Authentication required. Please log in again.')
      } else {
        const errorData = await response.json().catch(() => ({}))
        setError(errorData.error || 'Failed to save profile. Please try again.')
      }
    } catch (error) {
      console.error('Failed to save profile:', error)
      setError('Network error. Please check your connection and try again.')
    } finally {
      setSaving(false)
    }
  }

  const addSkill = (skill: string) => {
    if (skill.trim() && !formData.skills?.includes(skill.trim())) {
      setFormData(prev => ({
        ...prev,
        skills: [...(prev.skills || []), skill.trim()]
      }))
    }
  }

  const removeSkill = (skillToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills?.filter(skill => skill !== skillToRemove) || []
    }))
  }

  if (loading) {
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
              setError(null)
              setSuccess(null)
            }}
            variant={editing ? "outline" : "default"}
          >
            {editing ? "Cancel" : "Edit Profile"}
          </Button>
        </div>

        {/* Messages */}
        {error && (
          <div className="bg-destructive/15 border border-destructive/20 rounded-lg p-4">
            <p className="text-sm text-destructive font-medium">{error}</p>
          </div>
        )}

        {success && (
          <div className="bg-green-500/15 border border-green-500/20 rounded-lg p-4">
            <p className="text-sm text-green-700 dark:text-green-400 font-medium">{success}</p>
          </div>
        )}

        {/* Personal Information */}
        <Card>
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
                      onChange={(e) => setFormData(prev => ({ ...prev, first_name: e.target.value }))}
                      placeholder="Enter your first name"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name">Last Name *</Label>
                    <Input
                      id="last_name"
                      value={formData.last_name || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, last_name: e.target.value }))}
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
                      onChange={(e) => setFormData(prev => ({ ...prev, city: e.target.value }))}
                      placeholder="Enter city"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="country">Country</Label>
                    <Input
                      id="country"
                      value={formData.country || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, country: e.target.value }))}
                      placeholder="Enter country"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="bio">Bio</Label>
                  <Textarea
                    id="bio"
                    value={formData.bio || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, bio: e.target.value }))}
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
                      formData.skills.map((skill) => (
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
            <Button onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
