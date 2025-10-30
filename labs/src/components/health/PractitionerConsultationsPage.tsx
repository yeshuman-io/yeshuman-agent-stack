import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { PageContainer } from '../ui/page-container'
import { CalendarCheck } from 'lucide-react'

export function PractitionerConsultationsPage() {
  return (
    <PageContainer>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <CalendarCheck className="h-5 w-5 mr-2" />
            Consultations
          </CardTitle>
          <CardDescription>
            Manage your consultation schedule and patient appointments.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Today's Schedule</h3>
              <p className="text-sm text-muted-foreground">Coming soon - View today's appointments and patient schedules.</p>
            </div>
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Upcoming Consultations</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Manage future appointments and consultation requests.</p>
            </div>
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Consultation History</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Review past consultations, notes, and follow-up items.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
