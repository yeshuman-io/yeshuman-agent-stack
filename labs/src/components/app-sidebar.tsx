import { Calendar, Home, Inbox, Search, Settings, MessageSquare, Brain, Bot, Mic, Wrench, Terminal, LogOut, LogIn, User, Trash2 } from "lucide-react"
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
            console.error('API response is not an array:', threadsData)
            setThreads([])
          }
        } catch (error) {
          console.error('JSON parsing error:', error)
          setThreads([])
        }
      } else {
        const errorText = await response.text()
        console.error('Failed to fetch threads:', response.status, response.statusText, errorText)
        setThreads([])
      }
    } catch (error) {
      console.error('Error fetching threads:', error)
      setThreads([])
    } finally {
      setThreadsLoading(false)
    }
  }

  const handleThreadClick = (threadId: string) => {
    console.log('Thread clicked:', threadId)
    if (onThreadSelect) {
      onThreadSelect(threadId)
    }
  }

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
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-muted text-sidebar-primary-foreground">
                  <Bot className="size-4 text-foreground" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">Yes Human</span>
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
