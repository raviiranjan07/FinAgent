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
        <div className="text-gray-500 dark:text-gray-400">Loading dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500 dark:text-red-400">
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
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
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
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          FinAgent content evaluation overview
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-l-4 border-l-blue-500 bg-gradient-to-br from-blue-50 to-white dark:from-blue-950/20 dark:to-gray-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Outputs</CardTitle>
            <FileText className="h-5 w-5 text-blue-500 dark:text-blue-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
              {(evaluation?.total ?? 0) + (evaluation?.pending_count ?? 0)}
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              {evaluation?.pending_count ?? 0} pending evaluation
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-purple-500 bg-gradient-to-br from-purple-50 to-white dark:from-purple-950/20 dark:to-gray-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pass Rate</CardTitle>
            <TrendingUp className="h-5 w-5 text-purple-500 dark:text-purple-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-purple-600 dark:text-purple-400">{passRate.toFixed(1)}%</div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              Target: 85%+ for Pre-MVP exit
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-green-500 bg-gradient-to-br from-green-50 to-white dark:from-green-950/20 dark:to-gray-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Passed</CardTitle>
            <CheckCircle className="h-5 w-5 text-green-500 dark:text-green-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600 dark:text-green-400">
              {evaluation?.pass_count ?? 0}
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              Content approved for publishing
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500 bg-gradient-to-br from-red-50 to-white dark:from-red-950/20 dark:to-gray-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-5 w-5 text-red-500 dark:text-red-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600 dark:text-red-400">
              {evaluation?.fail_count ?? 0}
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              Needs improvement or review
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Progress Card */}
      <Card className="border-t-4 border-t-green-500 bg-gradient-to-br from-green-50/50 to-blue-50/50 dark:from-green-950/10 dark:to-blue-950/10">
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-green-600 dark:text-green-400" />
            <CardTitle className="text-xl">HITL Exit Progress</CardTitle>
          </div>
          <CardDescription>
            Track progress toward 90% pass rate target for Pre-MVP completion
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-base font-semibold text-gray-900 dark:text-white">Current Pass Rate</span>
              <Badge
                variant={passRate >= 85 ? "success" : passRate >= 70 ? "warning" : "destructive"}
                className="text-base px-3 py-1"
              >
                {passRate.toFixed(1)}%
              </Badge>
            </div>
            <div className="w-full bg-gray-300 dark:bg-gray-800 rounded-full h-6 border-2 border-gray-400 dark:border-white shadow-lg overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
                style={{
                  width: `${Math.min(passRate, 100)}%`,
                  background: passRate >= 85
                    ? 'linear-gradient(to right, #16a34a, #22c55e)'
                    : passRate >= 70
                    ? 'linear-gradient(to right, #ca8a04, #eab308)'
                    : 'linear-gradient(to right, #dc2626, #ef4444)'
                }}
              >
                {passRate > 10 && (
                  <span className="text-xs font-bold" style={{ color: '#ffffff' }}>{passRate.toFixed(1)}%</span>
                )}
              </div>
            </div>
            <div className="flex justify-between text-sm">
              <span className="font-medium text-gray-600 dark:text-gray-400">0%</span>
              <span className="text-green-600 dark:text-green-400 font-bold bg-green-100 dark:bg-green-900/30 px-2 py-0.5 rounded">
                🎯 Target: 90%
              </span>
              <span className="font-medium text-gray-600 dark:text-gray-400">100%</span>
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
                stats.event_types.map((et, idx) => {
                  const colors = [
                    { bg: "#dbeafe", bgDark: "#1e3a8a40", text: "#1d4ed8", textDark: "#93c5fd", bar: "#3b82f6" },
                    { bg: "#f3e8ff", bgDark: "#581c8740", text: "#7c3aed", textDark: "#d8b4fe", bar: "#a855f7" },
                    { bg: "#dcfce7", bgDark: "#14532d40", text: "#16a34a", textDark: "#86efac", bar: "#22c55e" },
                    { bg: "#ffedd5", bgDark: "#7c290040", text: "#ea580c", textDark: "#fdba74", bar: "#f97316" },
                    { bg: "#fce7f3", bgDark: "#831843", text: "#db2777", textDark: "#f9a8d4", bar: "#ec4899" },
                    { bg: "#cffafe", bgDark: "#164e6340", text: "#0891b2", textDark: "#67e8f9", bar: "#06b6d4" },
                  ]
                  const color = colors[idx % colors.length]
                  const isDark = document.documentElement.classList.contains('dark')
                  return (
                    <div key={et.event_type} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span
                          className="px-2 py-1 rounded text-xs font-semibold"
                          style={{
                            backgroundColor: isDark ? color.bgDark : color.bg,
                            color: isDark ? color.textDark : color.text
                          }}
                        >
                          {et.event_type}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-gray-900 dark:text-white">{et.count}</span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">({et.percentage}%)</span>
                        </div>
                      </div>
                      <div className="w-full bg-gray-300 dark:bg-gray-600 rounded-full h-2.5 border border-gray-400 dark:border-gray-500">
                        <div className="h-full rounded-full" style={{ width: `${et.percentage}%`, backgroundColor: color.bar }} />
                      </div>
                    </div>
                  )
                })
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">No data yet</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Failure Reasons */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500 dark:text-yellow-400" />
              Failure Reasons
            </CardTitle>
            <CardDescription>Common issues in failed content</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats?.failure_reasons?.length ? (
                stats.failure_reasons.map((fr) => (
                  <div key={fr.reason} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-900 dark:text-white">{fr.reason}</span>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 rounded text-xs font-bold">
                          {fr.count}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">({fr.percentage}%)</span>
                      </div>
                    </div>
                    <div className="w-full bg-gray-300 dark:bg-gray-600 rounded-full h-2.5 border border-gray-400 dark:border-gray-500">
                      <div className="h-full rounded-full" style={{ width: `${fr.percentage}%`, backgroundColor: '#ef4444' }} />
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-4">
                  <CheckCircle className="h-8 w-8 text-green-500 dark:text-green-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-green-600 dark:text-green-400">No failures recorded! 🎉</p>
                </div>
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
                  className="flex items-center justify-between p-3 bg-blue-100 dark:bg-gray-800 rounded-lg border-2 border-blue-400 dark:border-white/30 shadow-md"
                >
                  <span className="text-sm font-semibold text-gray-900 dark:text-white">{src.source}</span>
                  <Badge variant="default">{src.count}</Badge>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400 col-span-full">No sources yet</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
