import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { PageContainer } from '../ui/page-container'
import { Thermometer } from 'lucide-react'

export function MeasurementsPage() {
  return (
    <PageContainer>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Thermometer className="h-5 w-5 mr-2" />
            Measurements
          </CardTitle>
          <CardDescription>
            Track vital signs and body measurements over time.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Vital Signs</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Blood pressure, heart rate, temperature, and other vital measurements.</p>
            </div>
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Body Measurements</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Weight, BMI, body fat percentage, and measurements over time with trends.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
