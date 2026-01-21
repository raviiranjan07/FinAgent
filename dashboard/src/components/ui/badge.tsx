import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning"
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
        {
          "border-transparent bg-gray-900 text-white": variant === "default",
          "border-transparent bg-gray-100 text-gray-900": variant === "secondary",
          "border-transparent bg-red-100 text-red-700": variant === "destructive",
          "border-gray-300 text-gray-700": variant === "outline",
          "border-transparent bg-green-100 text-green-700": variant === "success",
          "border-transparent bg-yellow-100 text-yellow-700": variant === "warning",
        },
        className
      )}
      {...props}
    />
  )
}

export { Badge }
