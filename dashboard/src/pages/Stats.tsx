import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { statsApi } from "@/api/client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, Target, AlertCircle, CheckCircle, Twitter, FileText } from "lucide-react"
import { AutoApprovalStats } from "@/components/AutoApprovalStats"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"

export function Stats() {
  const [publishingDays, setPublishingDays] = useState(7)

  const { data: hitlMetrics, isLoading: hitlLoading } = useQuery({
    queryKey: ["hitl-metrics"],
    queryFn: statsApi.getHitlMetrics,
  })

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: statsApi.getDashboard,
  })

  const { data: publishingAnalytics, isLoading: publishingLoading } = useQuery({
    queryKey: ["publishing-analytics", publishingDays],
    queryFn: () => statsApi.getPublishingAnalytics(publishingDays),
  })

  if (hitlLoading || statsLoading || publishingLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading statistics...</div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Statistics</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Detailed analytics and HITL progress</p>
      </div>

      {/* Publishing Analytics */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Twitter className="h-5 w-5" />
                Publishing Analytics
              </CardTitle>
              <CardDescription>Daily post publishing trends</CardDescription>
            </div>
            <select
              value={publishingDays}
              onChange={(e) => setPublishingDays(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={7}>Last 7 days</option>
              <option value={15}>Last 15 days</option>
              <option value={30}>Last 1 month</option>
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 rounded-lg border border-blue-200 dark:border-blue-700">
              <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
                {publishingAnalytics?.total_published || 0}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-300 mt-1">Total Published</div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                <span className="text-green-600">{publishingAnalytics?.live_count || 0} Live</span>
                {" · "}
                <span className="text-orange-500">{publishingAnalytics?.dry_run_count || 0} Dry Run</span>
              </div>
            </div>
            <div className="p-4 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 rounded-lg border border-green-200 dark:border-green-700">
              <div className="text-3xl font-bold text-green-600 dark:text-green-400">
                {publishingAnalytics?.by_format?.SINGLE || 0}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-300 mt-1 flex items-center gap-1">
                <FileText className="h-3 w-3" />
                Single Posts
              </div>
            </div>
            <div className="p-4 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 rounded-lg border border-purple-200 dark:border-purple-700">
              <div className="text-3xl font-bold text-purple-600 dark:text-purple-400">
                {publishingAnalytics?.by_format?.THREAD || 0}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-300 mt-1 flex items-center gap-1">
                <Twitter className="h-3 w-3" />
                Thread Posts
              </div>
            </div>
            <div className="p-4 bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/20 dark:to-orange-800/20 rounded-lg border border-orange-200 dark:border-orange-700">
              <div className="text-3xl font-bold text-orange-600 dark:text-orange-400">
                {publishingAnalytics?.dry_run_count || 0}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                Dry Run Tests
              </div>
            </div>
          </div>

          {/* Chart */}
          {publishingAnalytics?.daily_stats && publishingAnalytics.daily_stats.length > 0 ? (
            <div className="mt-6">
              <ResponsiveContainer width="100%" height={400}>
                <BarChart
                  data={publishingAnalytics.daily_stats}
                  margin={{ top: 5, right: 30, left: 20, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
                  <XAxis
                    dataKey="date"
                    className="text-xs"
                    tickFormatter={(value) => {
                      // Parse YYYY-MM-DD directly to avoid timezone issues
                      const parts = value.split("-")
                      return parseInt(parts[2], 10).toString() // Return day number
                    }}
                    label={{ value: "Days", position: "insideBottom", offset: -5 }}
                  />
                  <YAxis
                    className="text-xs"
                    label={{ value: "Number of Posts", angle: -90, position: "insideLeft" }}
                    allowDecimals={false}
                    domain={[0, (dataMax: number) => Math.max(1, dataMax)]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(255, 255, 255, 0.95)",
                      border: "1px solid #e5e7eb",
                      borderRadius: "8px",
                    }}
                    labelFormatter={(value) => {
                      // Parse YYYY-MM-DD directly to avoid timezone issues
                      const parts = value.split("-")
                      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                      const monthIndex = parseInt(parts[1], 10) - 1
                      const day = parseInt(parts[2], 10)
                      const year = parts[0]
                      return `${months[monthIndex]} ${day}, ${year} (IST)`
                    }}
                    formatter={(value: any, name: string) => {
                      const displayName = name === "Single Posts" ? "Single" : "Thread"
                      return [value, displayName]
                    }}
                  />
                  <Legend wrapperStyle={{ paddingTop: "20px" }} />
                  <Bar dataKey="single_count" stackId="a" fill="#10b981" name="Single Posts" />
                  <Bar dataKey="thread_count" stackId="a" fill="#8b5cf6" name="Thread Posts" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <Twitter className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No published content yet</p>
              <p className="text-sm mt-1">Start publishing posts to see analytics</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Auto-Approval System Stats */}
      <AutoApprovalStats days={7} />

      {/* HITL Agreement Metrics */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Target className="h-5 w-5" />
                HITL Exit Criteria - AI-Human Agreement
              </CardTitle>
              <CardDescription>
                Agreement rate between AI predictions and human evaluations
              </CardDescription>
            </div>
            <Badge
              variant={
                hitlMetrics?.status === "achieved"
                  ? "success"
                  : hitlMetrics?.status === "on_track"
                  ? "default"
                  : "warning"
              }
            >
              {hitlMetrics?.status === "achieved"
                ? "✓ Achieved"
                : hitlMetrics?.status === "on_track"
                ? "On Track"
                : "Needs Improvement"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Progress Bar */}
            <div className="space-y-4">
              <div className="flex justify-between text-sm">
                <span>
                  Current Agreement: {hitlMetrics?.overall_metrics.agreement_rate?.toFixed(1)}%
                </span>
                <span className="text-green-600">Target: {hitlMetrics?.target_rate}%</span>
              </div>
              <div className="relative h-6 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`absolute inset-y-0 left-0 ${
                    (hitlMetrics?.overall_metrics.agreement_rate || 0) >= 90
                      ? "bg-green-500"
                      : (hitlMetrics?.overall_metrics.agreement_rate || 0) >= 85
                      ? "bg-yellow-500"
                      : "bg-red-500"
                  } transition-all`}
                  style={{
                    width: `${Math.min(hitlMetrics?.overall_metrics.agreement_rate || 0, 100)}%`,
                  }}
                />
                <div className="absolute inset-y-0 border-r-2 border-green-700" style={{ left: "90%" }} />
              </div>
              <div className="flex justify-between text-xs text-gray-500">
                <span>0%</span>
                <span>50%</span>
                <span>90% (Target)</span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold">{hitlMetrics?.overall_metrics.total || 0}</div>
                <div className="text-sm text-gray-500">Total Compared</div>
              </div>
              <div className="p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {hitlMetrics?.overall_metrics.agreements || 0}
                </div>
                <div className="text-sm text-gray-500">Agreements</div>
              </div>
              <div className="p-4 bg-yellow-50 rounded-lg">
                <div className="text-2xl font-bold text-yellow-600">
                  {hitlMetrics?.overall_metrics.disagreements || 0}
                </div>
                <div className="text-sm text-gray-500">Disagreements</div>
              </div>
              <div className="p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {hitlMetrics?.remaining_to_target?.toFixed(1) || 0}%
                </div>
                <div className="text-sm text-gray-500">To Target</div>
              </div>
            </div>

            {/* Confusion Matrix & False Positive Rate */}
            <div className="grid gap-4 md:grid-cols-2">
              {/* Confusion Matrix */}
              <div>
                <h4 className="text-sm font-medium mb-3">Confusion Matrix</h4>
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-3 bg-green-100 border border-green-300 rounded text-center">
                    <div className="text-xs text-gray-600 mb-1">AI ✓ Human ✓</div>
                    <div className="text-lg font-bold text-green-700">
                      {hitlMetrics?.overall_metrics.confusion_matrix?.PP || 0}
                    </div>
                  </div>
                  <div className="p-3 bg-yellow-100 border border-yellow-300 rounded text-center">
                    <div className="text-xs text-gray-600 mb-1">AI ✓ Human ✗</div>
                    <div className="text-lg font-bold text-yellow-700">
                      {hitlMetrics?.overall_metrics.confusion_matrix?.PF || 0}
                    </div>
                  </div>
                  <div className="p-3 bg-orange-100 border border-orange-300 rounded text-center">
                    <div className="text-xs text-gray-600 mb-1">AI ✗ Human ✓</div>
                    <div className="text-lg font-bold text-orange-700">
                      {hitlMetrics?.overall_metrics.confusion_matrix?.FP || 0}
                    </div>
                  </div>
                  <div className="p-3 bg-blue-100 border border-blue-300 rounded text-center">
                    <div className="text-xs text-gray-600 mb-1">AI ✗ Human ✗</div>
                    <div className="text-lg font-bold text-blue-700">
                      {hitlMetrics?.overall_metrics.confusion_matrix?.FF || 0}
                    </div>
                  </div>
                </div>
              </div>

              {/* Recent Trend & False Positive Rate */}
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium mb-2">False Positive Rate</h4>
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <div className="text-3xl font-bold text-red-600">
                      {hitlMetrics?.overall_metrics.false_positive_rate?.toFixed(1) || 0}%
                    </div>
                    <div className="text-xs text-gray-600 mt-1">
                      AI says PASS but human marks FAIL
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-2">Recent Trend (Last 30)</h4>
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="text-3xl font-bold text-blue-600">
                      {hitlMetrics?.recent_metrics.agreement_rate?.toFixed(1) || 0}%
                    </div>
                    <div className="text-xs text-gray-600 mt-1">
                      {hitlMetrics?.recent_metrics.agreements || 0} / {hitlMetrics?.recent_metrics.total || 0}{" "}
                      agreements
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Disagreement Examples */}
            {hitlMetrics?.disagreement_examples && hitlMetrics.disagreement_examples.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-3">Recent Disagreement Examples</h4>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {hitlMetrics.disagreement_examples.slice(0, 5).map((example) => (
                    <div
                      key={example.output_id}
                      className="p-3 bg-yellow-50 border border-yellow-200 rounded text-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="font-medium text-gray-900 mb-1">
                            {example.event_type} - {example.intent}
                          </div>
                          <div className="text-xs text-gray-600 mb-2">{example.llm_output_preview}</div>
                          <div className="flex gap-4 text-xs">
                            <span className="text-blue-600">
                              <strong>AI:</strong> {example.suggested_verdict}
                              {example.suggested_reason && ` (${example.suggested_reason})`}
                            </span>
                            <span className="text-purple-600">
                              <strong>Human:</strong> {example.actual_verdict}
                              {example.actual_failure_reason && ` (${example.actual_failure_reason})`}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Detailed Stats */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Event Types Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>Event Type Distribution</CardTitle>
            <CardDescription>Breakdown by content classification</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats?.event_types?.map((et) => (
                <div key={et.event_type} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">{et.event_type}</span>
                    <span className="text-gray-500">
                      {et.count} ({et.percentage}%)
                    </span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500"
                      style={{ width: `${et.percentage}%` }}
                    />
                  </div>
                </div>
              )) || <p className="text-gray-500">No data</p>}
            </div>
          </CardContent>
        </Card>

        {/* Failure Analysis */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-500" />
              Failure Analysis
            </CardTitle>
            <CardDescription>Common reasons for content failures</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats?.failure_reasons?.length ? (
                stats.failure_reasons.map((fr) => (
                  <div key={fr.reason} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">{fr.reason}</span>
                      <span className="text-gray-500">
                        {fr.count} ({fr.percentage}%)
                      </span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-red-500"
                        style={{ width: `${fr.percentage}%` }}
                      />
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-4 text-gray-500">
                  <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                  <p>No failures recorded yet!</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Source Stats */}
      <Card>
        <CardHeader>
          <CardTitle>Source Distribution</CardTitle>
          <CardDescription>Events processed by RSS source</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {stats?.sources?.map((src) => (
              <div
                key={src.source}
                className="p-4 border rounded-lg flex justify-between items-center"
              >
                <span className="font-medium">{src.source}</span>
                <div className="text-right">
                  <div className="font-bold">{src.count}</div>
                  <div className="text-xs text-gray-500">{src.percentage}%</div>
                </div>
              </div>
            )) || <p className="text-gray-500">No sources</p>}
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Recent Activity
          </CardTitle>
          <CardDescription>Last 7 days processing summary</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4">
            <div className="text-4xl font-bold text-blue-600">
              {stats?.recent_activity?.total_last_7_days || 0}
            </div>
            <div className="text-gray-500">outputs processed in last 7 days</div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
