import { MessageSquare, Bot, LogOut, LogIn, User, Trash2, Plane, Leaf, Heart } from "lucide-react"
import { useState, useEffect } from "react"

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

export function AppSidebar({ onThreadSelect, onRefreshThreads }: AppSidebarProps = {}) {
  const { user, token, isAuthenticated, logout } = useAuth()
  const [threads, setThreads] = useState<Thread[]>([])
  const [threadsLoading, setThreadsLoading] = useState(false)

  // Fetch threads when user is authenticated
  useEffect(() => {
    if (isAuthenticated && user && token) {
      console.log('Authentication state changed, fetching threads...')
      fetchThreads()
    } else {
      setThreads([])
    }
  }, [isAuthenticated, user, token])

  // Also fetch threads on component mount if already authenticated
  useEffect(() => {
    if (isAuthenticated && user && token && threads.length === 0) {
      console.log('Component mounted with authentication, fetching threads...')
      fetchThreads()
    }
  }, []) // Only run on mount

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
      console.log('Making request to: http://127.0.0.1:8000/api/threads')

      console.log('About to make fetch request...')
      const response = await fetch('http://127.0.0.1:8000/api/threads', {
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
      const response = await fetch(`http://127.0.0.1:8000/api/threads/${threadId}`, {
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

  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <a href="#">
                <div className="flex items-center gap-3 w-full">
                  <div className="flex-shrink-0">
                    {CURRENT_CLIENT.logoPath ? (
                      <img
                        src={CURRENT_CLIENT.logoPath}
                        alt={`${CURRENT_CLIENT.brand} logo`}
                        className="h-8 w-8 object-contain rounded-md"
                        onError={(e) => {
                          // Fallback to brand icon if logo fails to load
                          const target = e.target as HTMLImageElement;
                          target.style.display = 'none';
                          const IconComponent = getBrandIcon(CURRENT_CLIENT.brandIcon || 'Bot');
                          const fallbackIcon = document.createElement('div');
                          fallbackIcon.innerHTML = `<svg class="h-8 w-8 text-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>`;
                          target.parentNode?.appendChild(fallbackIcon.firstChild as Node);
                        }}
                      />
                    ) : (
                      <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-muted text-sidebar-primary-foreground">
                        {(() => {
                          const IconComponent = getBrandIcon(CURRENT_CLIENT.brandIcon || 'Bot');
                          return <IconComponent className="size-4 text-foreground" />;
                        })()}
                      </div>
                    )}
                  </div>
                  <div className="grid flex-1 text-left text-sm leading-tight min-w-0">
                    <span className="truncate font-semibold text-base">{CURRENT_CLIENT.brand}</span>
                    <span className="truncate text-xs text-muted-foreground">{CURRENT_CLIENT.tagline}</span>
                  </div>
                </div>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
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
                    {isAuthenticated ? user?.username?.split('@')[0] : "Human?"}
                  </span>
                  <span className="truncate text-[10px] text-muted-foreground">
                    {isAuthenticated ? user?.email : "click to login"}
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
                  <span className="truncate text-xs text-muted-foreground">Human</span>
                  <span className="truncate text-[10px] text-muted-foreground">Return to anonymity</span>
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
