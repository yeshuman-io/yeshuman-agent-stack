import { Routes, Route, Navigate } from 'react-router-dom'
import { FocusDashboard } from '../focus-dashboard'
import { Profile } from '../profile'
import { OrganisationProfile } from '../organisation-profile'
import { EmployerEvaluations } from '../employer/evaluations'
import { EmployerOrganisationsPage } from '../employer/organisations-page'
import { EmployerOpportunitiesPage } from '../employer/opportunities-page'

interface EmployerRoutesProps {
  onStartConversation?: (message: string) => void
}

export function EmployerRoutes({ onStartConversation }: EmployerRoutesProps) {
  return (
    <Routes>
      <Route
        index
        element={
          <FocusDashboard
            focus="employer"
            onStartConversation={onStartConversation}
          />
        }
      />
      <Route path="profile" element={<Profile />} />
      <Route path="organisations" element={<EmployerOrganisationsPage onStartConversation={onStartConversation} />} />
      <Route path="opportunities" element={<EmployerOpportunitiesPage onStartConversation={onStartConversation} />} />
      <Route path="organisations/:slug/opportunities" element={<EmployerOpportunitiesPage onStartConversation={onStartConversation} />} />
      <Route path="organisation/:slug" element={<OrganisationProfile />} />
      <Route path="evaluations" element={<EmployerEvaluations />} />
      {/* Add more employer-specific routes here as needed */}
      <Route path="*" element={<Navigate to="" replace />} />
    </Routes>
  )
}
