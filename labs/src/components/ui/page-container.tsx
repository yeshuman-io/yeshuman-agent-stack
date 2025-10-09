import React from 'react'
import { cn } from '@/lib/utils'

interface PageContainerProps {
  children: React.ReactNode
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '4xl' | '6xl' | '7xl' | 'full'
  padding?: string
  className?: string
}

export function PageContainer({
  children,
  maxWidth = '4xl',
  padding = 'p-6',
  className,
}: PageContainerProps) {
  const maxWidthClass = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    '4xl': 'max-w-4xl',
    '6xl': 'max-w-6xl',
    '7xl': 'max-w-7xl',
    full: 'max-w-full',
  }[maxWidth]

  return (
    <div className={cn(
      'h-full overflow-auto custom-scrollbar',
      padding,
      className
    )}>
      <div className={cn('mx-auto space-y-6', maxWidthClass)}>
        {children}
      </div>
    </div>
  )
}
