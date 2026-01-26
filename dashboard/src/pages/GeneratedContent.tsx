import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { twitterApi, schedulingApi } from "@/api/client"
import type { TwitterContentItem } from "@/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { formatDate } from "@/lib/utils"
import {
  CheckCircle,
  XCircle,
  Edit,
  Trash2,
  ExternalLink,
  Clock,
  Zap,
  MessageSquare,
  Send,
  Loader2,
  ArrowLeft,
  RefreshCw,
} from "lucide-react"
import { EditContentModal } from "@/components/EditContentModal"

// X Logo Component
const XLogo = ({ className = "h-4 w-4" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" className={className} fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
)

// Helper to parse single tweet content from wrapped format
function parseSingleContent(content: string): string {
  try {
    const parsed = JSON.parse(content)
    // Handle wrapped format: {"format": "SINGLE", "content": {"tweet": "..."}}
    if (parsed?.content?.tweet) {
      return parsed.content.tweet
    }
  } catch {
    // Not valid JSON, return as-is
  }
  return content
}

// Helper to parse thread content from wrapped format
function parseThreadContent(content: string): string[] {
  try {
    const parsed = JSON.parse(content)
    // Handle wrapped format: {"format": "THREAD", "content": {"tweets": [...]}}
    if (parsed?.content?.tweets && Array.isArray(parsed.content.tweets)) {
      return parsed.content.tweets
    }
    // Handle simple array format (legacy)
    if (Array.isArray(parsed)) {
      return parsed
    }
  } catch {
    // Not valid JSON
  }
  return [content]
}

// Thread display component
function ThreadDisplay({ tweets }: { tweets: string[] }) {
  return (
    <div className="space-y-3">
      {tweets.map((tweet, idx) => (
        <div
          key={idx}
          className="border-l-2 border-blue-500 pl-3 space-y-1"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Post {idx + 1}/{tweets.length}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {tweet.length} chars
            </span>
          </div>
          <p className="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">
            {tweet}
          </p>
        </div>
      ))}
    </div>
  )
}

// Schedule Display Component with Countdown
function ScheduleDisplay({ scheduledFor }: { scheduledFor: string }) {
  const [timeLeft, setTimeLeft] = useState("")
  const [urgencyColor, setUrgencyColor] = useState("")

  useEffect(() => {
    const updateCountdown = () => {
      const now = new Date()
      const scheduledDate = new Date(scheduledFor)
      const diff = scheduledDate.getTime() - now.getTime()

      if (diff <= 0) {
        setTimeLeft("Overdue - should have published")
        setUrgencyColor("text-blue-600 dark:text-blue-400")
      } else {
        const hours = Math.floor(diff / (1000 * 60 * 60))
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
        const seconds = Math.floor((diff % (1000 * 60)) / 1000)

        setTimeLeft(`Publishing in ${hours}h ${minutes}m ${seconds}s`)

        // Color coding
        if (hours < 1) {
          setUrgencyColor("text-red-600 dark:text-red-400")
        } else if (hours < 6) {
          setUrgencyColor("text-yellow-600 dark:text-yellow-400")
        } else {
          setUrgencyColor("text-green-600 dark:text-green-400")
        }
      }
    }

    updateCountdown()
    const interval = setInterval(updateCountdown, 1000)

    return () => clearInterval(interval)
  }, [scheduledFor])

  const scheduledDate = new Date(scheduledFor)
  const formattedDate = scheduledDate.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    dateStyle: "medium",
    timeStyle: "short",
  })

  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        <span className="text-sm text-gray-700 dark:text-gray-300">
          Scheduled for {formattedDate} IST
        </span>
      </div>
      <div className={`text-sm font-semibold ${urgencyColor}`}>{timeLeft}</div>
    </div>
  )
}

// Worker Health Badge
function WorkerHealthBadge() {
  const { data: health } = useQuery({
    queryKey: ["worker-health"],
    queryFn: () => schedulingApi.getHealth(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  if (!health) return null

  return (
    <Badge
      variant={health.is_alive ? "success" : "destructive"}
      className="flex items-center gap-2"
    >
      <div
        className={`h-2 w-2 rounded-full ${
          health.is_alive ? "bg-green-500 animate-pulse" : "bg-red-500"
        }`}
      />
      Worker {health.is_alive ? "Active" : "Offline"}
      {health.success_rate !== null && health.success_rate !== undefined && (
        <span className="ml-1">({health.success_rate.toFixed(0)}%)</span>
      )}
    </Badge>
  )
}

export function GeneratedContent() {
  const [selectedContent, setSelectedContent] = useState<TwitterContentItem | null>(null)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false)
  const [scheduledDateTime, setScheduledDateTime] = useState("")
  const [rejectModalOpen, setRejectModalOpen] = useState(false)
  const [rejectionReason, setRejectionReason] = useState("")

  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ["twitter-content"],
    queryFn: () => twitterApi.list({ limit: 50, offset: 0 }),
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  const { data: settings } = useQuery({
    queryKey: ["twitter-settings"],
    queryFn: () => twitterApi.getSettings(),
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  const { data: systemStatus } = useQuery({
    queryKey: ["system-status"],
    queryFn: async () => {
      const res = await fetch("http://localhost:8001/api/system/status")
      if (!res.ok) throw new Error("Failed to fetch system status")
      return res.json()
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const deleteContent = useMutation({
    mutationFn: (contentQueueId: string) => twitterApi.delete(contentQueueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-content"] })
    },
  })

  const scheduleContentSmart = useMutation({
    mutationFn: (contentQueueIds: string[]) =>
      schedulingApi.scheduleSmart(contentQueueIds, 7),
    onSuccess: (data: any, variables: string[]) => {
      queryClient.invalidateQueries({ queryKey: ["twitter-content"] })
      const count = data.scheduled_count || variables.length
      // Simple confirmation - scheduled time will be visible on the card
      alert(`✅ Successfully scheduled ${count} item(s)\n\n⏱️ Random timing applied with natural gaps`)
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || "Failed to schedule content"
      alert(`❌ Smart scheduling failed: ${errorMessage}`)
    },
  })

  const scheduleContent = useMutation({
    mutationFn: ({ contentQueueId, scheduledFor }: { contentQueueId: string; scheduledFor: string }) =>
      schedulingApi.schedule(contentQueueId, scheduledFor),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-content"] })
      setScheduleModalOpen(false)
      setScheduledDateTime("")
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || "Failed to schedule content"
      alert(`❌ Scheduling failed: ${errorMessage}`)
    },
  })

  const rescheduleContent = useMutation({
    mutationFn: ({ contentQueueId, scheduledFor }: { contentQueueId: string; scheduledFor: string }) =>
      schedulingApi.reschedule(contentQueueId, scheduledFor),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-content"] })
      setScheduleModalOpen(false)
      setScheduledDateTime("")
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || "Failed to reschedule content"
      alert(`❌ Rescheduling failed: ${errorMessage}`)
    },
  })

  const unscheduleContent = useMutation({
    mutationFn: (contentQueueId: string) => schedulingApi.unschedule(contentQueueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-content"] })
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || "Failed to unschedule content"
      alert(`❌ Unscheduling failed: ${errorMessage}`)
    },
  })

  const publishNow = useMutation({
    mutationFn: (contentQueueId: string) => schedulingApi.publishNow(contentQueueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-content"] })
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || "Failed to publish content"
      alert(`❌ Publishing failed: ${errorMessage}`)
    },
  })

  const resetForRepublish = useMutation({
    mutationFn: (contentQueueId: string) => schedulingApi.resetForRepublish(contentQueueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-content"] })
      alert("✅ Content reset! You can now republish it.")
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || "Failed to reset for republish"
      alert(`❌ Reset failed: ${errorMessage}`)
    },
  })

  const approveHITL = useMutation({
    mutationFn: (contentQueueId: string) => twitterApi.approveHITL(contentQueueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-content"] })
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || "Failed to approve content"
      alert(`❌ Approval failed: ${errorMessage}`)
    },
  })

  const rejectHITL = useMutation({
    mutationFn: ({ contentQueueId, reason }: { contentQueueId: string; reason: string }) =>
      twitterApi.rejectHITL(contentQueueId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-content"] })
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || "Failed to reject content"
      alert(`❌ Rejection failed: ${errorMessage}`)
    },
  })

  const regenerateContent = useMutation({
    mutationFn: (contentQueueId: string) => twitterApi.regenerate(contentQueueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-content"] })
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || "Failed to regenerate content"
      alert(`❌ Regeneration failed: ${errorMessage}`)
    },
  })

  const handleRegenerate = (item: TwitterContentItem) => {
    const confirmRegenerate = confirm(
      `🔄 Regenerate this content?\n\n"${item.event_title}"\n\nThis will call the LLM again to generate a new version of the tweet/thread.\n\nThe current content will be replaced.\n\nContinue?`
    )

    if (confirmRegenerate) {
      regenerateContent.mutate(item.id)
    }
  }

  const handleEdit = (item: TwitterContentItem) => {
    setSelectedContent(item)
    setEditModalOpen(true)
  }

  const handleApproveHITL = (item: TwitterContentItem) => {
    const confirmApprove = confirm(
      `✅ Approve this content?\n\n"${item.event_title}"\n\n➡️ Next Step: This will move to "Ready to Schedule" where you can:\n  • Schedule it for a specific time\n  • Publish immediately\n  • Edit the content if needed\n\nApprove and continue?`
    )

    if (confirmApprove) {
      approveHITL.mutate(item.id)
    }
  }

  const handleRejectHITL = (item: TwitterContentItem) => {
    setSelectedContent(item)
    setRejectModalOpen(true)
    setRejectionReason("")  // Clear previous reason
  }

  const confirmRejectHITL = () => {
    if (!selectedContent) return

    // Require rejection reason
    if (!rejectionReason.trim()) {
      alert("Please provide a reason for rejection")
      return
    }

    rejectHITL.mutate({
      contentQueueId: selectedContent.id,
      reason: rejectionReason.trim()
    })

    setRejectModalOpen(false)
    setRejectionReason("")
  }

  const handleSaveEdit = async (editedContent: string) => {
    if (!selectedContent) return

    try {
      await twitterApi.edit(selectedContent.id, editedContent)
      // Wait for the query to refetch before closing modal
      await queryClient.invalidateQueries({ queryKey: ["twitter-content"] })
      setEditModalOpen(false)
      setSelectedContent(null)
    } catch (error: any) {
      alert(error.response?.data?.message || "Failed to save changes")
    }
  }

  const handleDelete = (item: TwitterContentItem) => {
    const confirmDelete = confirm(
      `Delete this X content?\n\n"${item.event_title}"\n\nThis action cannot be undone.`
    )

    if (confirmDelete) {
      deleteContent.mutate(item.id)
    }
  }

  const handleScheduleSmart = (item: TwitterContentItem) => {
    const confirmSchedule = confirm(
      `🤖 Schedule with Smart Timing?\n\n"${item.event_title}"\n\n✨ This will automatically:\n  • Pick an optimal posting time\n  • Apply random timing (±15-30 min)\n  • Add natural gaps between posts (1.5-3.5 hours)\n  • Avoid bot-like patterns\n\nSchedule now?`
    )

    if (confirmSchedule) {
      scheduleContentSmart.mutate([item.id])
    }
  }

  const handleSchedule = () => {
    if (!selectedContent || !scheduledDateTime) return

    // datetime-local gives us "YYYY-MM-DDTHH:mm" in local time
    // Append IST timezone offset for API (backend expects IST)
    const isoString = scheduledDateTime + ":00+05:30"

    // Use reschedule if already scheduled, otherwise schedule
    if (selectedContent.status === "scheduled") {
      rescheduleContent.mutate({
        contentQueueId: selectedContent.id,
        scheduledFor: isoString,
      })
    } else {
      scheduleContent.mutate({
        contentQueueId: selectedContent.id,
        scheduledFor: isoString,
      })
    }
  }

  const handleReschedule = (item: TwitterContentItem) => {
    setSelectedContent(item)
    setScheduleModalOpen(true)
    // Pre-fill with existing scheduled time (already in IST from backend)
    if (item.status === "scheduled" && item.scheduled_for) {
      // Backend sends IST time like "2026-01-26T15:00:00+05:30"
      // Extract just the date and time part for datetime-local input
      const istTime = item.scheduled_for.slice(0, 16)  // "YYYY-MM-DDTHH:mm"
      setScheduledDateTime(istTime)
    }
  }

  const handleUnschedule = (item: TwitterContentItem) => {
    const confirmUnschedule = confirm(
      `Cancel scheduled publish?\n\nThis will move the content back to "ready_to_schedule" status.`
    )

    if (confirmUnschedule) {
      unscheduleContent.mutate(item.id)
    }
  }

  const handlePublishNow = (item: TwitterContentItem) => {
    const confirmPublish = confirm(
      `Publish this content immediately?\n\n"${item.event_title}"\n\nThis will bypass the schedule and publish right away.`
    )

    if (confirmPublish) {
      publishNow.mutate(item.id)
    }
  }

  const handleResetForRepublish = (item: TwitterContentItem) => {
    const confirmReset = confirm(
      `Reset this content for republishing?\n\n"${item.event_title}"\n\nThis will:\n• Clear the published status\n• Allow you to schedule or publish again\n\nUse this if you deleted the tweet from X and want to post it again.`
    )

    if (confirmReset) {
      resetForRepublish.mutate(item.id)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "pending_generation":
        return <Clock className="h-4 w-4" />
      case "generating":
        return <Loader2 className="h-4 w-4 animate-spin" />
      case "pending_hitl":
        return <XCircle className="h-4 w-4" />
      case "ready_to_schedule":
        return <CheckCircle className="h-4 w-4" />
      case "scheduled":
        return <Clock className="h-4 w-4" />
      case "published":
        return <Send className="h-4 w-4" />
      case "failed":
        return <XCircle className="h-4 w-4" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending_generation":
        return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
      case "generating":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
      case "pending_hitl":
        return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300"
      case "ready_to_schedule":
        return "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
      case "scheduled":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
      case "published":
        return "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300"
      case "failed":
        return "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 dark:text-gray-400">Loading X content...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500 dark:text-red-400">Failed to load X content</div>
      </div>
    )
  }

  const content = data?.items || []

  const getModeColor = (mode: string) => {
    switch (mode) {
      case "LIVE":
        return "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 border-green-300 dark:border-green-700"
      case "DRY_RUN":
        return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300 border-yellow-300 dark:border-yellow-700"
      case "DISABLED":
        return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 border-gray-300 dark:border-gray-700"
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 border-gray-300 dark:border-gray-700"
    }
  }

  return (
    <div className="space-y-6">
      {/* Mode Banner */}
      {settings && settings.mode === "DRY_RUN" && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border-2 border-yellow-400 dark:border-yellow-700 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="text-3xl">🧪</div>
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-900 dark:text-yellow-100 text-lg">
                DRY RUN MODE ACTIVE
              </h3>
              <p className="text-yellow-800 dark:text-yellow-200 text-sm mt-1">
                Publishing is simulated - posts are NOT posted to real X.
                All "published" items are test runs only.
              </p>
            </div>
          </div>
        </div>
      )}

      {settings && settings.mode === "LIVE" && (
        <div className={`border-2 rounded-lg p-4 ${
          systemStatus?.publishing_enabled
            ? "bg-green-50 dark:bg-green-900/20 border-green-400 dark:border-green-700"
            : "bg-red-50 dark:bg-red-900/20 border-red-400 dark:border-red-700"
        }`}>
          <div className="flex items-center gap-3">
            <div className="text-3xl">{systemStatus?.publishing_enabled ? "🟢" : "🔴"}</div>
            <div className="flex-1">
              <h3 className={`font-semibold text-lg ${
                systemStatus?.publishing_enabled
                  ? "text-green-900 dark:text-green-100"
                  : "text-red-900 dark:text-red-100"
              }`}>
                {systemStatus?.publishing_enabled ? "LIVE MODE ACTIVE" : "LIVE MODE (Publishing Disabled)"}
              </h3>
              <p className={`text-sm mt-1 ${
                systemStatus?.publishing_enabled
                  ? "text-green-800 dark:text-green-200"
                  : "text-red-800 dark:text-red-200"
              }`}>
                {systemStatus?.publishing_enabled
                  ? "Publishing is LIVE - posts will be posted to your real X account."
                  : "Publishing is currently DISABLED. Enable it in settings to post to your real X account."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">X Content</h1>
            <Badge variant="outline" className="text-sm">
              {content.length} items
            </Badge>
            {settings && (
              <Badge
                variant="outline"
                className={`text-sm font-semibold ${getModeColor(settings.mode)}`}
              >
                {settings.mode === "DRY_RUN" && "🧪 "}
                {settings.mode === "LIVE" && "🔴 "}
                {settings.mode === "DISABLED" && "⏸️ "}
                {settings.mode.replace(/_/g, " ")}
              </Badge>
            )}
            <WorkerHealthBadge />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/approved-queue")}
            className="flex items-center gap-1"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Approved Queue
          </Button>
        </div>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Review, edit, and publish X-formatted content
          {settings && (
            <span className="ml-2 text-xs italic">
              ({settings.description})
            </span>
          )}
        </p>
      </div>

      {/* Content List */}
      {content.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <XLogo className="h-12 w-12 mx-auto text-gray-400 dark:text-gray-600 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No X content yet
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              Generate X content from approved outputs on the Outputs page
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6">
          {content.map((item) => (
            <Card key={item.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <CardTitle className="text-lg mb-2">{item.event_title}</CardTitle>
                    <div className="flex flex-wrap gap-2 items-center">
                      <Badge variant="outline">{item.event_type}</Badge>
                      <Badge
                        variant={item.format === "THREAD" ? "default" : "secondary"}
                        className="flex items-center gap-1"
                      >
                        <MessageSquare className="h-3 w-3" />
                        {item.format}
                        {item.format === "THREAD" && ` (${item.tweets?.length || parseThreadContent(item.content_text || "").length} posts)`}
                      </Badge>
                      <Badge className={`flex items-center gap-1 ${getStatusColor(item.status)}`}>
                        {getStatusIcon(item.status)}
                        {item.status.replace(/_/g, " ").toUpperCase()}
                      </Badge>
                      {item.is_edited && (
                        <Badge variant="outline" className="text-blue-600 dark:text-blue-400">
                          EDITED
                        </Badge>
                      )}
                    </div>
                  </div>
                  {item.event_url && (
                    <a
                      href={item.event_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Impact Framing */}
                {item.impact_framing && (
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Zap className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                      <h4 className="font-medium text-blue-900 dark:text-blue-100">
                        Impact Framing
                      </h4>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="font-medium text-blue-700 dark:text-blue-300">
                          Angle:{" "}
                        </span>
                        <span className="text-blue-900 dark:text-blue-100">
                          {item.impact_framing.primary_angle.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div>
                        <span className="font-medium text-blue-700 dark:text-blue-300">
                          What this is NOT:{" "}
                        </span>
                        <span className="text-blue-900 dark:text-blue-100">
                          {item.impact_framing.what_this_is_not}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* X Content */}
                <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium text-gray-900 dark:text-white flex items-center gap-2">
                      <XLogo className="h-4 w-4 text-blue-500" />
                      {item.format === "SINGLE" ? "Post" : `Thread (${item.tweets?.length || parseThreadContent(item.content_text || "").length} posts)`}
                    </h4>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {item.format === "SINGLE"
                        ? `${parseSingleContent(item.edited_content || item.content_text || "").length} chars`
                        : `${(item.tweets || parseThreadContent(item.content_text || "")).length} tweets`
                      }
                    </span>
                  </div>

                  {item.format === "SINGLE" ? (
                    <p className="text-gray-900 dark:text-white whitespace-pre-wrap">
                      {parseSingleContent(item.edited_content || item.content_text || "")}
                    </p>
                  ) : (
                    <ThreadDisplay
                      tweets={item.tweets || parseThreadContent(item.edited_content || item.content_text || "")}
                    />
                  )}

                  {item.hashtags && (
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Hashtags: {item.hashtags}
                      </span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="space-y-3 pt-2">
                  {/* Pending HITL Status - Requires Human Approval */}
                  {item.status === "pending_hitl" && (
                    <div className="space-y-3">
                      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <XCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                          <span className="font-medium text-yellow-900 dark:text-yellow-100">
                            Human Review Required
                          </span>
                        </div>
                        <p className="text-sm text-yellow-800 dark:text-yellow-200">
                          This content has been flagged for human review. Please approve or reject
                          it before it can be scheduled.
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          onClick={() => handleApproveHITL(item)}
                          disabled={approveHITL.isPending}
                          className="flex items-center gap-1 bg-green-600 hover:bg-green-700"
                        >
                          <CheckCircle className="h-3 w-3" />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleRejectHITL(item)}
                          disabled={rejectHITL.isPending}
                          className="flex items-center gap-1"
                        >
                          <XCircle className="h-3 w-3" />
                          Reject
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEdit(item)}
                          className="flex items-center gap-1"
                        >
                          <Edit className="h-3 w-3" />
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRegenerate(item)}
                          disabled={regenerateContent.isPending}
                          className="flex items-center gap-1"
                        >
                          <RefreshCw className={`h-3 w-3 ${regenerateContent.isPending ? "animate-spin" : ""}`} />
                          {regenerateContent.isPending ? "Regenerating..." : "Regenerate"}
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Ready to Schedule Status */}
                  {item.status === "ready_to_schedule" && (
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleEdit(item)}
                        className="flex items-center gap-1"
                      >
                        <Edit className="h-3 w-3" />
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleRegenerate(item)}
                        disabled={regenerateContent.isPending}
                        className="flex items-center gap-1"
                      >
                        <RefreshCw className={`h-3 w-3 ${regenerateContent.isPending ? "animate-spin" : ""}`} />
                        {regenerateContent.isPending ? "Regenerating..." : "Regenerate"}
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleScheduleSmart(item)}
                        disabled={scheduleContentSmart.isPending}
                        className="flex items-center gap-1 bg-blue-600 hover:bg-blue-700"
                      >
                        <Clock className="h-3 w-3" />
                        {scheduleContentSmart.isPending ? "Scheduling..." : "Schedule (Smart)"}
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handlePublishNow(item)}
                        disabled={publishNow.isPending}
                        className="flex items-center gap-1 bg-green-600 hover:bg-green-700"
                      >
                        <Zap className="h-3 w-3" />
                        Publish Now
                      </Button>
                    </div>
                  )}

                  {/* Scheduled Status */}
                  {item.status === "scheduled" && (
                    <>
                      {item.scheduled_for && <ScheduleDisplay scheduledFor={item.scheduled_for} />}
                      <div className="flex flex-wrap gap-2 mt-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleReschedule(item)}
                          className="flex items-center gap-1"
                        >
                          <Clock className="h-3 w-3" />
                          Reschedule
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleUnschedule(item)}
                          disabled={unscheduleContent.isPending}
                          className="flex items-center gap-1"
                        >
                          <XCircle className="h-3 w-3" />
                          Cancel Schedule
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handlePublishNow(item)}
                          disabled={publishNow.isPending}
                          className="flex items-center gap-1 bg-orange-600 hover:bg-orange-700"
                        >
                          <Zap className="h-3 w-3" />
                          Publish Now
                        </Button>
                      </div>
                    </>
                  )}

                  {/* Failed Status with Retry Info */}
                  {item.status === "failed" && (
                    <>
                      {item.retry_count !== undefined && item.retry_count < 3 && (
                        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
                          <p className="text-sm text-yellow-700 dark:text-yellow-300">
                            Publishing failed - will auto-retry
                          </p>
                          <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                            Attempt {(item.retry_count || 0) + 1}/3
                            {item.last_publish_attempt && (
                              <> • Last attempt: {formatDate(item.last_publish_attempt)}</>
                            )}
                          </p>
                        </div>
                      )}
                      {item.retry_count !== undefined && item.retry_count >= 3 && (
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                          <p className="text-sm text-red-700 dark:text-red-300">
                            Publishing failed after 3 attempts - manual intervention required
                          </p>
                        </div>
                      )}
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEdit(item)}
                          className="flex items-center gap-1"
                        >
                          <Edit className="h-3 w-3" />
                          Edit & Retry
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRegenerate(item)}
                          disabled={regenerateContent.isPending}
                          className="flex items-center gap-1"
                        >
                          <RefreshCw className={`h-3 w-3 ${regenerateContent.isPending ? "animate-spin" : ""}`} />
                          {regenerateContent.isPending ? "Regenerating..." : "Regenerate"}
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handlePublishNow(item)}
                          disabled={publishNow.isPending}
                          className="flex items-center gap-1 bg-orange-600 hover:bg-orange-700"
                        >
                          <Zap className="h-3 w-3" />
                          Retry Now
                        </Button>
                      </div>
                    </>
                  )}

                  {/* Published Status */}
                  {item.status === "published" && (
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2 text-sm">
                        <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          Published on {item.published_at && formatDate(item.published_at)}
                        </div>
                        {item.twitter_post_id?.startsWith("dry_run_") && (
                          <Badge variant="outline" className="text-yellow-600 dark:text-yellow-400 border-yellow-400">
                            🧪 DRY RUN
                          </Badge>
                        )}
                        {item.twitter_post_id && !item.twitter_post_id.startsWith("dry_run_") && (
                          <Badge variant="outline" className="text-green-600 dark:text-green-400 border-green-400">
                            ✓ LIVE
                          </Badge>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleResetForRepublish(item)}
                          disabled={resetForRepublish.isPending}
                          className="flex items-center gap-1"
                        >
                          <RefreshCw className={`h-3 w-3 ${resetForRepublish.isPending ? "animate-spin" : ""}`} />
                          {resetForRepublish.isPending ? "Resetting..." : "Republish"}
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Delete Button for non-live published items */}
                  {(item.status !== "published" || item.twitter_post_id?.startsWith("dry_run_")) && (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDelete(item)}
                      disabled={deleteContent.isPending}
                      className="flex items-center gap-1"
                    >
                      <Trash2 className="h-3 w-3" />
                      Delete
                    </Button>
                  )}
                </div>

                {/* Metadata */}
<div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    Created {formatDate(item.created_at)}
                    {item.updated_at && item.updated_at !== item.created_at && (
                      <> · Updated {formatDate(item.updated_at)}</>
                    )}
                    {item.scheduled_for && item.status === "scheduled" && (
                      <> · <span className="text-blue-600 dark:text-blue-400 font-medium">⏰ Scheduled for {formatDate(item.scheduled_for)}</span></>
                    )}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Edit Modal */}
      {selectedContent && (
        <EditContentModal
          isOpen={editModalOpen}
          onClose={() => {
            setEditModalOpen(false)
            setSelectedContent(null)
          }}
          onSave={handleSaveEdit}
          originalContent={selectedContent.content_text || ""}
          currentEditedContent={selectedContent.edited_content}
          hashtags={selectedContent.hashtags ? [selectedContent.hashtags] : []}
          format={selectedContent.format as "SINGLE" | "THREAD"}
        />
      )}

      {/* Schedule Modal */}
      {scheduleModalOpen && selectedContent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Schedule Content</CardTitle>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                {selectedContent.event_title}
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900 dark:text-white">
                  Publish Date & Time (IST)
                </label>
                <input
                  type="datetime-local"
                  value={scheduledDateTime}
                  onChange={(e) => setScheduledDateTime(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Content will be published automatically at the scheduled time
                </p>
              </div>

              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setScheduleModalOpen(false)
                    setSelectedContent(null)
                    setScheduledDateTime("")
                  }}
                >
                  Cancel
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleSchedule}
                  disabled={!scheduledDateTime || scheduleContent.isPending || rescheduleContent.isPending}
                >
                  {scheduleContent.isPending || rescheduleContent.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Scheduling...
                    </>
                  ) : (
                    <>
                      <Clock className="h-4 w-4 mr-2" />
                      Schedule
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Rejection Modal */}
      {rejectModalOpen && selectedContent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-md w-full bg-white dark:bg-gray-900">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <XCircle className="h-5 w-5 text-red-500" />
                Reject Content
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
                  You are rejecting: <strong>{selectedContent.event_title}</strong>
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Please provide a reason for rejection. This will help improve future content generation.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900 dark:text-white">
                  Rejection Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="E.g., Contains advice-like language, Too promotional, Inaccurate information..."
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-red-500 dark:focus:ring-red-400"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  This reason will be stored with the content and used to improve the system.
                </p>
              </div>

              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setRejectModalOpen(false)
                    setSelectedContent(null)
                    setRejectionReason("")
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={confirmRejectHITL}
                  disabled={!rejectionReason.trim() || rejectHITL.isPending}
                >
                  {rejectHITL.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Rejecting...
                    </>
                  ) : (
                    <>
                      <XCircle className="h-4 w-4 mr-2" />
                      Reject Content
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
