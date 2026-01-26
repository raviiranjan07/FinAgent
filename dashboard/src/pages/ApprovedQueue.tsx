import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { MarkdownContent } from "../components/MarkdownContent"
import { formatDate, truncate } from "../lib/utils"
import { useWebSocket } from "../hooks/useWebSocket"

interface ApprovedQueueItem {
  output_id: string
  event_id: string
  event_title: string
  event_source: string
  event_published_at: string
  event_type: string
  intent: string
  hitl_risk_level: string
  clarity_issues: string[]
  llm_output: string
  created_at: string
  approved_at: string | null
}

interface ApprovedQueueResponse {
  items: ApprovedQueueItem[]
  total: number
}

export default function ApprovedQueue() {
  const [data, setData] = useState<ApprovedQueueResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewFullId, setViewFullId] = useState<string | null>(null)
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set())
  const [sortBy, setSortBy] = useState<'date' | 'category'>('date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const navigate = useNavigate()

  // WebSocket connection for real-time updates
  const { isConnected, subscribe } = useWebSocket()

  // FIX: Use useCallback to prevent stale closures
  const fetchApprovedQueue = useCallback(async () => {
    try {
      setLoading(true)
      // FIX: Use relative URL to go through Vite proxy instead of hardcoded port
      const response = await fetch("/api/selection/approved-queue")
      if (!response.ok) throw new Error("Failed to fetch approved queue")
      const data: ApprovedQueueResponse = await response.json()
      setData(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, []) // No dependencies needed - fetch URL is static

  // Fetch approved queue on mount
  useEffect(() => {
    fetchApprovedQueue()
  }, [fetchApprovedQueue]) // FIX: Add fetchApprovedQueue to dependencies

  // Subscribe to WebSocket updates
  useEffect(() => {
    const unsubscribe = subscribe((message) => {
      // Refresh the queue when relevant events occur
      if (
        message.type === "NEW_EVALUATION" ||
        message.type === "APPROVED_QUEUE_UPDATE" ||
        message.type === "STATS_UPDATE"
      ) {
        console.log("[ApprovedQueue] WebSocket update received:", message.type)
        fetchApprovedQueue() // Now this uses the latest fetchApprovedQueue
      }
    })

    return unsubscribe
  }, [subscribe, fetchApprovedQueue]) // FIX: Add fetchApprovedQueue to dependencies

  // Selection handlers
  const handleToggleSelection = (outputId: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(outputId)) {
        newSet.delete(outputId)
      } else {
        newSet.add(outputId)
      }
      return newSet
    })
  }

  const handleSelectAll = () => {
    if (data) {
      setSelectedIds(new Set(data.items.map(item => item.output_id)))
    }
  }

  const handleDeselectAll = () => {
    setSelectedIds(new Set())
  }

  // Action handlers
  const handleBulkApproveForGeneration = async () => {
    if (selectedIds.size === 0) {
      alert("⚠️ No items selected")
      return
    }

    try {
      selectedIds.forEach(id => setProcessingIds(prev => new Set(prev).add(id)))

      const response = await fetch("/api/selection/approve-for-generation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ output_ids: Array.from(selectedIds) })
      })

      if (!response.ok) throw new Error("Failed to approve items for generation")

      // Clear selections and refresh
      setSelectedIds(new Set())
      await fetchApprovedQueue()

      // Navigate to Generated Content screen after 1 second
      setTimeout(() => {
        navigate("/generated-content")
      }, 1000)
    } catch (err) {
      alert(`❌ Error: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      selectedIds.forEach(id => {
        setProcessingIds(prev => {
          const newSet = new Set(prev)
          newSet.delete(id)
          return newSet
        })
      })
    }
  }

  const handleDeleteItem = async (outputId: string, eventTitle: string) => {
    if (!confirm(`Delete this item?\n\n"${eventTitle}"\n\nThis will permanently remove the output, evaluation, and any generated content.`)) {
      return
    }

    try {
      setProcessingIds(prev => new Set(prev).add(outputId))
      const response = await fetch(`/api/selection/delete-output/${outputId}`, {
        method: "DELETE"
      })

      if (!response.ok) throw new Error("Failed to delete item")

      const result = await response.json()
      alert(`✅ ${result.message}`)

      // Refresh the queue
      await fetchApprovedQueue()
    } catch (err) {
      alert(`❌ Error: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      setProcessingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(outputId)
        return newSet
      })
    }
  }

  // Sorting logic
  const sortedItems = data?.items ? [...data.items].sort((a, b) => {
    if (sortBy === 'date') {
      const dateA = new Date(a.approved_at || a.created_at).getTime()
      const dateB = new Date(b.approved_at || b.created_at).getTime()
      return sortOrder === 'asc' ? dateA - dateB : dateB - dateA
    } else {
      // Sort by category (event_type)
      const comparison = a.event_type.localeCompare(b.event_type)
      return sortOrder === 'asc' ? comparison : -comparison
    }
  }) : []

  if (loading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500 dark:text-gray-400">Loading approved queue...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-400">
          Error loading approved queue: {error}
        </div>
      </div>
    )
  }

  const viewedItem = sortedItems.find(item => item.output_id === viewFullId)

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Approved Queue</h1>
          {isConnected ? (
            <span className="flex items-center gap-1 text-xs font-semibold" style={{ color: '#16a34a' }}>
              <svg className="w-3 h-3" fill="#16a34a" viewBox="0 0 20 20">
                <circle cx="10" cy="10" r="8"/>
              </svg>
              Live
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <circle cx="10" cy="10" r="8"/>
              </svg>
              Offline
            </span>
          )}
        </div>
        <p className="text-gray-600 dark:text-gray-400">
          Content that passed evaluation and is ready for selection
        </p>

        {/* Bulk Selection Controls */}
        <div className="mt-4 space-y-3">
          {/* Selection Info and Actions */}
          <div className="flex items-center justify-between gap-4 p-4 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="flex items-center gap-4">
              <span className="text-sm font-semibold text-blue-900 dark:text-blue-100">
                {selectedIds.size} of {data?.total || 0} items selected
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSelectAll}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 font-medium"
                  disabled={!data || data.items.length === 0}
                >
                  Select All
                </button>
                <button
                  onClick={handleDeselectAll}
                  className="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 font-medium"
                  disabled={selectedIds.size === 0}
                >
                  Deselect All
                </button>
              </div>
            </div>
            <button
              onClick={handleBulkApproveForGeneration}
              disabled={selectedIds.size === 0}
              className="px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 dark:bg-green-600 dark:hover:bg-green-700 font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
            >
              🚀 Generate X Content ({selectedIds.size})
            </button>
          </div>

          {/* Sort Controls */}
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              <strong>{data?.total || 0}</strong> total items
            </span>
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600 dark:text-gray-400">Sort:</label>
              <select
                className="px-2 py-1 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded text-sm focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'date' | 'category')}
              >
                <option value="date">Date</option>
                <option value="category">Category</option>
              </select>
              <button
                onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
                className="px-2 py-1 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded text-sm hover:bg-gray-50 dark:hover:bg-gray-600"
              >
                {sortOrder === 'asc' ? '↑' : '↓'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Queue Items */}
      {sortedItems.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            No items in approved queue. Evaluate more content to add items here.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedItems.map((item) => {
            const isProcessing = processingIds.has(item.output_id)
            const isSelected = selectedIds.has(item.output_id)
            return (
              <div
                key={item.output_id}
                className={`bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition-all border-2 cursor-pointer ${
                  isSelected
                    ? 'border-blue-500 dark:border-blue-400 shadow-lg'
                    : 'border-gray-200 dark:border-gray-700'
                }`}
                onClick={() => handleToggleSelection(item.output_id)}
              >
                <div className="p-6">
                  {/* Header with Checkbox */}
                  <div className="flex items-start gap-4 mb-3">
                    {/* Checkbox */}
                    <div className="pt-1" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleToggleSelection(item.output_id)}
                        className="w-5 h-5 text-blue-600 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 dark:focus:ring-blue-400 focus:ring-2 cursor-pointer"
                        disabled={isProcessing}
                      />
                    </div>

                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                        {item.event_title}
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded">
                          {item.event_source}
                        </span>
                        <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
                          {item.event_type}
                        </span>
                        <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded">
                          {item.intent}
                        </span>
                        {item.hitl_risk_level && (
                          <span className={`px-2 py-0.5 rounded ${
                            item.hitl_risk_level === 'HIGH' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' :
                            item.hitl_risk_level === 'MEDIUM' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400' :
                            'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                          }`}>
                            {item.hitl_risk_level}
                          </span>
                        )}
                        <span className="text-xs">
                          Published: {formatDate(item.event_published_at)}
                        </span>
                        <span className="text-xs">
                          Approved: {formatDate(item.approved_at || item.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Preview */}
                  <div className="mb-3 line-clamp-3">
                    <MarkdownContent content={truncate(item.llm_output, 250)} />
                  </div>

                  {/* Clarity Issues */}
                  {item.clarity_issues && item.clarity_issues.length > 0 && (
                    <div className="mb-3 flex flex-wrap gap-1">
                      {item.clarity_issues.map((issue, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 text-xs rounded"
                        >
                          {issue}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-3" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => setViewFullId(item.output_id)}
                      className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 text-sm font-medium"
                      disabled={isProcessing}
                    >
                      View Full
                    </button>
                    <button
                      onClick={() => handleDeleteItem(item.output_id, item.event_title)}
                      disabled={isProcessing}
                      className="px-4 py-2 bg-red-600 dark:bg-red-700 text-white rounded hover:bg-red-700 dark:hover:bg-red-600 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isProcessing ? '⏳ Processing...' : 'Delete'}
                    </button>
                    {isSelected && (
                      <span className="ml-auto px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-sm font-semibold rounded">
                        ✓ Selected
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Full View Modal */}
      {viewedItem && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setViewFullId(null)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white pr-4">
                  {viewedItem.event_title}
                </h2>
                <button
                  onClick={() => setViewFullId(null)}
                  className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 text-2xl"
                >
                  ×
                </button>
              </div>

              <div className="flex flex-wrap items-center gap-2 mb-4 text-sm">
                <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded">
                  {viewedItem.event_source}
                </span>
                <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
                  {viewedItem.event_type}
                </span>
                <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded">
                  {viewedItem.intent}
                </span>
                <span className="text-xs text-gray-600 dark:text-gray-400">
                  Published: {formatDate(viewedItem.event_published_at)}
                </span>
              </div>

              {viewedItem.clarity_issues && viewedItem.clarity_issues.length > 0 && (
                <div className="mb-4">
                  <h3 className="font-medium text-yellow-700 dark:text-yellow-400 mb-2">Clarity Issues:</h3>
                  <ul className="list-disc list-inside text-sm text-yellow-600 dark:text-yellow-300 space-y-1">
                    {viewedItem.clarity_issues.map((issue, idx) => (
                      <li key={idx}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="prose dark:prose-invert max-w-none">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">AI-Generated Explanation:</h4>
                <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                  <MarkdownContent content={viewedItem.llm_output} />
                </div>
              </div>

              <div className="mt-6 space-y-3">
                {/* Selection Control */}
                <div className="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(viewedItem.output_id)}
                    onChange={() => handleToggleSelection(viewedItem.output_id)}
                    className="w-5 h-5 text-blue-600 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 dark:focus:ring-blue-400 focus:ring-2 cursor-pointer"
                  />
                  <label className="text-sm font-medium text-blue-900 dark:text-blue-100 cursor-pointer" onClick={() => handleToggleSelection(viewedItem.output_id)}>
                    {selectedIds.has(viewedItem.output_id) ? '✓ Selected for generation' : 'Select for generation'}
                  </label>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => {
                      handleDeleteItem(viewedItem.output_id, viewedItem.event_title)
                      setViewFullId(null)
                    }}
                    disabled={processingIds.has(viewedItem.output_id)}
                    className="px-6 py-2 bg-red-600 dark:bg-red-700 text-white rounded hover:bg-red-700 dark:hover:bg-red-600 font-medium disabled:opacity-50"
                  >
                    Delete
                  </button>
                  <button
                    onClick={() => setViewFullId(null)}
                    className="px-6 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 font-medium"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
