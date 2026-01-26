import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { eventsApi, type Event } from "../api/client"
import { Card } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Badge } from "../components/ui/badge"

export function Events() {
  const [page, setPage] = useState(1)
  const [selectedSource, setSelectedSource] = useState<string | undefined>(undefined)
  const [sortBy, setSortBy] = useState("published_at")
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")
  const [selectedEventIds, setSelectedEventIds] = useState<Set<string>>(new Set())
  const queryClient = useQueryClient()

  const { data: eventsData, isLoading, error } = useQuery({
    queryKey: ["events", page, selectedSource, sortBy, sortOrder],
    queryFn: () => eventsApi.list(page, 20, selectedSource, sortBy, sortOrder),
  })

  const { data: sourcesData } = useQuery({
    queryKey: ["sources"],
    queryFn: () => eventsApi.getSources(),
  })

  const regenerateMutation = useMutation({
    mutationFn: (eventId: string) => eventsApi.regenerate(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] })
      queryClient.invalidateQueries({ queryKey: ["outputs"] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (eventId: string) => eventsApi.delete(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] })
      queryClient.invalidateQueries({ queryKey: ["outputs"] })
    },
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: async (eventIds: string[]) => {
      // Delete all events in parallel
      await Promise.all(eventIds.map(id => eventsApi.delete(id)))
    },
    onSuccess: () => {
      setSelectedEventIds(new Set())
      queryClient.invalidateQueries({ queryKey: ["events"] })
      queryClient.invalidateQueries({ queryKey: ["outputs"] })
    },
  })

  const handleDelete = (eventId: string, eventTitle: string) => {
    if (confirm(`Permanently delete "${eventTitle}"?\n\nThis will delete all outputs, evaluations, and generated content for this event. This cannot be undone.`)) {
      deleteMutation.mutate(eventId)
    }
  }

  const handleBulkDelete = () => {
    const count = selectedEventIds.size
    if (count === 0) return

    if (confirm(`Permanently delete ${count} selected event${count > 1 ? 's' : ''}?\n\nThis will delete all outputs, evaluations, and generated content for these events. This cannot be undone.`)) {
      bulkDeleteMutation.mutate(Array.from(selectedEventIds))
    }
  }

  const toggleEventSelection = (eventId: string) => {
    setSelectedEventIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(eventId)) {
        newSet.delete(eventId)
      } else {
        newSet.add(eventId)
      }
      return newSet
    })
  }

  const toggleSelectAll = () => {
    if (selectedEventIds.size === eventsData?.items?.length) {
      setSelectedEventIds(new Set())
    } else {
      setSelectedEventIds(new Set(eventsData?.items?.map((e: Event) => e.id) || []))
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "N/A"
    const formatted = new Date(dateString).toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      dateStyle: "medium",
      timeStyle: "short",
    })
    return `${formatted} IST`
  }

  if (isLoading) {
    return <div className="p-6">Loading events...</div>
  }

  if (error) {
    return <div className="p-6 text-red-600">Error loading events</div>
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-3xl font-bold">Events</h1>
          <Badge variant="outline">
            {eventsData?.total || 0} total events
          </Badge>
        </div>
        {selectedEventIds.size > 0 && (
          <Button
            variant="destructive"
            size="sm"
            onClick={handleBulkDelete}
            disabled={bulkDeleteMutation.isPending}
          >
            {bulkDeleteMutation.isPending
              ? `Deleting ${selectedEventIds.size}...`
              : `Delete Selected (${selectedEventIds.size})`
            }
          </Button>
        )}
      </div>

      {/* Filters and Sort */}
      <div className="space-y-4">
        {/* Select All */}
        {eventsData?.items && eventsData.items.length > 0 && (
          <div className="flex items-center gap-2 pb-2 border-b border-gray-200 dark:border-gray-700">
            <input
              type="checkbox"
              id="select-all"
              checked={selectedEventIds.size === eventsData.items.length && eventsData.items.length > 0}
              onChange={toggleSelectAll}
              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="select-all" className="text-sm text-muted-foreground cursor-pointer">
              Select All ({eventsData.items.length} on this page)
            </label>
          </div>
        )}

        {/* Source Filter */}
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={selectedSource === undefined ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedSource(undefined)}
          >
            All Sources
          </Button>
          {sourcesData?.sources && Object.entries(sourcesData.sources).map(([source, count]) => (
            <Button
              key={source}
              variant={selectedSource === source ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedSource(source)}
            >
              {source} ({count})
            </Button>
          ))}
        </div>

        {/* Sort Controls */}
        <div className="flex gap-2 items-center">
          <span className="text-sm text-muted-foreground">Sort by:</span>
          <Button
            variant={sortBy === "published_at" ? "default" : "outline"}
            size="sm"
            onClick={() => setSortBy("published_at")}
          >
            Published Date
          </Button>
          <Button
            variant={sortBy === "created_at" ? "default" : "outline"}
            size="sm"
            onClick={() => setSortBy("created_at")}
          >
            Created Date
          </Button>
          <span className="text-sm text-muted-foreground">Order:</span>
          <Button
            variant={sortOrder === "desc" ? "default" : "outline"}
            size="sm"
            onClick={() => setSortOrder("desc")}
          >
            Newest First
          </Button>
          <Button
            variant={sortOrder === "asc" ? "default" : "outline"}
            size="sm"
            onClick={() => setSortOrder("asc")}
          >
            Oldest First
          </Button>
        </div>
      </div>

      {/* Events List */}
      <div className="space-y-4">
        {eventsData?.items?.map((event: Event) => (
          <Card key={event.id} className="p-4">
            <div className="space-y-2">
              {/* Header */}
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1">
                  <input
                    type="checkbox"
                    checked={selectedEventIds.has(event.id)}
                    onChange={() => toggleEventSelection(event.id)}
                    className="w-4 h-4 mt-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div className="flex-1 space-y-1">
                    <h3 className="font-semibold text-lg">{event.title}</h3>
                    <div className="flex gap-2 text-sm text-muted-foreground">
                      <span>Source: {event.source}</span>
                      <span>•</span>
                      <span>Published: {formatDate(event.published_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Status Badges */}
                <div className="flex gap-2 items-center">
                  {event.has_output ? (
                    <Badge variant="default">Has Output</Badge>
                  ) : (
                    <Badge variant="secondary">No Output</Badge>
                  )}
                  {event.has_evaluation && (
                    <Badge variant="outline">Evaluated</Badge>
                  )}
                </div>
              </div>

              {/* Summary */}
              {event.summary && (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {event.summary}
                </p>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                {event.link && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => window.open(event.link!, "_blank")}
                  >
                    View Source
                  </Button>
                )}

                {!event.has_output && (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => regenerateMutation.mutate(event.id)}
                    disabled={regenerateMutation.isPending}
                  >
                    {regenerateMutation.isPending ? "Generating..." : "Generate Output"}
                  </Button>
                )}

                {event.has_output && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => window.location.href = `/outputs`}
                  >
                    View Output
                  </Button>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDelete(event.id, event.title)}
                  disabled={deleteMutation.isPending}
                  className="ml-auto text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  {deleteMutation.isPending ? "Deleting..." : "Delete"}
                </Button>
              </div>

              {/* Status Messages */}
              {regenerateMutation.isSuccess && regenerateMutation.variables === event.id && (
                <div className="mt-2 p-2 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded text-sm">
                  ✓ Output generated successfully! Check the Outputs page.
                </div>
              )}
              {regenerateMutation.isError && regenerateMutation.variables === event.id && (
                <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded text-sm">
                  ✗ Failed to generate output. Check console for details.
                </div>
              )}
              {deleteMutation.isSuccess && deleteMutation.variables === event.id && (
                <div className="mt-2 p-2 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded text-sm">
                  ✓ Event deleted successfully!
                </div>
              )}
              {deleteMutation.isError && deleteMutation.variables === event.id && (
                <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded text-sm">
                  ✗ Failed to delete event. Check console for details.
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* Pagination */}
      {eventsData && eventsData.total_pages > 1 && (
        <div className="flex justify-center gap-2 pt-4">
          <Button
            variant="outline"
            onClick={() => setPage(page - 1)}
            disabled={page === 1}
          >
            Previous
          </Button>
          <span className="flex items-center px-4">
            Page {page} of {eventsData.total_pages}
          </span>
          <Button
            variant="outline"
            onClick={() => setPage(page + 1)}
            disabled={page >= eventsData.total_pages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
