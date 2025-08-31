import { useState } from "react"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { LoginForm } from "@/components/login-form"
import { useAuth } from "@/hooks/use-auth"

interface LoginDialogProps {
  children: React.ReactNode;
}

export function LoginDialog({ children }: LoginDialogProps) {
  const [open, setOpen] = useState(false)
  const { isAuthenticated } = useAuth()

  const handleLoginSuccess = () => {
    setOpen(false)
  }

  // If user is already authenticated, just return the children
  if (isAuthenticated) {
    return <>{children}</>
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        {children}
      </SheetTrigger>
      <SheetContent side="right" className="w-[400px] sm:w-[400px]">
        <SheetHeader>
          <SheetTitle>Log In</SheetTitle>
          <SheetDescription>
            Enter your precious credentials to interact with me, human.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 p-6">
          <LoginForm onSuccess={handleLoginSuccess} />
        </div>
      </SheetContent>
    </Sheet>
  )
}
