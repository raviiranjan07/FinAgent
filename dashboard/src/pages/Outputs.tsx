import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { outputsApi, evaluationsApi, twitterApi } from "@/api/client"
import { useWebSocket } from "@/hooks/useWebSocket"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { MarkdownContent } from "@/components/MarkdownContent"
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
  Trash2,
  Bot,
  Info,
  Loader2,
  ArrowRight,
  ArrowUpDown,
} from "lucide-react"

// X Logo Component
const XLogo = ({ className = "h-4 w-4" }: { className?: string }) => (
  <svg viewBox="0 0 24 24" className={className} fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
)

export function Outputs() {
  const [page, setPage] = useState(1)
  const [pendingOnly, setPendingOnly] = useState(true)
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")
  const [selectedIntent, setSelectedIntent] = useState<string | undefined>(undefined)
  const [selectedOutputId, setSelectedOutputId] = useState<string | null>(null)
  const [failureReason, setFailureReason] = useState("")  // Legacy, kept for backwards compat
  const [correctedEventType, setCorrectedEventType] = useState("")
  const [correctedIntent, setCorrectedIntent] = useState("")
  const [comment, setComment] = useState("")
  const [generatingTwitter, setGeneratingTwitter] = useState(false)
  const [twitterGenSuccess, setTwitterGenSuccess] = useState(false)
  const [twitterGenError, setTwitterGenError] = useState<string | null>(null)
  const [selectedForDeletion, setSelectedForDeletion] = useState<Set<string>>(new Set())

  const queryClient = useQueryClient()
  const navigate = useNavigate()
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
    queryKey: ["outputs", page, pendingOnly, sortOrder, selectedIntent],
    queryFn: () => outputsApi.list(page, 20, { pending_only: pendingOnly, sort_order: sortOrder, intent: selectedIntent }),
  })

  const { data: intentsData } = useQuery({
    queryKey: ["output-intents"],
    queryFn: () => outputsApi.getIntents(),
  })

  const createEvaluation = useMutation({
    mutationFn: evaluationsApi.create,
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["outputs"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })

      // Clear form fields
      setFailureReason("")
      setCorrectedEventType("")
      setCorrectedIntent("")
      setComment("")

      // Auto-generate Twitter content for PASS verdicts
      if (variables.verdict === "PASS" && selectedOutput) {
        console.log("[Auto-gen] Triggering Twitter generation for output:", selectedOutput.id)
        setTwitterGenSuccess(false)
        setTwitterGenError(null)
        generateTwitterContent.mutate(selectedOutput.id)
        // Don't close panel - let user see generation progress
      } else {
        // For FAIL/ACCEPT, close panel immediately
        setSelectedOutputId(null)
      }
    },
  })

  const deleteOutput = useMutation({
    mutationFn: async (outputId: string) => {
      const response = await fetch(`/api/selection/delete-output/${outputId}`, {
        method: "DELETE",
      })
      if (!response.ok) {
        throw new Error("Failed to delete output")
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outputs"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
      setSelectedOutputId(null)
    },
  })

  const deleteSelectedOutputs = useMutation({
    mutationFn: async (outputIds: string[]) => {
      const response = await fetch(`/api/selection/delete-selected-outputs`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ output_ids: outputIds }),
      })
      if (!response.ok) {
        throw new Error("Failed to delete selected outputs")
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outputs"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
      setSelectedForDeletion(new Set())
      setSelectedOutputId(null)
    },
  })

  const generateTwitterContent = useMutation({
    mutationFn: (outputId: string) => {
      console.log("[Auto-gen] Calling twitterApi.generate for:", outputId)
      return twitterApi.generate(outputId)
    },
    onSuccess: (data) => {
      console.log("[Auto-gen] Twitter generation successful:", data)
      setTwitterGenSuccess(true)
      setTwitterGenError(null)
      // Navigate to Generated Content screen after 1.5 seconds
      setTimeout(() => {
        console.log("[Auto-gen] Navigating to generated-content page")
        navigate("/generated-content")
        setSelectedOutputId(null) // Close panel after navigation
      }, 1500)
    },
    onError: (error: any) => {
      console.error("[Auto-gen] Twitter generation failed:", error)
      const errorMsg = error.response?.data?.message || error.response?.data?.detail || "Failed to generate X content"
      setTwitterGenError(errorMsg)
      setTwitterGenSuccess(false)
      // Keep panel open so user can see error and retry
    },
  })

  const getIntentColor = (intent: string | null | undefined): string => {
    if (!intent) return ""

    switch (intent) {
      case "EXPLANATORY":
        return "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-700"
      case "DESCRIPTIVE":
        return "bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600"
      case "MARKET_OPINION":
        return "bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 border-orange-300 dark:border-orange-700"
      case "BREAKING_NEWS":
        return "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700"
      case "DATA_RELEASE":
        return "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border-green-300 dark:border-green-700"
      default:
        return "bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600"
    }
  }

  const handleEvaluate = (verdict: "PASS" | "FAIL" | "ACCEPT") => {
    if (!selectedOutput) return

    // FAIL and ACCEPT require both dropdowns to be filled
    if (verdict !== "PASS" && (!correctedEventType || !correctedIntent)) {
      alert("Please select both Event Type and Intent for FAIL/ACCEPT verdicts")
      return
    }

    createEvaluation.mutate({
      output_id: selectedOutput.id,
      verdict,
      corrected_event_type: verdict !== "PASS" ? correctedEventType : undefined,
      corrected_intent: verdict !== "PASS" ? correctedIntent : undefined,
      comment: comment || undefined,
    })
  }

  const handleDelete = () => {
    if (!selectedOutput) return

    const confirmDelete = confirm(
      `Are you sure you want to delete this output?\n\nTitle: ${selectedOutput.event_title}\n\nThis will also delete all related evaluations, content queue entries, and generated content. This action cannot be undone.`
    )

    if (confirmDelete) {
      deleteOutput.mutate(selectedOutput.id)
    }
  }

  const handleGenerateTwitter = () => {
    if (!selectedOutput) return

    setGeneratingTwitter(true)
    setTwitterGenError(null)
    setTwitterGenSuccess(false)

    generateTwitterContent.mutate(selectedOutput.id, {
      onSettled: () => {
        setGeneratingTwitter(false)
      },
    })
  }

  const toggleSelection = (outputId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedForDeletion((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(outputId)) {
        newSet.delete(outputId)
      } else {
        newSet.add(outputId)
      }
      return newSet
    })
  }

  const toggleSelectAll = () => {
    if (!data?.items) return

    if (selectedForDeletion.size === data.items.length) {
      // Deselect all
      setSelectedForDeletion(new Set())
    } else {
      // Select all
      setSelectedForDeletion(new Set(data.items.map((item) => item.id)))
    }
  }

  const handleDeleteSelected = () => {
    if (selectedForDeletion.size === 0) {
      alert("No outputs selected")
      return
    }

    const confirmDelete = confirm(
      `Are you sure you want to delete ${selectedForDeletion.size} selected output(s)?\n\nThis will permanently remove:\n- Selected outputs\n- Related evaluations\n- Related content queue entries\n- Related generated content\n\nThis action CANNOT be undone!`
    )

    if (confirmDelete) {
      deleteSelectedOutputs.mutate(Array.from(selectedForDeletion))
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 dark:text-gray-400">Loading outputs...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500 dark:text-red-400">Failed to load outputs</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Content Outputs</h1>
            {isConnected ? (
              <span className="flex items-center gap-1 text-xs font-semibold" style={{ color: '#16a34a' }}>
                <Wifi className="h-3 w-3" style={{ color: '#16a34a' }} />
                Live
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
                <WifiOff className="h-3 w-3" />
                Offline
              </span>
            )}
          </div>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Review and evaluate LLM-generated content</p>
        </div>
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSortOrder(sortOrder === "desc" ? "asc" : "desc")
              setPage(1)
            }}
            className="flex items-center gap-1"
          >
            <ArrowUpDown className="h-4 w-4" />
            {sortOrder === "desc" ? "Newest First" : "Oldest First"}
          </Button>
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
      </div>

      {/* Intent Filter */}
      <div className="flex gap-2 flex-wrap">
        <Button
          variant={selectedIntent === undefined ? "default" : "outline"}
          size="sm"
          onClick={() => {
            setSelectedIntent(undefined)
            setPage(1)
          }}
        >
          All Intents
        </Button>
        {intentsData?.intents && Object.entries(intentsData.intents).map(([intent, count]) => (
          <Button
            key={intent}
            variant={selectedIntent === intent ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setSelectedIntent(intent)
              setPage(1)
            }}
            className={getIntentColor(intent)}
          >
            {intent.replace(/_/g, " ")} ({count as number})
          </Button>
        ))}
      </div>

      {/* Selection Controls */}
      {data && data.items && data.items.length > 0 && (
        <div className="flex items-center justify-between bg-gray-50 dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={data.items.length > 0 && selectedForDeletion.size === data.items.length}
                onChange={toggleSelectAll}
                className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-2 focus:ring-blue-500 cursor-pointer"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Select All ({data.items.length})
              </span>
            </label>
            {selectedForDeletion.size > 0 && (
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {selectedForDeletion.size} selected
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {selectedForDeletion.size > 0 && (
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDeleteSelected}
                disabled={deleteSelectedOutputs.isPending}
              >
                <Trash2 className="h-4 w-4 mr-1" />
                Delete Selected ({selectedForDeletion.size})
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Output List */}
      <div className="grid gap-4">
        {data?.items?.length ? (
          data.items.map((output) => (
            <Card
              key={output.id}
              className={`cursor-pointer transition-all ${
                selectedOutputId === output.id ? "ring-2 ring-blue-500" : "hover:shadow-md"
              } ${selectedForDeletion.has(output.id) ? "ring-2 ring-red-400 dark:ring-red-600" : ""}`}
              onClick={() => setSelectedOutputId(output.id)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                  {/* Checkbox */}
                  <div className="pt-1" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedForDeletion.has(output.id)}
                      onChange={(e) => toggleSelection(output.id, e as any)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-red-600 focus:ring-2 focus:ring-red-500 cursor-pointer"
                    />
                  </div>
                  {/* Content */}
                  <div className="flex-1 flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-lg">
                        {truncate(output.event_title || "Untitled", 80)}
                      </CardTitle>
                      <div className="flex items-center gap-2 flex-wrap text-sm text-muted-foreground">
                        <Badge variant="secondary">{output.event_source}</Badge>
                        <Badge variant="outline">{output.event_type}</Badge>
                        {output.intent && (
                          <Badge
                            variant="outline"
                            className={getIntentColor(output.intent)}
                          >
                            {output.intent.replace(/_/g, " ")}
                          </Badge>
                        )}
                        {output.event_published_at && (
                          <span className="text-xs text-gray-600 dark:text-gray-400">
                            Published: {formatDate(output.event_published_at)}
                          </span>
                        )}
                        <span className="text-xs text-gray-400 dark:text-gray-500">
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
                        <Badge
                          variant={
                            output.evaluation_verdict === "PASS" ? "success" :
                            output.evaluation_verdict === "ACCEPT" ? "default" : "destructive"
                          }
                          className={output.evaluation_verdict === "ACCEPT" ? "bg-blue-600 text-white" : ""}
                        >
                          {output.evaluation_verdict}
                        </Badge>
                      ) : (
                        <Badge variant="secondary">Pending</Badge>
                      )}
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-sm line-clamp-3 ml-7">
                  <MarkdownContent content={truncate(output.llm_output, 300)} />
                </div>
                {output.clarity_issues?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1 ml-7">
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
            <CardContent className="py-8 text-center text-gray-500 dark:text-gray-400">
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
          <span className="text-sm text-gray-500 dark:text-gray-400">
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
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleDelete}
                    disabled={deleteOutput.isPending}
                    className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Delete
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setSelectedOutputId(null)}>
                    Close
                  </Button>
                </div>
              </div>
              <CardDescription>
                {selectedOutput.event_title}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Output Preview */}
              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <h4 className="font-medium mb-2 text-gray-900 dark:text-white">LLM Output:</h4>
                <MarkdownContent content={selectedOutput.llm_output} />
              </div>

              {/* Metadata */}
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">Type: {selectedOutput.event_type}</Badge>
                <Badge
                  variant="outline"
                  className={getIntentColor(selectedOutput.intent)}
                >
                  Intent: {selectedOutput.intent.replace(/_/g, " ")}
                </Badge>
                {selectedOutput.llm_model && (
                  <Badge
                    variant="secondary"
                    className="bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200"
                  >
                    Model: {selectedOutput.llm_model}
                  </Badge>
                )}
                {selectedOutput.event?.link && (
                  <a
                    href={selectedOutput.event.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Source
                  </a>
                )}
              </div>

              {/* Clarity Issues */}
              {selectedOutput.clarity_issues?.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2 text-yellow-600 dark:text-yellow-400">Clarity Issues:</h4>
                  <ul className="list-disc list-inside text-sm text-yellow-700 dark:text-yellow-300">
                    {selectedOutput.clarity_issues.map((issue, idx) => (
                      <li key={idx}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* AI Suggestion (show before human evaluates) */}
              {!selectedOutput.has_evaluation && selectedOutput.suggested_verdict && (
                <details className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                  <summary className="cursor-pointer font-medium text-blue-700 dark:text-blue-300 flex items-center gap-2">
                    <Bot className="h-4 w-4" />
                    AI Prediction (optional reference)
                  </summary>
                  <div className="mt-3 space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge variant={selectedOutput.suggested_verdict === "PASS" ? "success" : "destructive"}>
                        AI suggests: {selectedOutput.suggested_verdict}
                      </Badge>
                    </div>
                    {selectedOutput.suggested_verdict_reason && (
                      <p className="text-sm text-blue-700 dark:text-blue-300">
                        <strong>Reason:</strong> {selectedOutput.suggested_verdict_reason}
                      </p>
                    )}
                    <div className="flex items-start gap-2 pt-2 border-t border-blue-200 dark:border-blue-700">
                      <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-blue-600 dark:text-blue-400">
                        This is the AI's automated assessment. Use your own judgment when evaluating.
                      </p>
                    </div>
                  </div>
                </details>
              )}

              {/* Show Evaluation if Already Evaluated */}
              {selectedOutput.has_evaluation && selectedOutput.evaluation ? (
                <div className="pt-4 border-t">
                  <h4 className="font-medium mb-3">Evaluation Result:</h4>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      {selectedOutput.evaluation.verdict === "PASS" || selectedOutput.evaluation.verdict === "ACCEPT" ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-500" />
                      )}
                      <Badge variant={
                        selectedOutput.evaluation.verdict === "PASS" ? "success" :
                        selectedOutput.evaluation.verdict === "ACCEPT" ? "default" : "destructive"
                      } className={selectedOutput.evaluation.verdict === "ACCEPT" ? "bg-blue-600 text-white" : ""}>
                        {selectedOutput.evaluation.verdict}
                      </Badge>
                      {selectedOutput.evaluation.failure_reason && (
                        <Badge variant="outline">{selectedOutput.evaluation.failure_reason}</Badge>
                      )}
                      {/* Show corrected classification for ACCEPT/FAIL */}
                      {selectedOutput.evaluation.corrected_event_type && (
                        <Badge variant="outline" className="bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200">
                          Corrected: {selectedOutput.evaluation.corrected_event_type}
                        </Badge>
                      )}
                      {selectedOutput.evaluation.corrected_intent && (
                        <Badge variant="outline" className="bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200">
                          Intent: {selectedOutput.evaluation.corrected_intent}
                        </Badge>
                      )}
                      {/* Auto-Approved Badge */}
                      {selectedOutput.evaluation.auto_approved && (
                        <Badge variant="default" className="flex items-center gap-1 bg-blue-600 text-white">
                          <Bot className="h-3 w-3" />
                          Auto-Approved ({selectedOutput.evaluation.confidence_score?.toFixed(1)}%)
                        </Badge>
                      )}
                      {/* AI Agreement Badge */}
                      {selectedOutput.agreement_details && (
                        <Badge
                          variant={selectedOutput.agreement_details.agreed ? "success" : "warning"}
                          className="flex items-center gap-1"
                        >
                          {selectedOutput.agreement_details.agreed ? (
                            <>
                              <CheckCircle className="h-3 w-3" />
                              AI Agreed
                            </>
                          ) : (
                            <>
                              <AlertTriangle className="h-3 w-3" />
                              AI Disagreed
                            </>
                          )}
                        </Badge>
                      )}
                    </div>

                    {/* Auto-Approval Confidence Breakdown */}
                    {selectedOutput.evaluation.auto_approved && selectedOutput.evaluation.confidence_signals && (
                      <details className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                        <summary className="cursor-pointer font-medium text-blue-700 dark:text-blue-300 flex items-center gap-2 text-sm">
                          <Info className="h-4 w-4" />
                          View Confidence Breakdown
                        </summary>
                        <div className="mt-3 space-y-2 text-sm">
                          <div className="grid grid-cols-2 gap-2">
                            <div className="text-gray-700 dark:text-gray-300">
                              <strong>Clarity:</strong> {selectedOutput.evaluation.confidence_signals.clarity?.toFixed(1)}%
                            </div>
                            <div className="text-gray-700 dark:text-gray-300">
                              <strong>Similarity:</strong> {selectedOutput.evaluation.confidence_signals.similarity?.toFixed(1)}%
                            </div>
                            <div className="text-gray-700 dark:text-gray-300">
                              <strong>Event Type:</strong> {selectedOutput.evaluation.confidence_signals.event_type_rate?.toFixed(1)}%
                            </div>
                            <div className="text-gray-700 dark:text-gray-300">
                              <strong>Intent:</strong> {selectedOutput.evaluation.confidence_signals.intent_rate?.toFixed(1)}%
                            </div>
                            <div className="text-gray-700 dark:text-gray-300">
                              <strong>Source:</strong> {selectedOutput.evaluation.confidence_signals.source_reliability?.toFixed(1)}%
                            </div>
                            <div className="text-gray-700 dark:text-gray-300">
                              <strong>Similar PASS items:</strong> {selectedOutput.evaluation.similar_outputs_count || 0}
                            </div>
                          </div>
                          <div className="pt-2 border-t border-blue-200 dark:border-blue-700 text-xs text-blue-600 dark:text-blue-400">
                            Auto-approved based on ≥95% confidence and 10+ similar PASS outputs
                          </div>
                        </div>
                      </details>
                    )}
                    {/* Disagreement Details */}
                    {selectedOutput.agreement_details && !selectedOutput.agreement_details.agreed && (
                      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 mt-3">
                        <div className="text-sm text-yellow-800 dark:text-yellow-200 space-y-1">
                          <div>
                            <strong>AI suggested:</strong> {selectedOutput.agreement_details.ai_verdict}
                            {selectedOutput.agreement_details.ai_reason && (
                              <span className="text-xs ml-1">({selectedOutput.agreement_details.ai_reason})</span>
                            )}
                          </div>
                          <div>
                            <strong>You marked:</strong> {selectedOutput.agreement_details.human_verdict}
                            {selectedOutput.agreement_details.human_reason && (
                              <span className="text-xs ml-1">({selectedOutput.agreement_details.human_reason})</span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                    {selectedOutput.evaluation.comment && (
                      <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                        <p className="text-sm text-gray-700 dark:text-gray-300">{selectedOutput.evaluation.comment}</p>
                      </div>
                    )}
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                      Evaluated by {selectedOutput.evaluation.evaluator || "unknown"} on{" "}
                      {formatDate(selectedOutput.evaluation.evaluated_at)}
                    </p>
                  </div>

                  {/* Auto-generation status for PASS/ACCEPT */}
                  {(selectedOutput.evaluation.verdict === "PASS" || selectedOutput.evaluation.verdict === "ACCEPT") && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                      {/* Success Message */}
                      {twitterGenSuccess && (
                        <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                          <div className="flex items-center justify-between">
                            <p className="text-sm text-green-700 dark:text-green-300 flex items-center gap-2">
                              <CheckCircle className="h-4 w-4" />
                              X content generation started! Redirecting...
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Error Message */}
                      {twitterGenError && (
                        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                          <p className="text-sm text-red-700 dark:text-red-300 flex items-center gap-2">
                            <XCircle className="h-4 w-4" />
                            {twitterGenError}
                          </p>
                          <Button
                            onClick={() => handleGenerateTwitter()}
                            disabled={generatingTwitter || generateTwitterContent.isPending}
                            className="w-full mt-3"
                            variant="outline"
                          >
                            <XLogo className="h-4 w-4 mr-2" />
                            Retry Generation
                          </Button>
                        </div>
                      )}

                      {/* Loading state */}
                      {(generatingTwitter || generateTwitterContent.isPending) && !twitterGenSuccess && !twitterGenError && (
                        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                          <p className="text-sm text-blue-700 dark:text-blue-300 flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Generating X content automatically...
                          </p>
                        </div>
                      )}

                      {/* Info message for already evaluated items */}
                      {!twitterGenSuccess && !twitterGenError && !generatingTwitter && !generateTwitterContent.isPending && (
                        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                          <p className="text-sm text-blue-700 dark:text-blue-300 flex items-center gap-2">
                            <Info className="h-4 w-4" />
                            X content was automatically generated when this output was approved.
                          </p>
                          <Button
                            onClick={() => navigate("/generated-content")}
                            className="w-full mt-3"
                            variant="outline"
                          >
                            <XLogo className="h-4 w-4 mr-2" />
                            View Generated Content
                          </Button>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
                    To edit this evaluation, go to the Evaluations page.
                  </div>
                </div>
              ) : (
                /* Evaluation Form for Unevaluated Outputs */
                <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div>
                    <label className="block text-sm font-medium mb-1 text-gray-900 dark:text-white">
                      Comment (optional)
                    </label>
                    <textarea
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                      rows={2}
                      placeholder="Any additional notes..."
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                    />
                  </div>

                  {/* Type/Intent Dropdowns for Training Data Collection */}
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                    <h4 className="font-medium mb-3 text-yellow-800 dark:text-yellow-200">
                      Correct Classification (required for FAIL/ACCEPT)
                    </h4>

                    <div className="grid grid-cols-2 gap-4">
                      {/* Event Type Dropdown */}
                      <div>
                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">
                          Event Type
                        </label>
                        <select
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                          value={correctedEventType}
                          onChange={(e) => setCorrectedEventType(e.target.value)}
                        >
                          <option value="">Select type...</option>
                          <option value="DIGITAL_ASSETS">DIGITAL_ASSETS</option>
                          <option value="FINANCE_POLICY">FINANCE_POLICY</option>
                          <option value="GEO_FINANCIAL">GEO_FINANCIAL</option>
                          <option value="MACRO_ECONOMIC">MACRO_ECONOMIC</option>
                          <option value="MARKET_INFRASTRUCTURE">MARKET_INFRASTRUCTURE</option>
                          <option value="MARKET_MOVEMENT">MARKET_MOVEMENT</option>
                          <option value="NON_FINANCE">NON_FINANCE</option>
                          <option value="SKIP">SKIP</option>
                        </select>
                      </div>

                      {/* Intent Dropdown */}
                      <div>
                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">
                          Intent
                        </label>
                        <select
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                          value={correctedIntent}
                          onChange={(e) => setCorrectedIntent(e.target.value)}
                        >
                          <option value="">Select intent...</option>
                          <option value="EXPLANATORY">EXPLANATORY</option>
                          <option value="DESCRIPTIVE">DESCRIPTIVE</option>
                          <option value="MARKET_OPINION">MARKET_OPINION</option>
                          <option value="BREAKING_NEWS">BREAKING_NEWS</option>
                          <option value="DATA_RELEASE">DATA_RELEASE</option>
                        </select>
                      </div>
                    </div>

                    <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-2">
                      Select the correct type/intent if ML got it wrong. This data trains future models.
                    </p>
                  </div>

                  {/* Three Verdict Buttons */}
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
                      className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                      onClick={() => handleEvaluate("ACCEPT")}
                      disabled={createEvaluation.isPending || !correctedEventType || !correctedIntent}
                    >
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Accept
                    </Button>
                    <Button
                      variant="destructive"
                      className="flex-1"
                      onClick={() => handleEvaluate("FAIL")}
                      disabled={createEvaluation.isPending || !correctedEventType || !correctedIntent}
                    >
                      <XCircle className="h-4 w-4 mr-2" />
                      Fail
                    </Button>
                  </div>

                  {/* Verdict Explanation */}
                  <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
                    <p><strong>PASS:</strong> Content good, ML classification correct (no dropdowns needed)</p>
                    <p><strong>ACCEPT:</strong> Content good, but ML got type/intent wrong (goes to queue + training data)</p>
                    <p><strong>FAIL:</strong> Content rejected (training data only)</p>
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
