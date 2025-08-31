import { Calendar, Home, Inbox, Search, Settings, MessageSquare, Brain, Bot, Mic, Wrench, Terminal, LogOut, LogIn, User } from "lucide-react"
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

export function AppSidebar() {
  const { user, token, isAuthenticated, logout } = useAuth()
  const [threads, setThreads] = useState<Thread[]>([])
  const [threadsLoading, setThreadsLoading] = useState(false)

  // Fetch threads when user is authenticated
  useEffect(() => {
    if (isAuthenticated && user && token) {
      fetchThreads()
    } else {
      setThreads([])
    }
  }, [isAuthenticated, user, token])

  const fetchThreads = async () => {
    console.log('fetchThreads called, token:', token ? token.substring(0, 20) + '...' : 'null')
    console.log('isAuthenticated:', isAuthenticated, 'user:', user?.username)

    if (!token) {
      console.warn('No token available for threads fetch')
      return
    }

    try {
      setThreadsLoading(true)
      console.log('Making request to: http://127.0.0.1:8000/api/threads')

      const response = await fetch('http://127.0.0.1:8000/api/threads', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      console.log('Response status:', response.status, response.statusText)

      if (response.ok) {
        const threadsData = await response.json()
        console.log('Fetched threads:', threadsData.length, 'threads')
        setThreads(threadsData)
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
                    <SidebarMenuButton asChild tooltip={thread.subject}>
                      <a href={`#thread-${thread.id}`}>
                        <MessageSquare className="size-4" />
                        <span className="truncate">{thread.subject || 'Untitled Thread'}</span>
                      </a>
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
