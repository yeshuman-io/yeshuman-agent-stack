import { LoginForm } from "@/components/login-form"
import { useAuth } from "@/hooks/use-auth"
import { useNavigate } from "react-router-dom"
import { useEffect } from "react"
import { AnimatedTitle } from "@/components/animated-title"

export function LoginPage() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    // If user becomes authenticated, redirect back to profile
    if (isAuthenticated) {
      navigate('/profile', { replace: true })
    }
  }, [isAuthenticated, navigate])

  const handleLoginSuccess = () => {
    // Navigation will happen via useEffect when auth state changes
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 bg-background">
      {/* Animated Branding Title */}
      <div className="mb-4 md:mb-8 text-center text-6xl md:text-8xl lg:text-9xl font-bold text-foreground">
        <AnimatedTitle />
      </div>

      {/* Login Form */}
      <div className="w-full max-w-md">
        <LoginForm onSuccess={handleLoginSuccess} />
      </div>
    </div>
  )
}
