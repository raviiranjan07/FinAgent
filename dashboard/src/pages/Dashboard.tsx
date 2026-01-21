import { useEffect } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { statsApi } from "@/api/client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useWebSocket } from "@/hooks/useWebSocket"
import {
  FileText,
  CheckCircle,
  XCircle,
  TrendingUp,
  AlertTriangle,
  Wifi,
  WifiOff,
} from "lucide-react"

export function Dashboard() {
  const queryClient = useQueryClient()
  const { subscribe, isConnected } = useWebSocket()

  // Listen for WebSocket events to auto-refresh stats
  useEffect(() => {
    const unsubscribe = subscribe((message) => {
      if (message.type === "NEW_EVALUATION" || message.type === "NEW_OUTPUT" || message.type === "STATS_UPDATE") {
        queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
      }
    })
    return unsubscribe
  }, [subscribe, queryClient])

  const { data: stats, isLoading, error } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: statsApi.getDashboard,
    refetchInterval: 30000, // Fallback: refresh every 30 seconds
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">
          Failed to load dashboard. Is the API running?
        </div>
      </div>
    )
  }

  const evaluation = stats?.evaluation
  const passRate = evaluation?.pass_rate ?? 0

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
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
        <p className="text-gray-500 mt-1">
          FinAgent content evaluation overview
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Outputs</CardTitle>
            <FileText className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(evaluation?.total ?? 0) + (evaluation?.pending_count ?? 0)}
            </div>
            <p className="text-xs text-gray-500">
              {evaluation?.pending_count ?? 0} pending evaluation
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{passRate.toFixed(1)}%</div>
            <p className="text-xs text-gray-500">
              Target: 85%+ for Pre-MVP exit
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Passed</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {evaluation?.pass_count ?? 0}
            </div>
            <p className="text-xs text-gray-500">
              Content approved for publishing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {evaluation?.fail_count ?? 0}
            </div>
            <p className="text-xs text-gray-500">
              Needs improvement or review
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Progress Card */}
      <Card>
        <CardHeader>
          <CardTitle>HITL Exit Progress</CardTitle>
          <CardDescription>
            Track progress toward 90% pass rate target for Pre-MVP completion
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Current Pass Rate</span>
              <Badge variant={passRate >= 85 ? "success" : passRate >= 70 ? "warning" : "destructive"}>
                {passRate.toFixed(1)}%
              </Badge>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all ${
                  passRate >= 85 ? "bg-green-500" : passRate >= 70 ? "bg-yellow-500" : "bg-red-500"
                }`}
                style={{ width: `${Math.min(passRate, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-gray-500">
              <span>0%</span>
              <span className="text-green-600 font-medium">Target: 90%</span>
              <span>100%</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Two Column Layout */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Event Types */}
        <Card>
          <CardHeader>
            <CardTitle>Event Types</CardTitle>
            <CardDescription>Distribution of processed content</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats?.event_types?.length ? (
                stats.event_types.map((et) => (
                  <div key={et.event_type} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">{et.event_type}</Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-500">{et.count}</span>
                      <span className="text-xs text-gray-400">({et.percentage}%)</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">No data yet</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Failure Reasons */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Failure Reasons
            </CardTitle>
            <CardDescription>Common issues in failed content</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats?.failure_reasons?.length ? (
                stats.failure_reasons.map((fr) => (
                  <div key={fr.reason} className="flex items-center justify-between">
                    <span className="text-sm">{fr.reason}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="destructive">{fr.count}</Badge>
                      <span className="text-xs text-gray-400">({fr.percentage}%)</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">No failures recorded</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Sources */}
      <Card>
        <CardHeader>
          <CardTitle>RSS Sources</CardTitle>
          <CardDescription>Events fetched by source</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-4">
            {stats?.sources?.length ? (
              stats.sources.map((src) => (
                <div
                  key={src.source}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <span className="text-sm font-medium">{src.source}</span>
                  <Badge variant="outline">{src.count}</Badge>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500 col-span-full">No sources yet</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
