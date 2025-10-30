import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { PageContainer } from '../ui/page-container'
import { Activity } from 'lucide-react'

export function ActivityPage() {
  return (
    <PageContainer>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Activity className="h-5 w-5 mr-2" />
            Activity
          </CardTitle>
          <CardDescription>
            Track your physical activity including exercise, sleep, and other wellness activities.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Exercise</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Track workouts, cardio, strength training, and fitness goals.</p>
            </div>
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Sleep</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Monitor sleep patterns, quality, and duration.</p>
            </div>
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Other Activities</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Track meditation, mindfulness, and other wellness activities.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
