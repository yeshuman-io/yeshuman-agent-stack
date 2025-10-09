import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { PageContainer } from './ui/page-container'
import { Button } from './ui/button'
import {
  User,
  Briefcase,
  Users,
  Shield,
  FileText,
  Search,
  TrendingUp,
  MessageSquare,
  Calendar,
  Settings,
  BarChart3,
  UserCheck,
  Star
} from 'lucide-react'
import { OrganisationList } from './organisation-list'

interface FocusDashboardProps {
  focus: string
  onStartConversation?: (message: string) => void
}

function CandidateDashboard({ onStartConversation }: { onStartConversation?: (message: string) => void }) {
  const quickActions = [
    {
      title: "Build Resume",
      description: "Create or improve your professional resume",
      icon: FileText,
      action: "Help me build a professional resume"
    },
    {
      title: "Job Search",
      description: "Find jobs that match your skills",
      icon: Search,
      action: "Help me find jobs in my field"
    },
    {
      title: "Interview Prep",
      description: "Practice common interview questions",
      icon: MessageSquare,
      action: "Prepare me for job interviews"
    },
    {
      title: "Skill Assessment",
      description: "Identify areas for professional growth",
      icon: TrendingUp,
      action: "Assess my current skills and suggest improvements"
    }
  ]

  const handleQuickAction = (action: string) => {
    onStartConversation?.(action)
  }

  return (
    <PageContainer maxWidth="6xl" padding="p-6" className="space-y-6">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-primary/10 rounded-lg">
          <User className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Job Seeker Dashboard</h1>
          <p className="text-muted-foreground">Find your next opportunity and advance your career</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {quickActions.map((action, index) => (
          <Card key={index} className="cursor-pointer hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-primary/5 rounded-lg">
                  <action.icon className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-lg">{action.title}</CardTitle>
                  <CardDescription>{action.description}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => handleQuickAction(action.action)}
              >
                Get Started
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Star className="h-5 w-5" />
            <span>Your Career Journey</span>
          </CardTitle>
          <CardDescription>
            Track your progress and get personalized recommendations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p>Start a conversation to begin building your career profile</p>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}

function EmployerDashboard({ onStartConversation }: { onStartConversation?: (message: string) => void }) {
  const handleQuickAction = (action: string) => {
    onStartConversation?.(action)
  }

  const quickActions = [
    {
      title: "Post Job",
      description: "Create a compelling job posting",
      icon: Briefcase,
      action: "Help me write a job description"
    },
    {
      title: "Find Candidates",
      description: "Search for qualified applicants",
      icon: Search,
      action: "Help me find candidates for my open positions"
    },
    {
      title: "Interview Planning",
      description: "Prepare for candidate interviews",
      icon: Calendar,
      action: "Help me plan effective interviews"
    },
    {
      title: "Hiring Analytics",
      description: "Track your recruitment metrics",
      icon: BarChart3,
      action: "Analyze my hiring pipeline and success rates"
    }
  ]

  return (
    <PageContainer maxWidth="6xl" padding="p-6" className="space-y-6">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Briefcase className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Employer Dashboard</h1>
          <p className="text-muted-foreground">Manage your organisations and find the best talent</p>
        </div>
      </div>

      {/* Organisation Management */}
      <OrganisationList onStartConversation={onStartConversation} />

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quickActions.map((action, index) => (
            <Card key={index} className="cursor-pointer hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-primary/5 rounded-lg">
                    <action.icon className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">{action.title}</CardTitle>
                    <CardDescription>{action.description}</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => handleQuickAction(action.action)}
                >
                  Get Started
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Analytics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Open Positions</CardTitle>
            <CardDescription>Currently active job postings</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center py-4 text-muted-foreground">
              <p>No active positions</p>
              <Button variant="link" className="mt-2">
                Create your first job posting
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Applications</CardTitle>
            <CardDescription>Candidate responses to your jobs</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center py-4 text-muted-foreground">
              <p>No recent applications</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  )
}

function RecruiterDashboard({ onStartConversation }: { onStartConversation?: (message: string) => void }) {
  const handleQuickAction = (action: string) => {
    onStartConversation?.(action)
  }

  const quickActions = [
    {
      title: "Talent Pipeline",
      description: "Manage your candidate database",
      icon: Users,
      action: "Help me organize my talent pipeline"
    },
    {
      title: "Client Briefs",
      description: "Create job requirements for clients",
      icon: FileText,
      action: "Help me write a client job brief"
    },
    {
      title: "Interview Scheduling",
      description: "Coordinate interviews efficiently",
      icon: Calendar,
      action: "Help me schedule interviews with candidates"
    },
    {
      title: "Placement Tracking",
      description: "Monitor successful placements",
      icon: UserCheck,
      action: "Track my placement success metrics"
    }
  ]

  return (
    <PageContainer maxWidth="6xl" padding="p-6" className="space-y-6">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Users className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Recruiter Dashboard</h1>
          <p className="text-muted-foreground">Connect the right talent with the right opportunities</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {quickActions.map((action, index) => (
          <Card key={index} className="cursor-pointer hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-primary/5 rounded-lg">
                  <action.icon className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-lg">{action.title}</CardTitle>
                  <CardDescription>{action.description}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => handleQuickAction(action.action)}
              >
                Get Started
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Active Searches</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-sm text-muted-foreground">Current placements</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">This Month</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-sm text-muted-foreground">Successful placements</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0%</div>
            <p className="text-sm text-muted-foreground">Placement rate</p>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  )
}

function AdminDashboard({ onStartConversation }: { onStartConversation?: (message: string) => void }) {
  const handleQuickAction = (action: string) => {
    onStartConversation?.(action)
  }

  const quickActions = [
    {
      title: "System Health",
      description: "Monitor platform performance",
      icon: BarChart3,
      action: "Show me system health metrics"
    },
    {
      title: "User Management",
      description: "Manage user accounts and permissions",
      icon: Users,
      action: "Help me manage user accounts"
    },
    {
      title: "Platform Settings",
      description: "Configure system-wide settings",
      icon: Settings,
      action: "Review platform configuration"
    },
    {
      title: "Analytics",
      description: "View usage statistics and reports",
      icon: TrendingUp,
      action: "Show me platform analytics"
    }
  ]

  return (
    <PageContainer maxWidth="6xl" padding="p-6" className="space-y-6">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Shield className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
          <p className="text-muted-foreground">Manage and monitor the platform</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {quickActions.map((action, index) => (
          <Card key={index} className="cursor-pointer hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-primary/5 rounded-lg">
                  <action.icon className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-lg">{action.title}</CardTitle>
                  <CardDescription>{action.description}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => handleQuickAction(action.action)}
              >
                Get Started
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Total Users</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">--</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Active Sessions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">--</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">API Requests</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">--</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">System Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm font-medium">Healthy</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  )
}

export function FocusDashboard({ focus, onStartConversation }: FocusDashboardProps) {
  switch (focus) {
    case 'candidate':
      return <CandidateDashboard onStartConversation={onStartConversation} />
    case 'employer':
      return <EmployerDashboard onStartConversation={onStartConversation} />
    case 'recruiter':
      return <RecruiterDashboard onStartConversation={onStartConversation} />
    case 'admin':
    case 'administrator':
      return <AdminDashboard onStartConversation={onStartConversation} />
    default:
      return (
        <div className="h-full flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <p className="text-lg font-medium mb-2">Welcome to YesHuman</p>
            <p className="text-sm">Please select a focus to get started</p>
          </div>
        </div>
      )
  }
}
