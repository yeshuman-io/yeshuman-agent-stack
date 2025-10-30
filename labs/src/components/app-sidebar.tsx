import { MessageSquare, Bot, LogOut, LogIn, User, Trash2, Plane, Leaf, Heart, HeartPulse, Briefcase, Shield, Search, FileText, Users, Settings, Sparkles, Building2, Handshake, Headset, Laptop2, Stethoscope, Crown, Brain, Activity, Pill, Soup, CalendarCheck, Thermometer } from "lucide-react"
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar"
import { LoginDialog } from "@/components/login-dialog"
import { GroupCheckboxes } from "@/components/group-checkboxes"
import { authorizedFetch } from "@/lib/api"
import { useAuth } from "@/hooks/use-auth"
import { CURRENT_CLIENT, CLIENT_CONFIG } from "@/constants"

// Helper function to get the appropriate icon component
const getBrandIcon = (iconName: string) => {
  switch (iconName) {
    case 'Bot':
      return Bot;
    case 'Plane':
      return Plane;
    case 'Leaf':
      return Leaf;
    case 'Heart':
      return Heart;
    default:
      return Bot; // fallback to Bot
  }
};

// Thread interface
interface Thread {
  id: string
  subject: string
  created_at: string
  updated_at: string
}

interface AppSidebarProps {
  onThreadSelect?: (threadId: string) => void
  onRefreshThreads?: () => void
  currentThreadId?: string | null
  onClearCurrentThread?: () => void
  onFocusChange?: (focusData: UserFocus | null) => void
  threadCallbacks?: {
    onThreadTitleGenerating?: (data: any) => void
  }
}

// Focus interface
interface UserFocus {
  current_focus: string
  available_foci: string[]
  focus_confirmed: boolean
}

export function AppSidebar({ onThreadSelect, onRefreshThreads, currentThreadId, onClearCurrentThread, onFocusChange, threadCallbacks }: AppSidebarProps = {}) {
  const navigate = useNavigate()
  const { user, token, isAuthenticated, logout } = useAuth()
  const { state } = useSidebar()
  const [threads, setThreads] = useState<Thread[]>([])
  const [threadsLoading, setThreadsLoading] = useState(false)
  const [generatingTitles, setGeneratingTitles] = useState<Set<string>>(new Set())
  const [userFocus, setUserFocus] = useState<UserFocus | null>(null)

  const isCollapsed = state === "collapsed"

  // Fetch threads when user is authenticated
  useEffect(() => {
    if (isAuthenticated && user && token) {
      console.log('Authentication state changed, fetching threads...')
      fetchThreads()
    } else {
      setThreads([])
    }
  }, [isAuthenticated, user, token])

  // Focus navigation is now handled in handleSetUserFocus to go to dashboard

  // Also fetch threads and focus on component mount if already authenticated
  useEffect(() => {
    if (isAuthenticated && user && token) {
      if (threads.length === 0) {
        console.log('Component mounted with authentication, fetching threads...')
        fetchThreads()
      }
      if (!userFocus) {
        console.log('Component mounted with authentication, fetching focus...')
        fetchUserFocus()
      }
    }
  }, []) // Only run on mount

  // Fetch user focus when authentication state changes
  useEffect(() => {
    if (isAuthenticated && user && token) {
      console.log('Authentication state changed, fetching focus...')
      fetchUserFocus()
    } else {
      setUserFocus(null)
    }
  }, [isAuthenticated, user, token])

  // Set up thread title generating callback
  useEffect(() => {
    if (threadCallbacks?.onThreadTitleGenerating) {
      // Replace the callback to also update local state
      const originalCallback = threadCallbacks.onThreadTitleGenerating
      threadCallbacks.onThreadTitleGenerating = (data: any) => {
        console.log('🎯 [SIDEBAR] Thread title generating:', data.thread_id)
        // Add to generating set
        setGeneratingTitles(prev => new Set(prev).add(data.thread_id))
        // Call original callback if needed
        originalCallback(data)
      }
    }
  }, [threadCallbacks])

  const fetchThreads = async () => {
    console.log('fetchThreads called, token:', token ? token.substring(0, 20) + '...' : 'null')
    console.log('isAuthenticated:', isAuthenticated, 'user:', user?.username)
    console.log('Full token:', token)

    if (!token) {
      console.warn('No token available for threads fetch')
      return
    }

    try {
      setThreadsLoading(true)
      console.log('Making request to: /api/threads')

      console.log('About to make fetch request...')
      const response = await authorizedFetch('/api/threads')
      console.log('Fetch completed, response object:', response)
      console.log('Response headers:', [...response.headers.entries()])
      console.log('Response status:', response.status)
      console.log('Response ok:', response.ok)

      console.log('Response status:', response.status, response.statusText)

      if (response.ok) {
        // Get the raw text first
        const responseText = await response.text()
        console.log('Raw response text:', responseText)

        try {
          const threadsData = JSON.parse(responseText)
          console.log('Parsed JSON:', threadsData)
          console.log('Response type:', typeof threadsData)
          console.log('Response isArray:', Array.isArray(threadsData))
          console.log('Fetched threads count:', threadsData.length, 'threads')

          if (Array.isArray(threadsData)) {
            console.log('Array contents:', threadsData)
            console.log('First item (if exists):', threadsData[0])
            console.log('Array keys:', Object.keys(threadsData))
            console.log('Array length via Object.keys:', Object.keys(threadsData).length)

            setThreads(threadsData)
            // Clear generating titles when threads are refreshed
            setGeneratingTitles(new Set())
            console.log('Successfully set threads state with', threadsData.length, 'threads')

            // Double-check the state was set correctly
            setTimeout(() => {
              console.log('Checking threads state after setTimeout - current threads:', threadsData.length)
            }, 100)

            // Notify parent component that threads were refreshed
            if (onRefreshThreads) {
              onRefreshThreads()
            }
          } else {
            console.error('API response is not an array:', threadsData);
            setThreads([]);
          }
        } catch (error) {
          console.error('JSON parsing error:', error);
          setThreads([]);
        }
      } else {
        const errorText = await response.text();
        console.error('Failed to fetch threads:', response.status, response.statusText, errorText);
        setThreads([]);
      }
    } catch (error) {
      console.error('Error fetching threads:', error);
      setThreads([]);
    } finally {
      setThreadsLoading(false);
    }
  }

  const handleThreadClick = (threadId: string) => {
    console.log('Thread clicked:', threadId);
    if (onThreadSelect) {
      onThreadSelect(threadId);
    }
  };

  const handleThreadDelete = async (threadId: string, event: React.MouseEvent) => {
    event.stopPropagation() // Prevent thread selection
    console.log('Deleting thread:', threadId)

    try {
      const response = await authorizedFetch(`/api/threads/${threadId}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        console.log('Thread deleted successfully')
        // If the deleted thread is currently selected, clear it
        if (currentThreadId === threadId && onClearCurrentThread) {
          console.log('Clearing current thread view')
          onClearCurrentThread()
        }
        // Refresh threads list
        fetchThreads()
        // Notify parent component
        if (onRefreshThreads) {
          onRefreshThreads()
        }
      } else {
        console.error('Failed to delete thread:', response.status, response.statusText)
      }
    } catch (error) {
      console.error('Error deleting thread:', error)
    }
  }

  const fetchUserFocus = async () => {
    console.log('fetchUserFocus called, token:', token ? token.substring(0, 20) + '...' : 'null')
    console.log('isAuthenticated:', isAuthenticated, 'user:', user?.username)

    if (!token) {
      console.warn('No token available for focus fetch')
      return
    }

    try {
      console.log('Making request to: /api/accounts/focus')

      const response = await fetch('/api/accounts/focus', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      console.log('Focus fetch response status:', response.status)

      if (response.ok) {
        const focusData = await response.json()
        console.log('Fetched user focus:', focusData)
        setUserFocus(focusData)
        // Notify parent component of initial focus load
        onFocusChange?.(focusData)
      } else {
        const errorText = await response.text()
        console.error('Failed to fetch focus:', response.status, response.statusText, errorText)
        setUserFocus(null)
      }
    } catch (error) {
      console.error('Error fetching user focus:', error)
      setUserFocus(null)
    }
  }

  const handleSetUserFocus = async (focus: string) => {
    console.log('handleSetUserFocus called with focus:', focus)

    if (!token) {
      console.warn('No token available for focus setting')
      return
    }

    // Optimistic update: immediately update UI
    const previousFocus = userFocus
    setUserFocus(prev => prev ? { ...prev, current_focus: focus } : null)

    try {
      console.log('Making request to: /api/accounts/focus')

      const response = await fetch('/api/accounts/focus', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ focus }),
      })

      console.log('Focus set response status:', response.status)

      if (response.ok) {
        const result = await response.json()
        console.log('Focus set successfully:', result)
        setUserFocus(result) // Update with server response
        // Notify parent component of focus change
        onFocusChange?.(result)
        // Navigate to focus-specific route
        navigate(`/${focus}`)
      } else {
        const errorText = await response.text()
        console.error('Failed to set focus:', response.status, response.statusText, errorText)
        // Revert optimistic update on failure
        setUserFocus(previousFocus)
        // TODO: Show user-friendly error message (toast notification)
      }
    } catch (error) {
      console.error('Error setting user focus:', error)
      // Revert optimistic update on error
      setUserFocus(previousFocus)
      // TODO: Show user-friendly error message (toast notification)
    }
  }

  const getFocusIcon = (focus: string) => {
    const PatientIcon = ({ className = "size-4" }) => (
      <span className="relative inline-flex">
        <User className={className} />
        <HeartPulse className="absolute right-0 bottom-0 size-2 text-red-500" />
      </span>
    )
    switch (focus) {
      case 'candidate':
        return <User className="size-4" />
      case 'employer':
        return <Briefcase className="size-4" />
      case 'recruiter':
        return <Users className="size-4" />
      case 'administrator':
        return <Shield className="size-4" />
      case 'traveler':
        return <Plane className="size-4" />
      case 'agent':
        return <Headset className="size-4" />
      case 'patient':
        return <PatientIcon />
      case 'practitioner':
        return <Stethoscope className="size-4" />
      case 'client':
        return <Handshake className="size-4" />
      case 'engineer':
        return <Laptop2 className="size-4" />
      case 'principal':
        return <Crown className="size-4" />
      default:
        return <User className="size-4" />
    }
  }

  const getFocusLabel = (focus: string) => {
    // Use client-specific naming to match group selection
    const clientName = CURRENT_CLIENT.name.toLowerCase()

    // Map focus names to group names for consistent naming
    const focusToGroupMapping: Record<string, string> = {
      'candidate': 'candidate',
      'employer': 'employer',
      'recruiter': 'recruiter',
      'administrator': 'administrator'  // focus uses 'administrator', groups use 'administrator'
    }

    const groupName = focusToGroupMapping[focus] || focus

    // Check for client-specific naming
    if (clientName === 'talentco') {
      const talentCoNames: Record<string, string> = {
        'candidate': 'Job Seeker',
        'employer': 'Employer',
        'recruiter': 'Talent Partner',
        'administrator': 'System Admin'
      }
      return talentCoNames[groupName] || focus
    }

    // Default naming
    const defaultNames: Record<string, string> = {
      'candidate': 'Job Seeker',
      'employer': 'Employer',
      'recruiter': 'Recruiter',
      'administrator': 'Administrator'
    }

    return defaultNames[groupName] || focus
  }

  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <div className="flex items-center justify-center">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-muted text-sidebar-primary-foreground">
                  {(() => {
                    const IconComponent = getBrandIcon(CURRENT_CLIENT.brandIcon || 'Bot');
                    return <IconComponent className="size-4 text-foreground" />;
                  })()}
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      {/* Focus Selection */}
      {isAuthenticated && (
        <div className={`${isCollapsed ? 'px-2 py-3' : 'px-3 py-2'} border-b`}>
          {userFocus ? (
            <div className={`space-y-1 ${isCollapsed ? 'flex flex-col items-center space-y-2' : ''}`}>
              {userFocus.available_foci.map((focus) => {
                const isSelected = userFocus.current_focus === focus
                return (
                  <button
                    key={focus}
                    onClick={() => handleSetUserFocus(focus)}
                    className={`
                      flex items-center justify-start p-2 rounded-md transition-all duration-200
                      ${isCollapsed ? 'w-8 h-8' : 'w-full space-x-2 cursor-pointer hover:bg-muted/50 px-1 py-0.5'}
                      ${isSelected
                        ? 'bg-primary/10 text-primary border border-primary/20'
                        : 'text-muted-foreground hover:text-foreground opacity-50 hover:opacity-100'
                      }
                    `}
                    title={isCollapsed ? getFocusLabel(focus) : undefined}
                  >
                    {getFocusIcon(focus)}
                    {!isCollapsed && (
                      <span className="text-xs">{getFocusLabel(focus)}</span>
                    )}
                  </button>
                )
              })}
            </div>
          ) : (
            <div className={`text-xs text-muted-foreground ${isCollapsed ? 'text-center' : ''}`}>
              {isCollapsed ? '!' : 'Unable to load focus options'}
            </div>
          )}
        </div>
      )}

      {/* Universal Actions - Available for all authenticated users */}
      {isAuthenticated && (
        <SidebarGroup>
          
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton tooltip="View your stored memories" onClick={() => navigate('/memories')}>
                  <Brain className="size-4" />
                  {!isCollapsed && <span>Memories</span>}
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      )}

      {/* Focus-Specific Navigation */}
      {isAuthenticated && userFocus && (
        <SidebarGroup>
          
          <SidebarGroupContent>
            <SidebarMenu>
              {userFocus.current_focus === 'candidate' ? (
                // Job Seeker menu items
                <>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Update your profile" onClick={() => navigate('/profile')}>
                      <User className="size-4" />
                      {!isCollapsed && <span>My Profile</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Browse job opportunities" onClick={() => navigate('/candidate/opportunities')}>
                      <Search className="size-4" />
                      {!isCollapsed && <span>Browse Opportunities</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="View application status" onClick={() => navigate('/candidate/applications')}>
                      <FileText className="size-4" />
                      {!isCollapsed && <span>My Applications</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Evaluate jobs for your profile" onClick={() => navigate('/candidate/evaluations')}>
                      <Sparkles className="size-4" />
                      {!isCollapsed && <span>Evaluate Jobs</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </>
              ) : userFocus.current_focus === 'employer' ? (
                // Employer menu items
                <>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Update your profile" onClick={() => navigate('/profile')}>
                      <User className="size-4" />
                      {!isCollapsed && <span>My Profile</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Manage your organisations" onClick={() => navigate('/employer/organisations')}>
                      <Building2 className="size-4" />
                      {!isCollapsed && <span>My Organisations</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Manage your jobs" onClick={() => navigate('/employer/opportunities')}>
                      <Briefcase className="size-4" />
                      {!isCollapsed && <span>My Jobs</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Review candidates">
                      <Users className="size-4" />
                      {!isCollapsed && <span>Candidates</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Evaluate candidates for your jobs" onClick={() => navigate('/employer/evaluations')}>
                      <Sparkles className="size-4" />
                      {!isCollapsed && <span>Evaluate Candidates</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </>
              ) : userFocus.current_focus === 'recruiter' ? (
                // Recruiter menu items
                <>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Update your profile" onClick={() => navigate('/profile')}>
                      <User className="size-4" />
                      {!isCollapsed && <span>My Profile</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Find talent">
                      <Search className="size-4" />
                      {!isCollapsed && <span>Find Talent</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Manage placements">
                      <Users className="size-4" />
                      {!isCollapsed && <span>My Placements</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </>
              ) : userFocus.current_focus === 'administrator' ? (
                // Administrator menu items
                <>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Update your profile" onClick={() => navigate('/profile')}>
                      <User className="size-4" />
                      {!isCollapsed && <span>My Profile</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="System settings">
                      <Settings className="size-4" />
                      {!isCollapsed && <span>System Settings</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="User management">
                      <Users className="size-4" />
                      {!isCollapsed && <span>User Management</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </>
              ) : CLIENT_CONFIG === 'lumie' && userFocus?.current_focus === 'patient' ? (
                // Patient health menu items
                <>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Track your activity and exercise" onClick={() => navigate('/health/activity')}>
                      <Activity className="size-4" />
                      {!isCollapsed && <span>Activity</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Monitor your symptoms" onClick={() => navigate('/health/symptoms')}>
                      <Stethoscope className="size-4" />
                      {!isCollapsed && <span>Symptoms</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Track vital signs and measurements" onClick={() => navigate('/health/measurements')}>
                      <Thermometer className="size-4" />
                      {!isCollapsed && <span>Measurements</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Manage medications and treatments" onClick={() => navigate('/health/therapeutics')}>
                      <Pill className="size-4" />
                      {!isCollapsed && <span>Therapeutics</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Track your nutrition" onClick={() => navigate('/health/nutrition')}>
                      <Soup className="size-4" />
                      {!isCollapsed && <span>Nutrition</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Access health records and test results" onClick={() => navigate('/health/records')}>
                      <FileText className="size-4" />
                      {!isCollapsed && <span>Records</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Schedule and manage consultations" onClick={() => navigate('/health/consultations')}>
                      <CalendarCheck className="size-4" />
                      {!isCollapsed && <span>Consultations</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </>
              ) : CLIENT_CONFIG === 'lumie' && userFocus?.current_focus === 'practitioner' ? (
                // Practitioner health menu items
                <>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Manage your patients" onClick={() => navigate('/health/patients')}>
                      <Users className="size-4" />
                      {!isCollapsed && <span>Patients</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Manage your consultations" onClick={() => navigate('/health/consultations')}>
                      <CalendarCheck className="size-4" />
                      {!isCollapsed && <span>Consultations</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </>
              ) : null}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      )}

      {/* Divider between menu and threads */}
      <div className="border-t mx-2 my-2" />

      <SidebarContent className="custom-scrollbar">
        <SidebarGroup>
          
          <SidebarGroupContent>
            <SidebarMenu>
              {threadsLoading ? (
                <SidebarMenuItem>
                  <SidebarMenuButton disabled>
                    <MessageSquare className="size-4" />
                    <span>Loading threads...</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ) : threads.length === 0 ? (
                <SidebarMenuItem>
                  <SidebarMenuButton disabled>
                    <MessageSquare className="size-4" />
                    <span>No threads yet</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ) : (
                threads.slice(0, 10).map((thread) => (
                  <SidebarMenuItem key={thread.id}>
                    <div className="group relative">
                      <SidebarMenuButton
                        onClick={() => handleThreadClick(thread.id)}
                        tooltip={thread.subject}
                        className="cursor-pointer w-full pr-8"
                      >
                        <MessageSquare className="size-4 flex-shrink-0" />
                        <span className="break-words whitespace-normal leading-tight">
                          {generatingTitles.has(thread.id) ? (
                            <span className="inline-flex items-center gap-1">
                              <span className="animate-pulse bg-muted rounded h-4 flex-1 min-w-16"></span>
                              <span className="text-xs text-muted-foreground animate-pulse">naming...</span>
                            </span>
                          ) : (
                            (thread.subject || 'Untitled Thread')
                              .replace(/^Conversation - /, '')
                              .replace(/^Anonymous conversation - /, '')
                          )}
                        </span>
                      </SidebarMenuButton>
                      {!isCollapsed && (
                        <button
                          onClick={(e) => handleThreadDelete(thread.id, e)}
                          className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity p-1 z-10"
                          title="Delete thread"
                        >
                          <Trash2 className="size-3" />
                        </button>
                      )}
                    </div>
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

      </SidebarContent>

      {/* Group Selection - Bottom aligned */}
      {isAuthenticated && (
        <div className={`${isCollapsed ? 'px-2 py-3' : 'px-2 pb-2'}`}>
          <GroupCheckboxes
            onGroupsUpdated={fetchUserFocus}
            isCollapsed={isCollapsed}
          />
        </div>
      )}
      
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <LoginDialog>
              <SidebarMenuButton size="lg" className="hover:bg-transparent hover:text-sidebar-foreground data-[state=open]:hover:bg-sidebar-accent data-[state=open]:hover:text-sidebar-accent-foreground">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-accent text-sidebar-accent-foreground">
                  {isAuthenticated ? (
                    <User className="size-4" />
                  ) : (
                    <LogIn className="size-4" />
                  )}
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate text-xs text-muted-foreground">
                    {isAuthenticated ? user?.username?.split('@')[0] : CURRENT_CLIENT.loginLabel}
                  </span>
                  <span className="truncate text-[10px] text-muted-foreground">
                    {isAuthenticated ? user?.email : CURRENT_CLIENT.loginSubheader}
                  </span>
                </div>
              </SidebarMenuButton>
            </LoginDialog>
          </SidebarMenuItem>
          {isAuthenticated && (
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" onClick={logout} className="cursor-pointer">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <LogOut className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate text-xs text-muted-foreground">{CURRENT_CLIENT.logoutLabel}</span>
                  <span className="truncate text-[10px] text-muted-foreground">{CURRENT_CLIENT.logoutDescription}</span>
                </div>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )}
        </SidebarMenu>
      </SidebarFooter>
      
      <SidebarRail />
    </Sidebar>
  )
}
