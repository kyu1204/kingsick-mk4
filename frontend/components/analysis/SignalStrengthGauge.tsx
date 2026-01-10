import * as React from "react"
import { cn } from "@/lib/utils"

export type SignalType = "BUY" | "SELL" | "HOLD" | "STRONG_BUY" | "STRONG_SELL"

interface SignalStrengthGaugeProps {
  strength: number
  signal: SignalType
  className?: string
}

const SignalStrengthGauge = React.forwardRef<HTMLDivElement, SignalStrengthGaugeProps>(
  ({ strength, signal, className }, ref) => {
    const getColor = (s: SignalType) => {
      if (s === "BUY" || s === "STRONG_BUY") return "text-green-500 stroke-green-500"
      if (s === "SELL" || s === "STRONG_SELL") return "text-red-500 stroke-red-500"
      return "text-yellow-500 stroke-yellow-500"
    }

    const colorClass = getColor(signal)
    
    const angle = Math.PI - (Math.min(Math.max(strength, 0), 100) / 100) * Math.PI
    const endX = 100 + 80 * Math.cos(angle)
    const endY = 100 - 80 * Math.sin(angle)
    
    return (
      <div 
        ref={ref} 
        className={cn("flex flex-col items-center justify-center relative", className)}
      >
        <div className="relative w-64 h-32 overflow-hidden">
          <svg 
            viewBox="0 0 200 110" 
            className="w-full h-full transform translate-y-2"
          >
            <path 
              d="M 20 100 A 80 80 0 0 1 180 100" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="15" 
              className="text-muted/20"
              strokeLinecap="round"
            />
            
            <path 
              d={`M 20 100 A 80 80 0 0 1 ${endX} ${endY}`} 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="15" 
              className={cn("transition-all duration-1000 ease-out", colorClass)}
              strokeLinecap="round"
            />
          </svg>
          
          <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 flex flex-col items-center mb-2">
            <span className={cn("text-4xl font-bold tracking-tighter", colorClass.split(" ")[0])}>
              {Math.round(strength)}
            </span>
            <span className="text-xs text-muted-foreground uppercase tracking-widest font-semibold mt-1">
              Score
            </span>
          </div>
        </div>
        
        <div className={cn("mt-4 px-4 py-1.5 rounded-full border bg-background text-sm font-bold tracking-wide shadow-sm", 
            signal.includes("BUY") ? "border-green-200 text-green-700 dark:border-green-900 dark:text-green-400" :
            signal.includes("SELL") ? "border-red-200 text-red-700 dark:border-red-900 dark:text-red-400" :
            "border-yellow-200 text-yellow-700 dark:border-yellow-900 dark:text-yellow-400"
        )}>
          {signal.replace("_", " ")}
        </div>
      </div>
    )
  }
)
SignalStrengthGauge.displayName = "SignalStrengthGauge"

export { SignalStrengthGauge }
