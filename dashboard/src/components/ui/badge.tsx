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
          "border-transparent bg-blue-600 text-white": variant === "default",
          "border-transparent bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white": variant === "secondary",
          "border-transparent bg-red-100 dark:bg-red-600 text-red-700 dark:text-white": variant === "destructive",
          "border-gray-300 dark:border-gray-600 text-gray-700 dark:text-white": variant === "outline",
          "border-transparent bg-green-100 dark:bg-green-600 text-green-700 dark:text-white": variant === "success",
          "border-transparent bg-yellow-100 dark:bg-yellow-600 text-yellow-800 dark:text-white": variant === "warning",
        },
        className
      )}
      {...props}
    />
  )
}

export { Badge }
