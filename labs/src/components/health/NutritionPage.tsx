import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { PageContainer } from '../ui/page-container'
import { Soup } from 'lucide-react'

export function NutritionPage() {
  return (
    <PageContainer>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Soup className="h-5 w-5 mr-2" />
            Nutrition
          </CardTitle>
          <CardDescription>
            Track your dietary intake and nutritional goals.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Soup className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-lg font-medium mb-2">Nutrition Tracking</p>
            <p className="text-sm text-muted-foreground">
              Coming soon - Log meals, track nutrients, set dietary goals, and monitor eating patterns.
            </p>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
