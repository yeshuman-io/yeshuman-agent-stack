import { useState } from "react"
import { Bot, Plane, Leaf, Heart } from "lucide-react"

import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { AnimatedLoginButton } from "@/components/animated-login-button"
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

interface LoginFormProps extends React.ComponentPropsWithoutRef<"div"> {
  onSuccess?: () => void;
}

export function LoginForm({ className, onSuccess, ...props }: LoginFormProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const { login, isLoading } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!email || !password) {
      setError("Please fill in all fields")
      return
    }

    const result = await login(email, password)

    if (result.success) {
      onSuccess?.()
    } else {
      setError(result.error || "Login failed")
    }
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <form onSubmit={handleSubmit}>
        <div className="flex flex-col gap-6">
          <div className="flex flex-col items-center gap-2">
            <div className="flex flex-col items-center gap-2 font-medium">
              <div className="flex h-8 w-8 items-center justify-center rounded-md">
                {(() => {
                  const IconComponent = getBrandIcon(CURRENT_CLIENT.brandIcon || 'Bot');
                  return <IconComponent className="size-6" />;
                })()}
              </div>
            </div>
            <h1 className="text-xl font-bold">{CURRENT_CLIENT.welcomeMessage}</h1>
          </div>
          <div className="flex flex-col gap-6">
            {error && (
              <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md dark:bg-red-900/20 dark:text-red-400 dark:border-red-800">
                {error}
              </div>
            )}
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder={CURRENT_CLIENT.placeholderEmail}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder={CURRENT_CLIENT.placeholderPassword}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>
            <AnimatedLoginButton
              disabled={isLoading}
              isLoading={isLoading}
            />
          </div>
         
        </div>
      </form>
    </div>
  )
}
