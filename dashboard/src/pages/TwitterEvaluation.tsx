import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { twitterApi } from "@/api/client"
import type { TwitterContentItem } from "@/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { formatDate } from "@/lib/utils"
import {
  CheckCircle,
  XCircle,
  Twitter,
  Loader2,
  MessageSquare,
} from "lucide-react"

export function TwitterEvaluation() {
  const [selectedContent, setSelectedContent] = useState<TwitterContentItem | null>(null)

  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ["twitter-evaluation"],
    queryFn: () => twitterApi.list({ status: "ready_to_schedule", limit: 50 }),
    refetchInterval: 5000,
  })

  const publishContent = useMutation({
    mutationFn: (contentQueueId: string) => twitterApi.publish(contentQueueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-evaluation"] })
      setSelectedContent(null)
    },
  })

  const deleteContent = useMutation({
    mutationFn: (contentQueueId: string) => twitterApi.delete(contentQueueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-evaluation"] })
      setSelectedContent(null)
    },
  })

  const handleApprove = (item: TwitterContentItem) => {
    const confirmPublish = confirm(
      `Approve this Twitter content for publishing?\n\n"${item.event_title}"`
    )

    if (confirmPublish) {
      publishContent.mutate(item.id)
    }
  }

  const handleReject = (item: TwitterContentItem) => {
    const confirmReject = confirm(
      `Reject and delete this Twitter content?\n\n"${item.event_title}"\n\nThis action cannot be undone.`
    )

    if (confirmReject) {
      deleteContent.mutate(item.id)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500 dark:text-red-400">Failed to load Twitter content</div>
      </div>
    )
  }

  const content = data?.items || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <Twitter className="h-8 w-8 text-blue-500" />
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Twitter Evaluation</h1>
          <Badge variant="outline" className="text-sm">
            {content.length} items pending
          </Badge>
        </div>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Review and approve Twitter content before publishing
        </p>
      </div>

      {/* Content List */}
      {content.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Twitter className="h-12 w-12 mx-auto text-gray-400 dark:text-gray-600 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No Twitter content pending review
            </h3>
            <p className="text-gray-500 dark:text-gray-400">
              All generated Twitter content has been reviewed
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6">
          {content.map((item) => (
            <Card
              key={item.id}
              className={`cursor-pointer transition-all ${
                selectedContent?.id === item.id ? "ring-2 ring-blue-500" : "hover:shadow-md"
              }`}
              onClick={() => setSelectedContent(item)}
            >
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
                      </Badge>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Twitter Content Preview */}
                <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                  {item.format === "SINGLE" ? (
                    <p className="text-sm">{item.tweets?.[0] || item.content_text}</p>
                  ) : (
                    <div className="space-y-2">
                      {item.tweets?.map((tweet, idx) => (
                        <div key={idx} className="border-l-2 border-blue-500 pl-3">
                          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                            Tweet {idx + 1}/{item.tweets?.length}
                          </div>
                          <p className="text-sm">{tweet}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="mt-2 text-xs text-gray-500">
                    {item.format === "SINGLE"
                      ? `${item.tweets?.[0]?.length || 0} characters`
                      : `${item.thread_length} tweets`}
                  </div>
                </div>

                {/* Action Buttons */}
                {selectedContent?.id === item.id && (
                  <div className="flex gap-3 pt-4 border-t">
                    <Button
                      variant="success"
                      className="flex-1"
                      onClick={() => handleApprove(item)}
                      disabled={publishContent.isPending}
                    >
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Approve & Publish
                    </Button>
                    <Button
                      variant="destructive"
                      className="flex-1"
                      onClick={() => handleReject(item)}
                      disabled={deleteContent.isPending}
                    >
                      <XCircle className="h-4 w-4 mr-2" />
                      Reject
                    </Button>
                  </div>
                )}

                <div className="text-xs text-gray-400 dark:text-gray-500">
                  Created: {formatDate(item.created_at)}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
