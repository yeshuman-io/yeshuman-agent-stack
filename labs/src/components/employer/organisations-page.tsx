import { OrganisationList } from '../organisation-list'
import { PageContainer } from '../ui/page-container'
import { Building2 } from 'lucide-react'

interface EmployerOrganisationsPageProps {
  onStartConversation?: (message: string) => void
}

export function EmployerOrganisationsPage({ onStartConversation }: EmployerOrganisationsPageProps) {
  return (
    <PageContainer maxWidth="6xl" padding="p-6" className="space-y-6">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Building2 className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">My Organisations</h1>
          <p className="text-muted-foreground">Manage your company profiles and job opportunities</p>
        </div>
      </div>

      <OrganisationList onStartConversation={onStartConversation} />
    </PageContainer>
  )
}
