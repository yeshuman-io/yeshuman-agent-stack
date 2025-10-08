import { useState } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Badge } from './ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { X, Plus, Search, Loader2 } from 'lucide-react'
import { useSkills, Skill } from '../hooks/use-skills'

export interface OpportunitySkill {
  skill_id: string
  skill_name: string
  requirement_type: 'required' | 'preferred'
}

interface OpportunitySkillsEditorProps {
  skills: OpportunitySkill[]
  onSkillsChange: (skills: OpportunitySkill[]) => void
}

export function OpportunitySkillsEditor({ skills, onSkillsChange }: OpportunitySkillsEditorProps) {
  const { skills: availableSkills, isLoading, error, createSkill, isCreatingSkill, createSkillError } = useSkills()
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedSkillId, setSelectedSkillId] = useState('')
  const [requirementType, setRequirementType] = useState<'required' | 'preferred'>('required')
  const [newSkillName, setNewSkillName] = useState('')
  const [showCreateSkill, setShowCreateSkill] = useState(false)

  const filteredSkills = availableSkills.filter(skill =>
    skill.name.toLowerCase().includes(searchTerm.toLowerCase()) &&
    !skills.some(s => s.skill_id === skill.id)
  )

  const handleAddSkill = () => {
    if (!selectedSkillId) return

    const selectedSkill = availableSkills.find(s => s.id === selectedSkillId)
    if (!selectedSkill) return

    const newSkill: OpportunitySkill = {
      skill_id: selectedSkill.id,
      skill_name: selectedSkill.name,
      requirement_type: requirementType
    }

    onSkillsChange([...skills, newSkill])
    setSelectedSkillId('')
    setSearchTerm('')
    setRequirementType('required')
  }

  const handleRemoveSkill = (skillId: string) => {
    onSkillsChange(skills.filter(s => s.skill_id !== skillId))
  }

  const handleCreateNewSkill = async () => {
    if (!newSkillName.trim()) return

    try {
      const newSkill = await new Promise<Skill>((resolve, reject) => {
        createSkill(newSkillName.trim(), {
          onSuccess: (skill) => resolve(skill),
          onError: (error) => reject(error),
        })
      })

      // Add the new skill to the opportunity
      const newOpportunitySkill: OpportunitySkill = {
        skill_id: newSkill.id,
        skill_name: newSkill.name,
        requirement_type: requirementType
      }

      onSkillsChange([...skills, newOpportunitySkill])
      setNewSkillName('')
      setShowCreateSkill(false)
      setRequirementType('required')
    } catch (error) {
      console.error('Failed to create skill:', error)
      // Error is handled by the mutation
    }
  }

  const handleUpdateRequirementType = (skillId: string, newType: 'required' | 'preferred') => {
    onSkillsChange(skills.map(s =>
      s.skill_id === skillId ? { ...s, requirement_type: newType } : s
    ))
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Required Skills</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Add Skill Section */}
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="space-y-2">
              <Label htmlFor="skill-search">Search Skills</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="skill-search"
                  placeholder="Search skills..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Select Skill</Label>
              <div className="max-h-32 overflow-y-auto border rounded-md p-2">
                {error ? (
                  <p className="text-sm text-destructive">Error loading skills: {error.message}</p>
                ) : isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading skills...</p>
                ) : availableSkills.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No skills available in system</p>
                ) : filteredSkills.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    {searchTerm ? `No skills match "${searchTerm}"` : 'All skills already added'}
                  </p>
                ) : (
                  <div className="space-y-1">
                    {filteredSkills.map((skill) => (
                      <button
                        key={skill.id}
                        type="button"
                        onClick={() => setSelectedSkillId(skill.id)}
                        className={`w-full text-left px-2 py-1 rounded text-sm hover:bg-accent ${
                          selectedSkillId === skill.id ? 'bg-accent' : ''
                        }`}
                      >
                        {skill.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Requirement Type</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={requirementType === 'required' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setRequirementType('required')}
                >
                  Required
                </Button>
                <Button
                  type="button"
                  variant={requirementType === 'preferred' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setRequirementType('preferred')}
                >
                  Preferred
                </Button>
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              type="button"
              onClick={handleAddSkill}
              disabled={!selectedSkillId}
              className="flex-1 md:flex-none"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Skill
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowCreateSkill(!showCreateSkill)}
              className="flex-1 md:flex-none"
            >
              Create New
            </Button>
          </div>
        </div>

        {/* Create New Skill Section */}
        {showCreateSkill && (
          <div className="space-y-3 border-t pt-4">
            <div className="space-y-2">
              <Label htmlFor="new-skill-name">Create New Skill</Label>
              <Input
                id="new-skill-name"
                placeholder="Enter skill name..."
                value={newSkillName}
                onChange={(e) => setNewSkillName(e.target.value)}
                disabled={isCreatingSkill}
              />
              {createSkillError && (
                <p className="text-sm text-destructive">
                  {createSkillError.message || 'Failed to create skill'}
                </p>
              )}
            </div>

            <div className="flex gap-2">
              <Button
                type="button"
                onClick={handleCreateNewSkill}
                disabled={!newSkillName.trim() || isCreatingSkill}
                className="flex-1"
              >
                {isCreatingSkill ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Create & Add Skill
                  </>
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShowCreateSkill(false)
                  setNewSkillName('')
                }}
                disabled={isCreatingSkill}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Selected Skills */}
        {skills.length > 0 && (
          <div className="space-y-2">
            <Label>Selected Skills</Label>
            <div className="flex flex-wrap gap-2">
              {skills.map((skill) => (
                <div key={skill.skill_id} className="flex items-center gap-2 bg-muted rounded-lg p-2">
                  <span className="text-sm font-medium">{skill.skill_name}</span>
                  <div className="flex gap-1">
                    <Button
                      type="button"
                      variant={skill.requirement_type === 'required' ? 'default' : 'outline'}
                      size="sm"
                      className="h-6 px-2 text-xs"
                      onClick={() => handleUpdateRequirementType(skill.skill_id, 'required')}
                    >
                      Req
                    </Button>
                    <Button
                      type="button"
                      variant={skill.requirement_type === 'preferred' ? 'default' : 'outline'}
                      size="sm"
                      className="h-6 px-2 text-xs"
                      onClick={() => handleUpdateRequirementType(skill.skill_id, 'preferred')}
                    >
                      Pref
                    </Button>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveSkill(skill.skill_id)}
                    className="h-6 w-6 p-0"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {skills.length === 0 && (
          <div className="text-center text-muted-foreground py-8">
            <p>No skills added yet. Add required and preferred skills for this opportunity.</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
