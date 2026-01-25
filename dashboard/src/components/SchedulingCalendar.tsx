import { useState, useEffect } from "react"
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isSameDay, addMonths, subMonths, parseISO } from "date-fns"
import { ChevronLeft, ChevronRight, Calendar, Clock, Zap } from "lucide-react"
import { Card } from "./ui/card"
import { Badge } from "./ui/badge"

interface ScheduledItem {
  content_queue_id: string
  event_title: string
  content_text: string
  scheduled_for: string
  status: string
  event_type: string
  randomization_applied: {
    base_time: string
    jitter_minutes: number
    gap_from_previous_hours: number
  }
}

interface SchedulingCalendarProps {
  onSelectDate?: (date: Date) => void
  onSelectItem?: (item: ScheduledItem) => void
}

export function SchedulingCalendar({ onSelectDate, onSelectItem }: SchedulingCalendarProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [scheduledItems, setScheduledItems] = useState<ScheduledItem[]>([])
  const [selectedDate, setSelectedDate] = useState<Date | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchScheduledItems()
  }, [currentMonth])

  const fetchScheduledItems = async () => {
    setLoading(true)
    try {
      const start = format(startOfMonth(currentMonth), "yyyy-MM-dd")
      const end = format(endOfMonth(currentMonth), "yyyy-MM-dd")

      const response = await fetch(`/api/scheduling/calendar?start_date=${start}&end_date=${end}`)
      if (!response.ok) throw new Error("Failed to fetch calendar")

      const data = await response.json()
      setScheduledItems(data.items || [])
    } catch (error) {
      console.error("Error fetching calendar:", error)
    } finally {
      setLoading(false)
    }
  }

  const getItemsForDate = (date: Date) => {
    return scheduledItems.filter((item) => {
      const itemDate = parseISO(item.scheduled_for)
      return isSameDay(itemDate, date)
    })
  }

  const handlePreviousMonth = () => {
    setCurrentMonth(subMonths(currentMonth, 1))
  }

  const handleNextMonth = () => {
    setCurrentMonth(addMonths(currentMonth, 1))
  }

  const handleDateClick = (date: Date) => {
    setSelectedDate(date)
    onSelectDate?.(date)
  }

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const days = eachDayOfInterval({ start: monthStart, end: monthEnd })

  const getDayColor = (date: Date) => {
    const items = getItemsForDate(date)
    if (items.length === 0) return "bg-white dark:bg-gray-800"
    if (items.length >= 5) return "bg-green-50 dark:bg-green-900/20"
    if (items.length >= 3) return "bg-blue-50 dark:bg-blue-900/20"
    return "bg-gray-50 dark:bg-gray-700"
  }

  const getEventTypeIcon = (eventType: string) => {
    switch (eventType) {
      case "FINANCE_POLICY":
        return "🏛️"
      case "MARKET_MOVEMENT":
        return "📈"
      case "MACRO_ECONOMIC":
        return "🌍"
      case "GEO_FINANCIAL":
        return "🌐"
      default:
        return "📄"
    }
  }

  return (
    <div className="space-y-4">
      {/* Calendar Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {format(currentMonth, "MMMM yyyy")}
          </h2>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handlePreviousMonth}
            className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <button
            onClick={handleNextMonth}
            className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Anti-Bot Features Badge */}
      <Card className="p-4 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700">
        <div className="flex items-start gap-3">
          <Zap className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
          <div className="space-y-1">
            <p className="font-medium text-blue-900 dark:text-blue-100">
              Smart Anti-Bot Scheduling Active
            </p>
            <p className="text-sm text-blue-700 dark:text-blue-300">
              Times randomized ±15-30 min • Gaps 1.5-3.5 hrs • Daily variation 3-6 posts • Weekend reduction • 15% skip days
            </p>
          </div>
        </div>
      </Card>

      {loading ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">Loading calendar...</div>
      ) : (
        <>
          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-2">
            {/* Day Headers */}
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
              <div
                key={day}
                className="text-center text-sm font-medium text-gray-600 dark:text-gray-400 py-2"
              >
                {day}
              </div>
            ))}

            {/* Calendar Days */}
            {days.map((day, idx) => {
              const items = getItemsForDate(day)
              const isSelected = selectedDate && isSameDay(day, selectedDate)
              const isWeekend = day.getDay() === 0 || day.getDay() === 6

              return (
                <button
                  key={idx}
                  onClick={() => handleDateClick(day)}
                  className={`
                    relative min-h-[100px] p-2 rounded-lg border transition-all
                    ${getDayColor(day)}
                    ${isSelected ? "border-blue-500 ring-2 ring-blue-200 dark:ring-blue-700" : "border-gray-200 dark:border-gray-700"}
                    ${isWeekend ? "opacity-75" : ""}
                    hover:border-blue-300 dark:hover:border-blue-600
                  `}
                >
                  <div className="flex flex-col items-start h-full">
                    {/* Date Number */}
                    <span
                      className={`
                        text-sm font-medium mb-1
                        ${!isSameMonth(day, currentMonth) ? "text-gray-400 dark:text-gray-600" : "text-gray-900 dark:text-white"}
                      `}
                    >
                      {format(day, "d")}
                    </span>

                    {/* Items Count Badge */}
                    {items.length > 0 && (
                      <Badge variant="default" className="text-xs mb-1">
                        {items.length} post{items.length !== 1 ? "s" : ""}
                      </Badge>
                    )}

                    {/* First 2 Items Preview */}
                    <div className="space-y-1 w-full">
                      {items.slice(0, 2).map((item) => (
                        <div
                          key={item.content_queue_id}
                          className="text-xs p-1 bg-white dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600"
                        >
                          <div className="flex items-center gap-1 mb-0.5">
                            <Clock className="h-3 w-3" />
                            <span className="font-medium">
                              {format(parseISO(item.scheduled_for), "HH:mm")}
                            </span>
                          </div>
                          <div className="truncate text-gray-600 dark:text-gray-400">
                            {getEventTypeIcon(item.event_type)} {item.event_title}
                          </div>
                        </div>
                      ))}

                      {/* Show +N more if there are more items */}
                      {items.length > 2 && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
                          +{items.length - 2} more
                        </div>
                      )}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>

          {/* Selected Date Details */}
          {selectedDate && (
            <Card className="p-4">
              <h3 className="font-semibold text-lg mb-4 text-gray-900 dark:text-white">
                {format(selectedDate, "EEEE, MMMM d, yyyy")}
              </h3>

              {getItemsForDate(selectedDate).length === 0 ? (
                <p className="text-gray-500 dark:text-gray-400">No posts scheduled for this day</p>
              ) : (
                <div className="space-y-3">
                  {getItemsForDate(selectedDate)
                    .sort((a, b) => parseISO(a.scheduled_for).getTime() - parseISO(b.scheduled_for).getTime())
                    .map((item) => (
                      <button
                        key={item.content_queue_id}
                        onClick={() => onSelectItem?.(item)}
                        className="w-full text-left p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                            <span className="font-semibold text-gray-900 dark:text-white">
                              {format(parseISO(item.scheduled_for), "HH:mm")}
                            </span>
                            {item.randomization_applied && (
                              <Badge variant="outline" className="text-xs">
                                Jitter: {item.randomization_applied.jitter_minutes > 0 ? '+' : ''}
                                {item.randomization_applied.jitter_minutes}min
                              </Badge>
                            )}
                          </div>
                          <Badge variant="default">{item.status}</Badge>
                        </div>

                        <div className="mb-2">
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            {getEventTypeIcon(item.event_type)} {item.event_title}
                          </span>
                        </div>

                        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                          {item.content_text}
                        </p>

                        {item.randomization_applied && (
                          <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                            Base: {format(parseISO(item.randomization_applied.base_time), "HH:mm")} •
                            Gap from previous: {item.randomization_applied.gap_from_previous_hours.toFixed(1)}h
                          </div>
                        )}
                      </button>
                    ))}
                </div>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  )
}
