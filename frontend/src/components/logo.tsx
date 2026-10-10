import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "icon" | "full"
  size?: "sm" | "md" | "lg" | "xl"
  className?: string
}

const sizeClasses = {
  sm: "h-6",
  md: "h-10",
  lg: "h-14",
  xl: "h-20",
}

export function Logo({ variant = "full", size = "md", className }: LogoProps) {
  const heightClass = sizeClasses[size]

  if (variant === "icon") {
    return (
      <svg
        className={cn(heightClass, "w-auto", className)}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="iconGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3B82F6" />
            <stop offset="50%" stopColor="#06B6D4" />
            <stop offset="100%" stopColor="#8B5CF6" />
          </linearGradient>
        </defs>
        {/* Three dots forming triangle */}
        <circle cx="50" cy="25" r="12" fill="url(#iconGradient)" />
        <circle cx="30" cy="65" r="12" fill="url(#iconGradient)" />
        <circle cx="70" cy="65" r="12" fill="url(#iconGradient)" />
        {/* Circuit connections */}
        <path
          d="M 50 37 L 50 50 M 50 50 L 35 60 M 50 50 L 65 60"
          stroke="url(#iconGradient)"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
    )
  }

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <svg
        className={cn(heightClass, "w-auto")}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="fullGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3B82F6" />
            <stop offset="50%" stopColor="#06B6D4" />
            <stop offset="100%" stopColor="#8B5CF6" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="25" r="12" fill="url(#fullGradient)" />
        <circle cx="30" cy="65" r="12" fill="url(#fullGradient)" />
        <circle cx="70" cy="65" r="12" fill="url(#fullGradient)" />
        <path
          d="M 50 37 L 50 50 M 50 50 L 35 60 M 50 50 L 65 60"
          stroke="url(#fullGradient)"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
      <span
        className={cn(
          "font-bold bg-gradient-to-r from-blue-500 via-cyan-500 to-purple-500 bg-clip-text text-transparent",
          size === "sm" && "text-lg",
          size === "md" && "text-2xl",
          size === "lg" && "text-4xl",
          size === "xl" && "text-5xl"
        )}
      >
        Elipsis
      </span>
    </div>
  )
}
