import { useState } from 'react'
import { useGroups, GroupInfo } from '../hooks/use-groups'
import { Loader2, User, Briefcase, Shield, Users, Plane, HeartPulse, Stethoscope, Handshake, Headset, Laptop2, Crown } from 'lucide-react'

interface GroupCheckboxesProps {
  onGroupsUpdated?: () => void
  isCollapsed?: boolean
}

const getGroupIcon = (groupName: string) => {
  switch (groupName) {
    case 'candidate':
      return <User className="size-4" />
    case 'employer':
      return <Briefcase className="size-4" />
    case 'recruiter':
      return <Users className="size-4" />
    case 'administrator':
      return <Shield className="size-4" />
    case 'traveler':
      return <Plane className="size-4" />
    case 'agent':
      return <Headset className="size-4" />
    case 'patient':
      return (
        <span className="relative inline-flex">
          <User className="size-4" />
          <HeartPulse className="absolute right-0 bottom-0 size-2 text-red-500" />
        </span>
      )
    case 'practitioner':
      return <Stethoscope className="size-4" />
    case 'client':
      return <Handshake className="size-4" />
    case 'engineer':
      return <Laptop2 className="size-4" />
    case 'principal':
      return <Crown className="size-4" />
    default:
      return <User className="size-4" />
  }
}

export function GroupCheckboxes({ onGroupsUpdated, isCollapsed = false }: GroupCheckboxesProps) {
  const { groups, isLoading, error, updateGroups, isUpdating, updateError } = useGroups()
  const [pendingUpdates, setPendingUpdates] = useState<Record<string, boolean>>({})

  const handleGroupChange = async (group: GroupInfo, checked: boolean) => {
    // Optimistic update
    setPendingUpdates(prev => ({ ...prev, [group.name]: checked }))

    try {
      await updateGroups({ [group.name]: checked })
      // Call callback to notify parent component that groups were updated
      if (onGroupsUpdated) {
        onGroupsUpdated()
      }
    } catch (error) {
      // Revert optimistic update on error
      setPendingUpdates(prev => {
        const newUpdates = { ...prev }
        delete newUpdates[group.name]
        return newUpdates
      })
    }
  }


  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="ml-2 text-xs text-muted-foreground">Loading groups...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-2 py-2 text-xs text-destructive">
        Failed to load groups
      </div>
    )
  }

  if (isCollapsed) {
    // Collapsed state: show icons only
    return (
      <div className="flex flex-col items-center space-y-2 px-2">
        {groups.map((group) => {
          const isChecked = pendingUpdates[group.name] !== undefined
            ? pendingUpdates[group.name]
            : group.is_assigned

          // Job Seeker (candidate) is always checked and cannot be unchecked
          const isRequired = group.name === 'candidate'
          const actuallyChecked = isRequired ? true : isChecked

          return (
            <button
              key={group.name}
              onClick={() => handleGroupChange(group, !actuallyChecked)}
              disabled={isUpdating || isRequired}
              className={`
                flex items-center justify-center w-8 h-8 rounded-md transition-all duration-200
                ${actuallyChecked
                  ? isRequired
                    ? 'bg-primary/20 text-primary border-2 border-primary/40 shadow-sm'
                    : 'bg-primary/10 text-primary border border-primary/20'
                  : 'text-muted-foreground hover:text-foreground opacity-50 hover:opacity-100'
                }
                ${isRequired ? 'cursor-default' : 'cursor-pointer hover:bg-muted/50'}
              `}
              title={`${group.display_name}${isRequired ? ' - Always active - cannot be removed' : ''}`}
            >
              {getGroupIcon(group.name)}
            </button>
          )
        })}
      </div>
    )
  }

  // Expanded state: show checkboxes with labels
  return (
    <div className="space-y-1 px-2">
      {groups.map((group) => {
        const isChecked = pendingUpdates[group.name] !== undefined
          ? pendingUpdates[group.name]
          : group.is_assigned

        // Job Seeker (candidate) is always checked and cannot be unchecked
        const isRequired = group.name === 'candidate'
        const actuallyChecked = isRequired ? true : isChecked

        return (
          <div key={group.name} className="flex items-center space-x-2">
            <button
              onClick={() => handleGroupChange(group, !actuallyChecked)}
              disabled={isUpdating || isRequired}
              className={`
                flex items-center justify-center w-6 h-6 rounded-md transition-all duration-200 shrink-0
                ${actuallyChecked
                  ? isRequired
                    ? 'bg-primary/20 text-primary border border-primary/40'
                    : 'bg-primary/10 text-primary border border-primary/20'
                  : 'text-muted-foreground hover:text-foreground opacity-50 hover:opacity-100 hover:bg-muted/50'
                }
                ${isRequired ? 'cursor-default' : 'cursor-pointer'}
              `}
              title={`${group.display_name}${isRequired ? ' (always active)' : ''}`}
            >
              {getGroupIcon(group.name)}
            </button>
            <span
              onClick={() => !isRequired && handleGroupChange(group, !actuallyChecked)}
              className={`text-xs select-none ${
                isRequired
                  ? 'cursor-default opacity-75 font-medium text-primary'
                  : 'cursor-pointer'
              }`}
              title={isRequired ? 'Always active - cannot be removed' : undefined}
            >
              {group.display_name}
              {isRequired && <span className="text-primary ml-1">*</span>}
            </span>
          </div>
        )
      })}

      {updateError && (
        <div className="px-2 py-1 text-xs text-destructive">
          Failed to update groups
        </div>
      )}
    </div>
  )
}
