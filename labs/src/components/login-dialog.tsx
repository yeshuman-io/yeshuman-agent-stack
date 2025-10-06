import { useNavigate } from "react-router-dom"
import { useAuth } from "@/hooks/use-auth"

interface LoginDialogProps {
  children: React.ReactNode;
}

export function LoginDialog({ children }: LoginDialogProps) {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  // If user is already authenticated, just return the children
  if (isAuthenticated) {
    return <>{children}</>
  }

  // For non-authenticated users, wrap children with click handler to navigate to login
  return (
    <div onClick={() => navigate('/login')} className="cursor-pointer">
      {children}
    </div>
  )
}
