import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { PageContainer } from '../ui/page-container'
import { CalendarCheck } from 'lucide-react'

export function ConsultationsPage() {
  return (
    <PageContainer>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <CalendarCheck className="h-5 w-5 mr-2" />
            Consultations
          </CardTitle>
          <CardDescription>
            Schedule and manage healthcare consultations.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Arrange Consultation</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Schedule appointments with healthcare providers.</p>
            </div>
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Prepare for Consultation</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Pre-visit checklists, questions to ask, and preparation materials.</p>
            </div>
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Post-Consultation Notes</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Capture notes, follow-up items, and action plans after visits.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
