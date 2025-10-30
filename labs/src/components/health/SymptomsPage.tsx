import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { PageContainer } from '../ui/page-container'
import { Stethoscope } from 'lucide-react'

export function SymptomsPage() {
  return (
    <PageContainer>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Stethoscope className="h-5 w-5 mr-2" />
            Symptoms
          </CardTitle>
          <CardDescription>
            Track and monitor your symptoms over time to identify patterns and trends.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Stethoscope className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-lg font-medium mb-2">Symptom Tracking</p>
            <p className="text-sm text-muted-foreground">
              Coming soon - Log symptoms, track severity, and correlate with other health data.
            </p>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
