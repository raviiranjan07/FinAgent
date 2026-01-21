import { useQuery } from "@tanstack/react-query"
import { statsApi } from "@/api/client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, Target, AlertCircle, CheckCircle } from "lucide-react"

export function Stats() {
  const { data: hitlProgress, isLoading: hitlLoading } = useQuery({
    queryKey: ["hitl-progress"],
    queryFn: statsApi.getHitlProgress,
  })

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: statsApi.getDashboard,
  })

  if (hitlLoading || statsLoading) {
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
        <h1 className="text-3xl font-bold text-gray-900">Statistics</h1>
        <p className="text-gray-500 mt-1">Detailed analytics and HITL progress</p>
      </div>

      {/* HITL Progress */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Target className="h-5 w-5" />
                HITL Exit Criteria
              </CardTitle>
              <CardDescription>
                Progress toward Pre-MVP completion
              </CardDescription>
            </div>
            <Badge
              variant={hitlProgress?.status === "on_track" ? "success" : "warning"}
            >
              {hitlProgress?.status === "on_track" ? "On Track" : "Needs Improvement"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            {/* Progress Bar */}
            <div className="space-y-4">
              <div className="flex justify-between text-sm">
                <span>Current: {hitlProgress?.pass_rate?.toFixed(1)}%</span>
                <span className="text-green-600">Target: {hitlProgress?.target_rate}%</span>
              </div>
              <div className="relative h-6 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`absolute inset-y-0 left-0 ${
                    hitlProgress?.pass_rate >= 85
                      ? "bg-green-500"
                      : hitlProgress?.pass_rate >= 70
                      ? "bg-yellow-500"
                      : "bg-red-500"
                  } transition-all`}
                  style={{ width: `${Math.min(hitlProgress?.pass_rate || 0, 100)}%` }}
                />
                <div
                  className="absolute inset-y-0 border-r-2 border-green-700"
                  style={{ left: "90%" }}
                />
              </div>
              <div className="flex justify-between text-xs text-gray-500">
                <span>0%</span>
                <span>50%</span>
                <span>90% (Target)</span>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold">{hitlProgress?.total_evaluated || 0}</div>
                <div className="text-sm text-gray-500">Total Evaluated</div>
              </div>
              <div className="p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {hitlProgress?.pass_count || 0}
                </div>
                <div className="text-sm text-gray-500">Passed</div>
              </div>
              <div className="p-4 bg-red-50 rounded-lg">
                <div className="text-2xl font-bold text-red-600">
                  {hitlProgress?.fail_count || 0}
                </div>
                <div className="text-sm text-gray-500">Failed</div>
              </div>
              <div className="p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {hitlProgress?.remaining_to_target?.toFixed(1) || 0}%
                </div>
                <div className="text-sm text-gray-500">To Target</div>
              </div>
            </div>
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
