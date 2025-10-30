import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { PageContainer } from '../ui/page-container'
import { Pill } from 'lucide-react'

export function TherapeuticsPage() {
  return (
    <PageContainer>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Pill className="h-5 w-5 mr-2" />
            Therapeutics
          </CardTitle>
          <CardDescription>
            Manage medications, treatments, and therapies.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Medications</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Track prescriptions, dosages, schedules, and medication adherence.</p>
            </div>
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Treatments</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Log therapies, procedures, and treatment plans.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
