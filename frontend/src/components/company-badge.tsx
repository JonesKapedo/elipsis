import { cn } from "@/lib/utils"
import { Building2 } from "lucide-react"

interface CompanyBadgeProps {
  size: "small" | "medium" | "big"
  className?: string
  showIcon?: boolean
}

const badgeConfig = {
  small: {
    color: "bg-green-100 text-green-800 border-green-300",
    label: "Small",
    description: "<50 employees or <$5M revenue",
  },
  medium: {
    color: "bg-red-100 text-red-900 border-red-400",
    label: "Medium",
    description: "50-500 employees or $5M-$50M revenue",
  },
  big: {
    color: "bg-red-200 text-red-950 border-red-500",
    label: "Big",
    description: ">500 employees or >$50M revenue",
  },
}

export function CompanyBadge({
  size,
  className,
  showIcon = false,
}: CompanyBadgeProps) {
  const config = badgeConfig[size] || badgeConfig.small

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border",
        config.color,
        className
      )}
      title={config.description}
    >
      {showIcon && <Building2 className="h-3 w-3" />}
      {config.label}
    </span>
  )
}

export function CompanySize({
  size,
  employeeCount,
  revenue,
  className,
}: {
  size: "small" | "medium" | "big"
  employeeCount?: number
  revenue?: { min?: number; max?: number }
  className?: string
}) {
  const revenueAvg =
    revenue?.min && revenue?.max
      ? (revenue.min + revenue.max) / 2
      : revenue?.min || revenue?.max

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <CompanyBadge size={size} showIcon />
      <div className="text-xs text-muted-foreground">
        {employeeCount && <div>{employeeCount.toLocaleString()} employees</div>}
        {revenueAvg && (
          <div>
            ~${(revenueAvg / 1_000_000).toFixed(1)}M revenue
          </div>
        )}
      </div>
    </div>
  )
}
