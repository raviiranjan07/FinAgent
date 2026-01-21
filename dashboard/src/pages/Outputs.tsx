import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { outputsApi, evaluationsApi } from "@/api/client"
import type { Output } from "@/api/client"
import { useWebSocket } from "@/hooks/useWebSocket"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { formatDate, truncate } from "@/lib/utils"
import {
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  AlertTriangle,
  Wifi,
  WifiOff,
} from "lucide-react"

export function Outputs() {
  const [page, setPage] = useState(1)
  const [pendingOnly, setPendingOnly] = useState(true)
  const [selectedOutputId, setSelectedOutputId] = useState<string | null>(null)
  const [failureReason, setFailureReason] = useState("")
  const [comment, setComment] = useState("")

  const queryClient = useQueryClient()
  const { subscribe, isConnected } = useWebSocket()

  // Fetch full output details when selected
  const { data: selectedOutput } = useQuery({
    queryKey: ["output-detail", selectedOutputId],
    queryFn: () => outputsApi.get(selectedOutputId!),
    enabled: !!selectedOutputId,
  })

  // Listen for WebSocket events to auto-refresh
  useEffect(() => {
    const unsubscribe = subscribe((message) => {
      if (message.type === "NEW_EVALUATION" || message.type === "NEW_OUTPUT") {
        // Refetch outputs and stats when new evaluation/output arrives
        queryClient.invalidateQueries({ queryKey: ["outputs"] })
        queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
      }
    })
    return unsubscribe
  }, [subscribe, queryClient])

  const { data, isLoading, error } = useQuery({
    queryKey: ["outputs", page, pendingOnly],
    queryFn: () => outputsApi.list(page, 20, { pending_only: pendingOnly }),
  })

  const createEvaluation = useMutation({
    mutationFn: evaluationsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outputs"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
      setSelectedOutputId(null)
      setFailureReason("")
      setComment("")
    },
  })

  const handleEvaluate = (verdict: "PASS" | "FAIL") => {
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
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading outputs...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">Failed to load outputs</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">Content Outputs</h1>
            {isConnected ? (
              <span className="flex items-center gap-1 text-xs text-green-600">
                <Wifi className="h-3 w-3" />
                Live
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-gray-400">
                <WifiOff className="h-3 w-3" />
                Offline
              </span>
            )}
          </div>
          <p className="text-gray-500 mt-1">Review and evaluate LLM-generated content</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={pendingOnly ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setPendingOnly(true)
              setPage(1)
            }}
          >
            Pending Only
          </Button>
          <Button
            variant={!pendingOnly ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setPendingOnly(false)
              setPage(1)
            }}
          >
            All Outputs
          </Button>
        </div>
      </div>

      {/* Output List */}
      <div className="grid gap-4">
        {data?.items?.length ? (
          data.items.map((output) => (
            <Card
              key={output.id}
              className={`cursor-pointer transition-all ${
                selectedOutputId === output.id ? "ring-2 ring-blue-500" : "hover:shadow-md"
              }`}
              onClick={() => setSelectedOutputId(output.id)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg">
                      {truncate(output.event_title || "Untitled", 80)}
                    </CardTitle>
                    <div className="flex items-center gap-2 flex-wrap text-sm text-muted-foreground">
                      <Badge variant="secondary">{output.event_source}</Badge>
                      <Badge variant="outline">{output.event_type}</Badge>
                      {output.event_published_at && (
                        <span className="text-xs text-gray-600">
                          Published: {formatDate(output.event_published_at)}
                        </span>
                      )}
                      <span className="text-xs text-gray-400">
                        Processed: {formatDate(output.created_at)}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {output.hitl_required && (
                      <Badge variant="warning" className="flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" />
                        HITL
                      </Badge>
                    )}
                    {output.has_evaluation ? (
                      <Badge variant={output.evaluation_verdict === "PASS" ? "success" : "destructive"}>
                        {output.evaluation_verdict}
                      </Badge>
                    ) : (
                      <Badge variant="secondary">Pending</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600 whitespace-pre-wrap line-clamp-3">
                  {output.llm_output}
                </p>
                {output.clarity_issues?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {output.clarity_issues.map((issue, idx) => (
                      <Badge key={idx} variant="warning" className="text-xs">
                        {issue}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        ) : (
          <Card>
            <CardContent className="py-8 text-center text-gray-500">
              {pendingOnly
                ? "No pending outputs to evaluate. Great job!"
                : "No outputs found. Run the pipeline first."}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <span className="text-sm text-gray-500">
            Page {page} of {data.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
            disabled={page === data.total_pages}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* View/Evaluation Modal */}
      {selectedOutput && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>
                  {selectedOutput.has_evaluation ? "View Content" : "Evaluate Content"}
                </CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setSelectedOutputId(null)}>
                  Close
                </Button>
              </div>
              <CardDescription>
                {selectedOutput.event_title}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Output Preview */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-medium mb-2">LLM Output:</h4>
                <p className="text-sm whitespace-pre-wrap">{selectedOutput.llm_output}</p>
              </div>

              {/* Metadata */}
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">Type: {selectedOutput.event_type}</Badge>
                <Badge variant="outline">Intent: {selectedOutput.intent}</Badge>
                {selectedOutput.event?.link && (
                  <a
                    href={selectedOutput.event.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Source
                  </a>
                )}
              </div>

              {/* Clarity Issues */}
              {selectedOutput.clarity_issues?.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2 text-yellow-600">Clarity Issues:</h4>
                  <ul className="list-disc list-inside text-sm text-yellow-700">
                    {selectedOutput.clarity_issues.map((issue, idx) => (
                      <li key={idx}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Show Evaluation if Already Evaluated */}
              {selectedOutput.has_evaluation && selectedOutput.evaluation ? (
                <div className="pt-4 border-t">
                  <h4 className="font-medium mb-3">Evaluation Result:</h4>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      {selectedOutput.evaluation.verdict === "PASS" ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-500" />
                      )}
                      <Badge variant={selectedOutput.evaluation.verdict === "PASS" ? "success" : "destructive"}>
                        {selectedOutput.evaluation.verdict}
                      </Badge>
                      {selectedOutput.evaluation.failure_reason && (
                        <Badge variant="outline">{selectedOutput.evaluation.failure_reason}</Badge>
                      )}
                    </div>
                    {selectedOutput.evaluation.comment && (
                      <div className="bg-gray-50 p-3 rounded-md">
                        <p className="text-sm text-gray-700">{selectedOutput.evaluation.comment}</p>
                      </div>
                    )}
                    <p className="text-xs text-gray-400">
                      Evaluated by {selectedOutput.evaluation.evaluator || "unknown"} on{" "}
                      {formatDate(selectedOutput.evaluation.evaluated_at)}
                    </p>
                  </div>
                  <div className="mt-4 text-sm text-gray-500">
                    To edit this evaluation, go to the Evaluations page.
                  </div>
                </div>
              ) : (
                /* Evaluation Form for Unevaluated Outputs */
                <div className="space-y-4 pt-4 border-t">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Comment (optional)
                    </label>
                    <textarea
                      className="w-full px-3 py-2 border rounded-md text-sm"
                      rows={2}
                      placeholder="Any additional notes..."
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Failure Reason (required for FAIL)
                    </label>
                    <select
                      className="w-full px-3 py-2 border rounded-md text-sm"
                      value={failureReason}
                      onChange={(e) => setFailureReason(e.target.value)}
                    >
                      <option value="">Select a reason...</option>
                      <option value="ADVICE_DETECTED">Advice Detected</option>
                      <option value="PREDICTION_MADE">Prediction Made</option>
                      <option value="JARGON_NOT_EXPLAINED">Jargon Not Explained</option>
                      <option value="FACTUAL_ERROR">Factual Error</option>
                      <option value="INCOMPLETE_EXPLANATION">Incomplete Explanation</option>
                      <option value="SENSATIONALISM">Sensationalism</option>
                      <option value="OTHER">Other</option>
                    </select>
                  </div>

                  <div className="flex gap-3">
                    <Button
                      variant="success"
                      className="flex-1"
                      onClick={() => handleEvaluate("PASS")}
                      disabled={createEvaluation.isPending}
                    >
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Pass
                    </Button>
                    <Button
                      variant="destructive"
                      className="flex-1"
                      onClick={() => handleEvaluate("FAIL")}
                      disabled={createEvaluation.isPending}
                    >
                      <XCircle className="h-4 w-4 mr-2" />
                      Fail
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
