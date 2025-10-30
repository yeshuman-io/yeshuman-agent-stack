import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { PageContainer } from '../ui/page-container'
import { Users } from 'lucide-react'

export function PatientsPage() {
  return (
    <PageContainer>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Users className="h-5 w-5 mr-2" />
            Patients
          </CardTitle>
          <CardDescription>
            Manage your patient roster and access patient information.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-lg font-medium mb-2">Patient Management</p>
            <p className="text-sm text-muted-foreground">
              Coming soon - View patient lists, access health records, and manage care teams.
            </p>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
