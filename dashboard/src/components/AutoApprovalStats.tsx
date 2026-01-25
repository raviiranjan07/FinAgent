import { useQuery } from "@tanstack/react-query"
import { autoApprovalApi } from "@/api/client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Bot, TrendingUp, AlertTriangle, CheckCircle, Loader2 } from "lucide-react"

interface AutoApprovalStatsProps {
  days?: number
}

export function AutoApprovalStats({ days = 7 }: AutoApprovalStatsProps) {
  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ["auto-approval-stats", days],
    queryFn: () => autoApprovalApi.getStats(days),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Auto-Approval System
          </CardTitle>
          <CardDescription>Last {days} days</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </CardContent>
      </Card>
    )
  }

  if (error || !metrics) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Auto-Approval System
          </CardTitle>
          <CardDescription>Last {days} days</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-red-500">Failed to load auto-approval metrics</div>
        </CardContent>
      </Card>
    )
  }

  const autoApprovalRate = metrics.auto_approval_rate ?? 0
  const falsePositiveRate = metrics.false_positive_rate ?? 0
  const avgConfidence = metrics.avg_confidence_score ?? 0

  // Status determination
  const isOnTrack = autoApprovalRate >= 70 && falsePositiveRate <= 5
  const needsImprovement = autoApprovalRate < 70 || falsePositiveRate > 5

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              Auto-Approval System
            </CardTitle>
            <CardDescription>Last {days} days</CardDescription>
          </div>
          <Badge variant={isOnTrack ? "success" : needsImprovement ? "warning" : "default"}>
            {isOnTrack ? "On Track" : needsImprovement ? "Needs Improvement" : "Active"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 gap-4">
          {/* Auto-Approval Rate */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-blue-700 dark:text-blue-300">Auto-Approval Rate</span>
              {autoApprovalRate >= 70 ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
              )}
            </div>
            <div className="text-3xl font-bold text-blue-900 dark:text-blue-100">
              {autoApprovalRate.toFixed(1)}%
            </div>
            <div className="text-xs text-blue-600 dark:text-blue-400 mt-1">
              Target: ~80% • {metrics.total_auto_approved ?? 0} auto-approved
            </div>
          </div>

          {/* Average Confidence */}
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-green-700 dark:text-green-300">Avg Confidence</span>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </div>
            <div className="text-3xl font-bold text-green-900 dark:text-green-100">
              {avgConfidence.toFixed(1)}%
            </div>
            <div className="text-xs text-green-600 dark:text-green-400 mt-1">
              Minimum threshold: 95%
            </div>
          </div>

          {/* False Positive Rate */}
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-yellow-700 dark:text-yellow-300">False Positive Rate</span>
              {falsePositiveRate <= 5 ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-red-600" />
              )}
            </div>
            <div className="text-3xl font-bold text-yellow-900 dark:text-yellow-100">
              {falsePositiveRate.toFixed(1)}%
            </div>
            <div className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
              Target: &lt;5%
            </div>
          </div>

          {/* Manual Review Required */}
          <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-purple-700 dark:text-purple-300">Manual Review</span>
            </div>
            <div className="text-3xl font-bold text-purple-900 dark:text-purple-100">
              {metrics.total_manual_review ?? 0}
            </div>
            <div className="text-xs text-purple-600 dark:text-purple-400 mt-1">
              Requires human evaluation
            </div>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {metrics.total_evaluated ?? 0}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">Total Evaluated</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">
                {metrics.total_auto_approved ?? 0}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">Auto-Approved</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-600">
                {metrics.total_manual_review ?? 0}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">Manual Review</div>
            </div>
          </div>
        </div>

        {/* Status Message */}
        {isOnTrack && (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
            <p className="text-sm text-green-700 dark:text-green-300 flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              Auto-approval system is performing well. Meets target rate and accuracy.
            </p>
          </div>
        )}

        {needsImprovement && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
            <p className="text-sm text-yellow-700 dark:text-yellow-300 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              {autoApprovalRate < 70
                ? "Auto-approval rate below target (70%). Consider adjusting confidence threshold."
                : "False positive rate above target (5%). Review auto-approval criteria."}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
