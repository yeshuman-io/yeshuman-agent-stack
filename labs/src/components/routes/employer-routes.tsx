import { Routes, Route, Navigate } from 'react-router-dom'
import { FocusDashboard } from '../focus-dashboard'
import { Profile } from '../profile'
import { OrganisationProfile } from '../organisation-profile'

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
      <Route path="organisation/:slug" element={<OrganisationProfile />} />
      {/* Add more employer-specific routes here as needed */}
      <Route path="*" element={<Navigate to="" replace />} />
    </Routes>
  )
}
