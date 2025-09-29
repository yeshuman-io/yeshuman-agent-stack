import { MessageSquare, Bot, LogOut, LogIn, User, Trash2, Plane, Leaf, Heart, Briefcase, Shield, Search, FileText, Users } from "lucide-react"
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar"
import { LoginDialog } from "@/components/login-dialog"
import { useAuth } from "@/hooks/use-auth"
import { CURRENT_CLIENT } from "@/constants"

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
}

// Focus interface
interface UserFocus {
  current_focus: string
  available_foci: string[]
  focus_confirmed: boolean
}

export function AppSidebar({ onThreadSelect, onRefreshThreads }: AppSidebarProps = {}) {
  const navigate = useNavigate()
  const { user, token, isAuthenticated, logout } = useAuth()
  const { state } = useSidebar()
  const [threads, setThreads] = useState<Thread[]>([])
  const [threadsLoading, setThreadsLoading] = useState(false)
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

  // Navigate to profile when seeker focus is selected
  useEffect(() => {
    if (userFocus?.current_focus === 'candidate') {
      navigate('/profile')
    }
  }, [userFocus?.current_focus, navigate])

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
      const response = await fetch('/api/threads', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
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
      const response = await fetch(`/api/threads/${threadId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        console.log('Thread deleted successfully')
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
    switch (focus) {
      case 'candidate':
        return <User className="size-4" />
      case 'employer':
        return <Briefcase className="size-4" />
      case 'admin':
        return <Shield className="size-4" />
      default:
        return <User className="size-4" />
    }
  }

  const getFocusLabel = (focus: string) => {
    switch (focus) {
      case 'candidate':
        return 'Job Seeker'
      case 'employer':
        return 'Employer'
      case 'admin':
        return 'Admin'
      default:
        return focus
    }
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
                      flex items-center justify-center p-2 rounded-md transition-all duration-200
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

      {/* Focus-Specific Navigation */}
      {isAuthenticated && userFocus && (
        <SidebarGroup>
          <SidebarGroupLabel>Actions</SidebarGroupLabel>
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
                    <SidebarMenuButton tooltip="Browse job opportunities">
                      <Search className="size-4" />
                      {!isCollapsed && <span>Find Jobs</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="View application status">
                      <FileText className="size-4" />
                      {!isCollapsed && <span>My Applications</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </>
              ) : userFocus.current_focus === 'employer' ? (
                // Employer menu items
                <>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Post a new job">
                      <Briefcase className="size-4" />
                      {!isCollapsed && <span>Post Job</span>}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton tooltip="Manage your jobs">
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
                </>
              ) : null}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      )}

      <SidebarContent className="custom-scrollbar">
        <SidebarGroup>
          <SidebarGroupLabel>Threads</SidebarGroupLabel>
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
                    <SidebarMenuButton
                      onClick={() => handleThreadClick(thread.id)}
                      tooltip={thread.subject}
                      className="cursor-pointer group relative"
                    >
                      <MessageSquare className="size-4 flex-shrink-0" />
                      <span className="break-words whitespace-normal leading-tight pr-6">
                        {thread.subject || 'Untitled Thread'}
                      </span>
                      <button
                        onClick={(e) => handleThreadDelete(thread.id, e)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity p-1"
                        title="Delete thread"
                      >
                        <Trash2 className="size-3" />
                      </button>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      
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
