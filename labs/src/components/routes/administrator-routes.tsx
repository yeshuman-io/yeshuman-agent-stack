import { Routes, Route, Navigate } from 'react-router-dom'
import { FocusDashboard } from '../focus-dashboard'
import { Profile } from '../profile'

interface AdministratorRoutesProps {
  onStartConversation?: (message: string) => void
}

export function AdministratorRoutes({ onStartConversation }: AdministratorRoutesProps) {
  return (
    <Routes>
      <Route
        index
        element={
          <FocusDashboard
            focus="administrator"
            onStartConversation={onStartConversation}
          />
        }
      />
      <Route path="profile" element={<Profile />} />
      {/* Add more administrator-specific routes here as needed */}
      <Route path="*" element={<Navigate to="" replace />} />
    </Routes>
  )
}
