import * as React from "react"
import { cn } from "@/lib/utils"

export interface Contribution {
  name: string
  score: number
  weight: number
}

interface IndicatorContributionProps {
  contributions: Contribution[]
  className?: string
}

const IndicatorContribution = React.forwardRef<HTMLDivElement, IndicatorContributionProps>(
  ({ contributions, className }, ref) => {
    return (
      <div ref={ref} className={cn("space-y-4", className)}>
        {contributions.map((item) => {
          const isHigh = item.score >= 70
          const isLow = item.score <= 30
          
          const barColor = isHigh 
            ? "bg-green-500" 
            : isLow 
              ? "bg-red-500" 
              : "bg-yellow-500"
              
          const textColor = isHigh 
            ? "text-green-600 dark:text-green-400" 
            : isLow 
              ? "text-red-600 dark:text-red-400" 
              : "text-yellow-600 dark:text-yellow-400"

          return (
            <div key={item.name} className="space-y-1.5">
              <div className="flex justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{item.name}</span>
                  <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                    {item.weight}% weight
                  </span>
                </div>
                <span className={cn("font-bold font-mono", textColor)}>
                  {Math.round(item.score)}
                </span>
              </div>
              
              <div className="h-2.5 w-full bg-muted/50 rounded-full overflow-hidden">
                <div 
                  className={cn("h-full rounded-full transition-all duration-1000 ease-out", barColor)}
                  style={{ width: `${Math.max(5, Math.min(100, item.score))}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    )
  }
)
IndicatorContribution.displayName = "IndicatorContribution"

export { IndicatorContribution }
