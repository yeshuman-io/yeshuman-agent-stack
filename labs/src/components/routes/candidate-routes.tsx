import { Routes, Route, Navigate } from 'react-router-dom'
import { FocusDashboard } from '../focus-dashboard'
import { Profile } from '../profile'
import { CandidateEvaluations } from '../candidate/evaluations'
import { MyApplications } from '../candidate/my-applications'
import { BrowseOpportunities } from '../candidate/browse-opportunities'

interface CandidateRoutesProps {
  onStartConversation?: (message: string) => void
}

export function CandidateRoutes({ onStartConversation }: CandidateRoutesProps) {
  return (
    <Routes>
      <Route
        index
        element={
          <FocusDashboard
            focus="candidate"
            onStartConversation={onStartConversation}
          />
        }
      />
      <Route path="profile" element={<Profile />} />
      <Route path="evaluations" element={<CandidateEvaluations />} />
      <Route path="applications" element={<MyApplications />} />
      <Route path="opportunities" element={<BrowseOpportunities />} />
      {/* Add more candidate-specific routes here as needed */}
      <Route path="*" element={<Navigate to="" replace />} />
    </Routes>
  )
}
