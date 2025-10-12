import { User, Briefcase, Users, Shield } from 'lucide-react'
import { CURRENT_CLIENT } from '@/constants'

interface FocusHeadingProps {
  focus: 'candidate' | 'employer' | 'recruiter' | 'administrator' | 'admin'
  subtitle?: string
}

export function FocusHeading({ focus, subtitle }: FocusHeadingProps) {
  const getFocusIcon = (focus: string) => {
    switch (focus) {
      case 'candidate':
        return <User className="h-6 w-6 text-primary" />
      case 'employer':
        return <Briefcase className="h-6 w-6 text-primary" />
      case 'recruiter':
        return <Users className="h-6 w-6 text-primary" />
      case 'administrator':
      case 'admin':
        return <Shield className="h-6 w-6 text-primary" />
      default:
        return <User className="h-6 w-6 text-primary" />
    }
  }

  const getFocusLabel = (focus: string) => {
    // Use client-specific naming to match group selection
    const clientName = CURRENT_CLIENT.name.toLowerCase()

    // Map focus names to group names for consistent naming
    const focusToGroupMapping: Record<string, string> = {
      'candidate': 'candidate',
      'employer': 'employer',
      'recruiter': 'recruiter',
      'administrator': 'administrator',  // focus uses 'administrator', groups use 'administrator'
      'admin': 'administrator'
    }

    const groupName = focusToGroupMapping[focus] || focus

    // Check for client-specific naming
    if (clientName === 'talentco') {
      const talentCoNames: Record<string, string> = {
        'candidate': 'Job Seeker',
        'employer': 'Employer',
        'recruiter': 'Talent Partner',
        'administrator': 'System Admin'
      }
      return talentCoNames[groupName] || focus
    }

    // Default naming
    const defaultNames: Record<string, string> = {
      'candidate': 'Job Seeker',
      'employer': 'Employer',
      'recruiter': 'Recruiter',
      'administrator': 'Administrator'
    }

    return defaultNames[groupName] || focus
  }

  const label = getFocusLabel(focus)
  const icon = getFocusIcon(focus)

  return (
    <div className="flex items-center space-x-3">
      <div className="p-2 bg-primary/10 rounded-lg">
        {icon}
      </div>
      <div>
        <h1 className="text-2xl font-bold">{label} Dashboard</h1>
        {subtitle && <p className="text-muted-foreground">{subtitle}</p>}
      </div>
    </div>
  )
}
