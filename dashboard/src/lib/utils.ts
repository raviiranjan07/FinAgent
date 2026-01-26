import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return "-"

  // Backend sends naive IST timestamps (no timezone info)
  // Parse directly and format - the value IS the IST time
  const dateStr = typeof date === 'string' ? date : date.toISOString()
  const d = new Date(dateStr)

  // Format the date parts directly (don't use timezone conversion)
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
  const day = d.getUTCDate()
  const month = months[d.getUTCMonth()]
  const year = d.getUTCFullYear()
  const hours = d.getUTCHours()
  const minutes = d.getUTCMinutes()

  // Format hours in 12-hour format
  const hour12 = hours % 12 || 12
  const ampm = hours < 12 ? "am" : "pm"
  const minuteStr = minutes.toString().padStart(2, "0")

  return `${day} ${month} ${year}, ${hour12}:${minuteStr} ${ampm} IST`
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str
  return str.slice(0, length) + "..."
}
