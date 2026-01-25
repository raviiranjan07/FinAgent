import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { outputsApi, evaluationsApi, twitterApi } from "@/api/client"
import type { Output, TwitterContentItem } from "@/api/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { MarkdownContent } from "@/components/MarkdownContent"
import { formatDate } from "@/lib/utils"
import {
  CheckCircle,
  XCircle,
  FileText,
  Twitter,
  Loader2,
  MessageSquare,
} from "lucide-react"

export function EvaluationQueue() {
  // Content Evaluation State
  const [selectedOutput, setSelectedOutput] = useState<Output | null>(null)
  const [verdict, setVerdict] = useState<"PASS" | "FAIL">("PASS")
  const [failureReason, setFailureReason] = useState("")
  const [comment, setComment] = useState("")

  // Twitter Evaluation State
  const [selectedTwitter, setSelectedTwitter] = useState<TwitterContentItem | null>(null)

  const queryClient = useQueryClient()

  // Fetch pending content evaluations
  const { data: contentData, isLoading: contentLoading } = useQuery({
    queryKey: ["pending-outputs"],
    queryFn: () => outputsApi.list(1, 50, { pending_only: true }),
    refetchInterval: 5000,
  })

  // Fetch pending Twitter evaluations
  const { data: twitterData, isLoading: twitterLoading } = useQuery({
    queryKey: ["twitter-evaluation"],
    queryFn: () => twitterApi.list({ status: "ready_to_schedule", limit: 50 }),
    refetchInterval: 5000,
  })

  // Create evaluation mutation
  const createEvaluation = useMutation({
    mutationFn: evaluationsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pending-outputs"] })
      queryClient.invalidateQueries({ queryKey: ["evaluations"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
      setSelectedOutput(null)
      setVerdict("PASS")
      setFailureReason("")
      setComment("")
    },
  })

  // Twitter publish mutation
  const publishTwitter = useMutation({
    mutationFn: (contentQueueId: string) => twitterApi.publish(contentQueueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-evaluation"] })
      setSelectedTwitter(null)
    },
  })

  // Twitter delete mutation
  const deleteTwitter = useMutation({
    mutationFn: (contentQueueId: string) => twitterApi.delete(contentQueueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["twitter-evaluation"] })
      setSelectedTwitter(null)
    },
  })

  const handleSubmitEvaluation = () => {
    if (!selectedOutput) return
    if (verdict === "FAIL" && !failureReason) {
      alert("Please provide a failure reason")
      return
    }

    createEvaluation.mutate({
      output_id: selectedOutput.id,
      verdict,
      failure_reason: verdict === "FAIL" ? failureReason : undefined,
      comment: comment || undefined,
      evaluator: "human",
    })
  }

  const handleApproveTwitter = (item: TwitterContentItem) => {
    const confirmPublish = confirm(
      `Approve this Twitter content for publishing?\n\n"${item.event_title}"`
    )
    if (confirmPublish) {
      publishTwitter.mutate(item.id)
    }
  }

  const handleRejectTwitter = (item: TwitterContentItem) => {
    const confirmReject = confirm(
      `Reject and delete this Twitter content?\n\n"${item.event_title}"\n\nThis action cannot be undone.`
    )
    if (confirmReject) {
      deleteTwitter.mutate(item.id)
    }
  }

  const contentItems = contentData?.items || []
  const twitterItems = twitterData?.items || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Evaluation Queue</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Review generated content and Twitter posts before publishing
        </p>
      </div>

      {/* Split Screen Layout */}
      <div className="grid grid-cols-2 gap-6">
        {/* LEFT: Content Evaluation */}
        <div className="flex flex-col space-y-4">
          <div className="flex items-center gap-3">
            <FileText className="h-6 w-6 text-blue-500" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Content Evaluation</h2>
            <Badge variant="outline" className="text-sm">
              {contentItems.length} pending
            </Badge>
          </div>

          {contentLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            </div>
          ) : contentItems.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <FileText className="h-12 w-12 mx-auto text-gray-400 dark:text-gray-600 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  No content pending evaluation
                </h3>
                <p className="text-gray-500 dark:text-gray-400">
                  All generated content has been evaluated
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* List View */}
              <div className="space-y-2">
                {contentItems.map((output) => (
                  <Card
                    key={output.id}
                    className={`cursor-pointer transition-all ${
                      selectedOutput?.id === output.id
                        ? "ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20"
                        : "hover:shadow-md"
                    }`}
                    onClick={() => setSelectedOutput(output)}
                  >
                    <CardContent className="p-4">
                      <h3 className="font-medium text-sm line-clamp-2">{output.event_title}</h3>
                      <div className="flex gap-2 mt-2">
                        <Badge variant="outline" className="text-xs">{output.event_type}</Badge>
                        <Badge variant="secondary" className="text-xs">{output.intent}</Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Detail View */}
              {selectedOutput && (
                <Card>
                  <CardHeader>
                    <CardTitle>{selectedOutput.event_title}</CardTitle>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">{selectedOutput.event_type}</Badge>
                      <Badge variant="secondary">{selectedOutput.intent}</Badge>
                      {selectedOutput.hitl_required && (
                        <Badge variant="warning">HITL Required</Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Content */}
                    <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                      <MarkdownContent content={selectedOutput.llm_output} />
                    </div>

                    {/* Evaluation Form */}
                    <div className="space-y-3 pt-3 border-t">
                      <div className="flex gap-2">
                        <Button
                          variant={verdict === "PASS" ? "success" : "outline"}
                          onClick={() => setVerdict("PASS")}
                          className="flex-1"
                        >
                          <CheckCircle className="h-4 w-4 mr-2" />
                          PASS
                        </Button>
                        <Button
                          variant={verdict === "FAIL" ? "destructive" : "outline"}
                          onClick={() => setVerdict("FAIL")}
                          className="flex-1"
                        >
                          <XCircle className="h-4 w-4 mr-2" />
                          FAIL
                        </Button>
                      </div>

                      {verdict === "FAIL" && (
                        <select
                          className="w-full px-3 py-2 border rounded bg-white dark:bg-gray-700"
                          value={failureReason}
                          onChange={(e) => setFailureReason(e.target.value)}
                        >
                          <option value="">Select reason...</option>
                          <option value="ADVICE_DETECTED">Advice Detected</option>
                          <option value="PREDICTION_MADE">Prediction Made</option>
                          <option value="JARGON_NOT_EXPLAINED">Jargon Not Explained</option>
                          <option value="FACTUAL_ERROR">Factual Error</option>
                          <option value="INCOMPLETE_EXPLANATION">Incomplete</option>
                          <option value="SENSATIONALISM">Sensationalism</option>
                        </select>
                      )}

                      <textarea
                        className="w-full px-3 py-2 border rounded bg-white dark:bg-gray-700"
                        rows={3}
                        placeholder="Comment (optional)..."
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                      />

                      <Button
                        onClick={handleSubmitEvaluation}
                        disabled={createEvaluation.isPending}
                        className="w-full"
                      >
                        {createEvaluation.isPending ? "Submitting..." : "Submit Evaluation"}
                      </Button>
                    </div>

                    <div className="text-xs text-gray-400">
                      Created: {formatDate(selectedOutput.created_at)}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>

        {/* RIGHT: Twitter Evaluation */}
        <div className="flex flex-col space-y-4">
          <div className="flex items-center gap-3">
            <Twitter className="h-6 w-6 text-blue-500" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Twitter Evaluation</h2>
            <Badge variant="outline" className="text-sm">
              {twitterItems.length} pending
            </Badge>
          </div>

          {twitterLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            </div>
          ) : twitterItems.length === 0 ? (
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
            <>
              {/* List View */}
              <div className="space-y-2">
                {twitterItems.map((item) => (
                  <Card
                    key={item.id}
                    className={`cursor-pointer transition-all ${
                      selectedTwitter?.id === item.id
                        ? "ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20"
                        : "hover:shadow-md"
                    }`}
                    onClick={() => setSelectedTwitter(item)}
                  >
                    <CardContent className="p-4">
                      <h3 className="font-medium text-sm line-clamp-2">{item.event_title}</h3>
                      <div className="flex gap-2 mt-2">
                        <Badge variant="outline" className="text-xs">{item.event_type}</Badge>
                        <Badge
                          variant={item.format === "THREAD" ? "default" : "secondary"}
                          className="flex items-center gap-1 text-xs"
                        >
                          <MessageSquare className="h-3 w-3" />
                          {item.format}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Detail View */}
              {selectedTwitter && (
                <Card>
                  <CardHeader>
                    <CardTitle>{selectedTwitter.event_title}</CardTitle>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">{selectedTwitter.event_type}</Badge>
                      <Badge
                        variant={selectedTwitter.format === "THREAD" ? "default" : "secondary"}
                        className="flex items-center gap-1"
                      >
                        <MessageSquare className="h-3 w-3" />
                        {selectedTwitter.format}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Twitter Content */}
                    <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                      {selectedTwitter.format === "SINGLE" ? (
                        <p className="text-sm whitespace-pre-wrap">
                          {selectedTwitter.tweets?.[0] || selectedTwitter.content_text}
                        </p>
                      ) : (
                        <div className="space-y-3">
                          {selectedTwitter.tweets?.map((tweet, idx) => (
                            <div key={idx} className="border-l-2 border-blue-500 pl-3">
                              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                                Tweet {idx + 1}/{selectedTwitter.tweets?.length}
                              </div>
                              <p className="text-sm whitespace-pre-wrap">{tweet}</p>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
                        {selectedTwitter.format === "SINGLE"
                          ? `${selectedTwitter.tweets?.[0]?.length || 0} characters`
                          : `${selectedTwitter.thread_length} tweets`}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3 pt-3 border-t">
                      <Button
                        variant="success"
                        className="flex-1"
                        onClick={() => handleApproveTwitter(selectedTwitter)}
                        disabled={publishTwitter.isPending}
                      >
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Approve
                      </Button>
                      <Button
                        variant="destructive"
                        className="flex-1"
                        onClick={() => handleRejectTwitter(selectedTwitter)}
                        disabled={deleteTwitter.isPending}
                      >
                        <XCircle className="h-4 w-4 mr-2" />
                        Reject
                      </Button>
                    </div>

                    <div className="text-xs text-gray-400">
                      Created: {formatDate(selectedTwitter.created_at)}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
