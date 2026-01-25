import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { evaluationsApi, outputsApi } from "@/api/client"
import type { Evaluation, Output } from "@/api/client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { MarkdownContent } from "@/components/MarkdownContent"
import { formatDate } from "@/lib/utils"
import { ChevronLeft, ChevronRight, CheckCircle, XCircle, Edit, Trash2, Eye } from "lucide-react"

export function Evaluations() {
  const [page, setPage] = useState(1)
  const [verdictFilter, setVerdictFilter] = useState<string | undefined>(undefined)
  const [editingEval, setEditingEval] = useState<Evaluation | null>(null)
  const [viewingOutput, setViewingOutput] = useState<Output | null>(null)
  const [newVerdict, setNewVerdict] = useState<"PASS" | "FAIL">("PASS")
  const [newFailureReason, setNewFailureReason] = useState("")
  const [newComment, setNewComment] = useState("")

  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ["evaluations", page, verdictFilter],
    queryFn: () => evaluationsApi.list(page, 20, verdictFilter),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => evaluationsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evaluations"] })
      queryClient.invalidateQueries({ queryKey: ["outputs"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
      setEditingEval(null)
      setNewFailureReason("")
      setNewComment("")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: evaluationsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evaluations"] })
      queryClient.invalidateQueries({ queryKey: ["outputs"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
    },
  })

  const handleEdit = (evaluation: Evaluation) => {
    setEditingEval(evaluation)
    setNewVerdict(evaluation.verdict)
    setNewFailureReason(evaluation.failure_reason || "")
    setNewComment(evaluation.comment || "")
  }

  const handleUpdate = () => {
    if (!editingEval) return
    if (newVerdict === "FAIL" && !newFailureReason) {
      alert("Please provide a failure reason")
      return
    }

    updateMutation.mutate({
      id: editingEval.id,
      data: {
        output_id: editingEval.output_id,
        verdict: newVerdict,
        failure_reason: newVerdict === "FAIL" ? newFailureReason : undefined,
        comment: newComment || undefined,
      },
    })
  }

  const handleDelete = (evaluationId: string) => {
    if (confirm("Are you sure you want to delete this evaluation? This cannot be undone.")) {
      deleteMutation.mutate(evaluationId)
    }
  }

  const handleViewOutput = async (outputId: string) => {
    const output = await outputsApi.get(outputId)
    setViewingOutput(output)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 dark:text-gray-400">Loading evaluations...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500 dark:text-red-400">Failed to load evaluations</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Evaluations</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">History of content evaluations</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={!verdictFilter ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setVerdictFilter(undefined)
              setPage(1)
            }}
          >
            All
          </Button>
          <Button
            variant={verdictFilter === "PASS" ? "success" : "outline"}
            size="sm"
            onClick={() => {
              setVerdictFilter("PASS")
              setPage(1)
            }}
          >
            <CheckCircle className="h-4 w-4 mr-1" />
            Passed
          </Button>
          <Button
            variant={verdictFilter === "FAIL" ? "destructive" : "outline"}
            size="sm"
            onClick={() => {
              setVerdictFilter("FAIL")
              setPage(1)
            }}
          >
            <XCircle className="h-4 w-4 mr-1" />
            Failed
          </Button>
        </div>
      </div>

      {/* Evaluation List */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Evaluations</CardTitle>
          <CardDescription>
            {data?.total ?? 0} total evaluations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {data?.items?.length ? (
              data.items.map((evaluation) => (
                <div
                  key={evaluation.id}
                  className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center gap-2">
                      {evaluation.verdict === "PASS" ? (
                        <CheckCircle className="h-5 w-5 text-green-500 dark:text-green-400" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-500 dark:text-red-400" />
                      )}
                      <Badge variant={evaluation.verdict === "PASS" ? "success" : "destructive"}>
                        {evaluation.verdict}
                      </Badge>
                      {evaluation.failure_reason && (
                        <Badge variant="outline">{evaluation.failure_reason}</Badge>
                      )}
                    </div>
                    {evaluation.comment && (
                      <p className="text-sm text-gray-600 dark:text-gray-300">{evaluation.comment}</p>
                    )}
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                      Evaluated by {evaluation.evaluator || "unknown"} on{" "}
                      {formatDate(evaluation.evaluated_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-xs text-gray-400 dark:text-gray-500 mr-2">
                      Output: {evaluation.output_id.slice(0, 8)}...
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleViewOutput(evaluation.output_id)}
                      title="View output"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(evaluation)}
                      title="Edit evaluation"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(evaluation.id)}
                      title="Delete evaluation"
                      className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                No evaluations found
              </div>
            )}
          </div>
        </CardContent>
      </Card>

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

      {/* Edit Modal */}
      {editingEval && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-lg">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Edit Evaluation</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setEditingEval(null)}>
                  Close
                </Button>
              </div>
              <CardDescription>
                Update verdict or failure reason
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-900 dark:text-white">Verdict</label>
                <div className="flex gap-2">
                  <Button
                    variant={newVerdict === "PASS" ? "success" : "outline"}
                    onClick={() => setNewVerdict("PASS")}
                    className="flex-1"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    PASS
                  </Button>
                  <Button
                    variant={newVerdict === "FAIL" ? "destructive" : "outline"}
                    onClick={() => setNewVerdict("FAIL")}
                    className="flex-1"
                  >
                    <XCircle className="h-4 w-4 mr-2" />
                    FAIL
                  </Button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1 text-gray-900 dark:text-white">
                  Failure Reason {newVerdict === "FAIL" && <span className="text-red-500 dark:text-red-400">*</span>}
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                  value={newFailureReason}
                  onChange={(e) => setNewFailureReason(e.target.value)}
                  disabled={newVerdict === "PASS"}
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

              <div>
                <label className="block text-sm font-medium mb-1 text-gray-900 dark:text-white">
                  Comment (optional)
                </label>
                <textarea
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md text-sm focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                  rows={3}
                  placeholder="Any additional notes..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                />
              </div>

              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setEditingEval(null)}
                >
                  Cancel
                </Button>
                <Button
                  variant="default"
                  className="flex-1"
                  onClick={handleUpdate}
                  disabled={updateMutation.isPending}
                >
                  {updateMutation.isPending ? "Updating..." : "Update"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* View Output Modal */}
      {viewingOutput && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>View Output</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setViewingOutput(null)}>
                  Close
                </Button>
              </div>
              <CardDescription>
                {viewingOutput.event_title}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <h4 className="font-medium mb-2 text-gray-900 dark:text-white">LLM Output:</h4>
                <MarkdownContent content={viewingOutput.llm_output} />
              </div>

              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">Type: {viewingOutput.event_type}</Badge>
                <Badge variant="outline">Intent: {viewingOutput.intent}</Badge>
                <Badge variant="outline">Source: {viewingOutput.event_source}</Badge>
              </div>

              {viewingOutput.clarity_issues?.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2 text-yellow-600 dark:text-yellow-400">Clarity Issues:</h4>
                  <ul className="list-disc list-inside text-sm text-yellow-700 dark:text-yellow-300">
                    {viewingOutput.clarity_issues.map((issue, idx) => (
                      <li key={idx}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}

              {viewingOutput.evaluation && (
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <h4 className="font-medium mb-2 text-gray-900 dark:text-white">Current Evaluation:</h4>
                  <div className="flex items-center gap-2">
                    <Badge variant={viewingOutput.evaluation.verdict === "PASS" ? "success" : "destructive"}>
                      {viewingOutput.evaluation.verdict}
                    </Badge>
                    {viewingOutput.evaluation.failure_reason && (
                      <Badge variant="outline">{viewingOutput.evaluation.failure_reason}</Badge>
                    )}
                  </div>
                  {viewingOutput.evaluation.comment && (
                    <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">{viewingOutput.evaluation.comment}</p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
