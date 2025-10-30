import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { PageContainer } from '../ui/page-container'
import { FileText } from 'lucide-react'

export function RecordsPage() {
  return (
    <PageContainer>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <FileText className="h-5 w-5 mr-2" />
            Health Records
          </CardTitle>
          <CardDescription>
            Access and manage your medical records and test results.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Medical Records</h3>
              <p className="text-sm text-muted-foreground">Coming soon - View medical history, doctor's notes, and clinical summaries.</p>
            </div>
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-2">Test Results</h3>
              <p className="text-sm text-muted-foreground">Coming soon - Lab results, imaging reports, and diagnostic test outcomes.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
