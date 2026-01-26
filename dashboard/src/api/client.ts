import axios from "axios"

const API_BASE = "/api"

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
})

// Types
export interface Event {
  id: string
  event_id: string
  title: string
  summary: string | null
  link: string | null
  source: string
  published_at: string | null
  created_at: string
  has_output: boolean
  has_evaluation: boolean
}

export interface Output {
  id: string
  event_id: string
  llm_output: string
  event_type: string
  intent: string
  clarity_issues: string[]
  hitl_required: boolean
  hitl_risk_level: string | null
  llm_model: string | null
  created_at: string
  event_title: string | null
  event_source: string | null
  event_published_at: string | null
  has_evaluation: boolean
  evaluation_verdict: string | null
  // HITL AI suggestion fields
  suggested_verdict: string | null
  suggested_verdict_reason: string | null
  // Agreement field (computed: suggested == actual)
  ai_human_agreement: boolean | null
  event?: Event
  evaluation?: Evaluation
  // Agreement details (full comparison)
  agreement_details?: {
    agreed: boolean
    ai_verdict: string
    ai_reason: string | null
    human_verdict: string
    human_reason: string | null
  }
}

export interface Evaluation {
  id: string
  event_id: string
  output_id: string
  verdict: "PASS" | "FAIL"
  failure_reason: string | null
  comment: string | null
  evaluator: string | null
  evaluated_at: string
  // Auto-approval fields
  auto_approved?: boolean
  confidence_score?: number
  confidence_signals?: ConfidenceSignals
  similar_outputs_count?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DashboardStats {
  evaluation: {
    total: number
    pass_count: number
    fail_count: number
    pass_rate: number
    fail_rate: number
    pending_count: number
  }
  event_types: Array<{
    event_type: string
    count: number
    percentage: number
  }>
  sources: Array<{
    source: string
    count: number
    percentage: number
  }>
  failure_reasons: Array<{
    reason: string
    count: number
    percentage: number
  }>
  recent_activity: {
    daily_outputs: Record<string, number>
    total_last_7_days: number
  }
}

// HITL Agreement Metrics
export interface AgreementMetrics {
  total: number
  agreements: number
  disagreements: number
  agreement_rate: number
  false_positive_rate: number
  confusion_matrix: {
    PP?: number  // Predicted PASS, Actual PASS
    PF?: number  // Predicted PASS, Actual FAIL
    FP?: number  // Predicted FAIL, Actual PASS
    FF?: number  // Predicted FAIL, Actual FAIL
  }
}

export interface DisagreementExample {
  output_id: string
  event_type: string
  intent: string
  suggested_verdict: string
  actual_verdict: string
  suggested_reason: string | null
  actual_failure_reason: string | null
  llm_output_preview: string
  evaluated_at: string
}

export interface HITLMetrics {
  overall_metrics: AgreementMetrics
  recent_metrics: AgreementMetrics  // Last 30 evaluations
  target_rate: number  // 90.0
  status: "on_track" | "needs_improvement" | "achieved"
  progress_percentage: number
  remaining_to_target: number
  disagreement_examples: DisagreementExample[]
}

// Generated Content
export interface GeneratedContentItem {
  id: string
  output_id: string
  content_queue_id: string
  platform: string
  format: "SINGLE" | "THREAD"  // Tweet format
  content_text: string | null
  edited_content: string | null
  hashtags: string[]
  character_count: number
  edited_character_count: number
  is_edited: boolean
  is_published: boolean
  generated_at: string | null
  status: string
  error_message: string | null
  event_title: string | null
  event_source: string | null
}

export interface GeneratedContentResponse {
  items: GeneratedContentItem[]
  total: number
}

// Publishing Analytics
export interface DailyPublishingStat {
  date: string
  single_count: number
  thread_count: number
  total_count: number
}

export interface PublishingAnalytics {
  daily_stats: DailyPublishingStat[]
  total_published: number
  live_count: number
  dry_run_count: number
  by_format: {
    SINGLE?: number
    THREAD?: number
  }
  date_range: {
    start: string
    end: string
    days: number
  }
}

// API Functions
export const statsApi = {
  getDashboard: () => api.get<DashboardStats>("/stats/dashboard").then((r) => r.data),
  getSummary: () => api.get("/stats/summary").then((r) => r.data),
  getHitlProgress: () => api.get("/stats/hitl-progress").then((r) => r.data),
  getHitlMetrics: () => api.get<HITLMetrics>("/stats/hitl-metrics").then((r) => r.data),
  getPublishingAnalytics: (days: number = 30) =>
    api.get<PublishingAnalytics>("/stats/publishing-analytics", { params: { days } }).then((r) => r.data),
}

export const eventsApi = {
  list: (page = 1, pageSize = 20, source?: string, sortBy = "published_at", sortOrder = "desc") =>
    api
      .get<PaginatedResponse<Event>>("/events", {
        params: { page, page_size: pageSize, source, sort_by: sortBy, sort_order: sortOrder },
      })
      .then((r) => r.data),
  get: (eventId: string) => api.get<Event>(`/events/${eventId}`).then((r) => r.data),
  getSources: () => api.get("/events/sources/list").then((r) => r.data),
  regenerate: (eventId: string) => api.post(`/events/${eventId}/regenerate`).then((r) => r.data),
  delete: (eventId: string) => api.delete(`/events/${eventId}`).then((r) => r.data),
}

export const outputsApi = {
  list: (page = 1, pageSize = 20, options?: { event_type?: string; pending_only?: boolean; hitl_only?: boolean }) =>
    api
      .get<PaginatedResponse<Output>>("/outputs", {
        params: { page, page_size: pageSize, ...options },
      })
      .then((r) => r.data),
  get: (outputId: string) => api.get<Output>(`/outputs/${outputId}`).then((r) => r.data),
  getEventTypes: () => api.get("/outputs/event-types/list").then((r) => r.data),
}

export const evaluationsApi = {
  list: (page = 1, pageSize = 20, verdict?: string) =>
    api
      .get<PaginatedResponse<Evaluation>>("/evaluations", {
        params: { page, page_size: pageSize, verdict },
      })
      .then((r) => r.data),
  get: (evaluationId: string) => api.get<Evaluation>(`/evaluations/${evaluationId}`).then((r) => r.data),
  create: (data: { output_id: string; verdict: string; failure_reason?: string; comment?: string; evaluator?: string }) =>
    api.post<Evaluation>("/evaluations", data).then((r) => r.data),
  update: (evaluationId: string, data: { output_id: string; verdict: string; failure_reason?: string; comment?: string }) =>
    api.put<Evaluation>(`/evaluations/${evaluationId}`, data).then((r) => r.data),
  delete: (evaluationId: string) => api.delete(`/evaluations/${evaluationId}`).then((r) => r.data),
}

export interface ApprovedQueueItem {
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

export interface ApprovedQueueResponse {
  items: ApprovedQueueItem[]
  total: number
}

export const approvedQueueApi = {
  list: (limit = 50, offset = 0) =>
    api
      .get<ApprovedQueueResponse>("/selection/approved-queue", {
        params: { limit, offset },
      })
      .then((r) => r.data),
  approveForGeneration: (outputIds: string[]) =>
    api.post("/selection/approve-for-generation", { output_ids: outputIds }).then((r) => r.data),
}

export const contentApi = {
  getGenerated: (limit = 50, offset = 0) =>
    api
      .get<GeneratedContentResponse>("/content/generated", {
        params: { limit, offset },
      })
      .then((r) => r.data),
  editContent: (contentQueueId: string, editedContent: string) =>
    api
      .put(`/content/edit/${contentQueueId}`, { edited_content: editedContent })
      .then((r) => r.data),
  markAsPublished: (contentQueueId: string) =>
    api
      .put(`/content/publish/${contentQueueId}`)
      .then((r) => r.data),
  deleteGenerated: (generatedId: string) =>
    api
      .delete(`/content/delete-generated/${generatedId}`)
      .then((r) => r.data),
}

// Auto-Approval Types
export interface ConfidenceSignals {
  clarity: number
  similarity: number
  event_type_rate: number
  intent_rate: number
  source_reliability: number
}

export interface AutoApprovalDecision {
  output_id: string
  should_auto_approve: boolean
  confidence_score: number
  confidence_signals: ConfidenceSignals
  similar_pass_count: number
  reasons: string[]
}

export interface AutoApprovalMetrics {
  auto_approval_rate: number
  avg_confidence_score: number
  false_positive_rate: number
  total_auto_approved: number
  total_manual_review: number
  total_evaluated: number
  date_range: {
    start: string
    end: string
    days: number
  }
}

// Scheduling Types
export interface ScheduledItem {
  content_queue_id: string
  output_id: string
  event_title: string
  platform: string
  scheduled_for: string
  status: string
  retry_count: number
  publish_attempts: number
  last_publish_attempt: string | null
}

export interface WorkerHealth {
  is_alive: boolean
  last_heartbeat: string | null
  uptime_minutes: number | null
  success_rate: number | null
}

export interface ScheduleRequest {
  scheduled_for: string  // ISO datetime in IST
}

// Twitter Plugin Types
export interface ImpactFraming {
  primary_angle: string
  what_this_is_not: string
  why_it_matters: string
  reader_lens: string
  discussion_hook: string
  angle_priority?: number
  confidence?: number
}

export interface TwitterContentItem {
  id: string  // content_queue_id
  output_id: string
  event_title: string
  event_type: string
  event_url: string | null
  format: "SINGLE" | "THREAD"
  thread_length: number
  content_text: string  // For SINGLE: tweet text, For THREAD: JSON array
  tweets?: string[]  // Parsed from content_text if THREAD
  hashtags: string | null
  impact_framing: ImpactFraming | null
  status: "pending_generation" | "generating" | "pending_hitl" | "ready_to_schedule" | "scheduled" | "published" | "failed"
  edited_content: string | null
  is_edited: boolean
  twitter_post_id: string | null
  published_at: string | null
  scheduled_for?: string | null
  created_at: string
  updated_at: string
  // Retry tracking fields
  publish_attempts?: number
  retry_count?: number
  last_publish_attempt?: string | null
}

export interface TwitterContentListResponse {
  items: TwitterContentItem[]
  total: number
}

export interface GenerateTwitterContentRequest {
  output_id: string
}

export interface GenerateTwitterContentResponse {
  success: boolean
  status: string
  content_queue_id?: string
  format?: string
  error?: string
}

export interface PublishingSettings {
  enabled: boolean
  dry_run: boolean
  mode: "DISABLED" | "DRY_RUN" | "LIVE"
  description: string
}

// Twitter Plugin API
export const twitterApi = {
  // Get publishing settings
  getSettings: () =>
    api
      .get<PublishingSettings>("/twitter/settings")
      .then((r) => r.data),

  // Generate Twitter content for approved outputs
  generate: (outputId: string) =>
    api
      .post<GenerateTwitterContentResponse>("/twitter/generate", { output_id: outputId })
      .then((r) => r.data),

  // List Twitter content with filters
  list: (params?: { status?: string; format?: string; limit?: number; offset?: number }) =>
    api
      .get<TwitterContentListResponse>("/twitter/list", { params })
      .then((r) => r.data),

  // Edit Twitter content
  edit: (contentQueueId: string, editedContent: string) =>
    api
      .put(`/content/edit/${contentQueueId}`, { edited_content: editedContent })
      .then((r) => r.data),

  // Publish to X (posts to Twitter and marks as published)
  publish: (contentQueueId: string) =>
    api
      .post(`/twitter/publish/${contentQueueId}`)
      .then((r) => r.data),

  // Delete Twitter content
  delete: (contentQueueId: string) =>
    api
      .delete(`/twitter/${contentQueueId}`)
      .then((r) => r.data),

  // Approve HITL content (moves from pending_hitl to ready_to_schedule)
  approveHITL: (contentQueueId: string) =>
    api
      .post(`/twitter/approve-hitl/${contentQueueId}`)
      .then((r) => r.data),

  // Reject HITL content (moves from pending_hitl to failed)
  rejectHITL: (contentQueueId: string, reason?: string) => {
    return api
      .post(`/twitter/reject-hitl/${contentQueueId}`, { reason })
      .then((r) => r.data)
  },

  // Regenerate Twitter content (calls LLM again for a new version)
  regenerate: (contentQueueId: string) =>
    api
      .post(`/twitter/regenerate/${contentQueueId}`)
      .then((r) => r.data),
}

// Auto-Approval API
export const autoApprovalApi = {
  // Auto-evaluate specific output
  autoEvaluate: (outputId: string) =>
    api
      .post<AutoApprovalDecision>(`/auto-approval/auto-evaluate/${outputId}`)
      .then((r) => r.data),

  // Get auto-approval metrics
  getStats: (days: number = 7) =>
    api
      .get<AutoApprovalMetrics>("/auto-approval/stats", { params: { days } })
      .then((r) => r.data),

  // Batch auto-evaluate all pending outputs
  batchAutoEvaluate: (limit: number = 50) =>
    api
      .post("/auto-approval/batch-auto-evaluate", { limit })
      .then((r) => r.data),

  // Refresh confidence stats cache
  refreshCache: () =>
    api
      .post("/auto-approval/refresh-cache")
      .then((r) => r.data),

  // Get confidence breakdown for specific output
  getConfidenceBreakdown: (outputId: string) =>
    api
      .get<AutoApprovalDecision>(`/auto-approval/confidence-breakdown/${outputId}`)
      .then((r) => r.data),
}

// Scheduling API
export const schedulingApi = {
  // Smart schedule with automatic random timing
  scheduleSmart: (contentQueueIds: string[], daysAhead: number = 7) =>
    api
      .post("/scheduling/schedule-smart", {
        content_queue_ids: contentQueueIds,
        days_ahead: daysAhead,
      })
      .then((r) => r.data),

  // Schedule content for future publish (manual time selection)
  schedule: (contentQueueId: string, scheduledFor: string) =>
    api
      .post(`/scheduling/schedule/${contentQueueId}`, { scheduled_for: scheduledFor })
      .then((r) => r.data),

  // Reschedule content
  reschedule: (contentQueueId: string, scheduledFor: string) =>
    api
      .put(`/scheduling/reschedule/${contentQueueId}`, { scheduled_for: scheduledFor })
      .then((r) => r.data),

  // Cancel schedule
  unschedule: (contentQueueId: string) =>
    api
      .delete(`/scheduling/cancel/${contentQueueId}`)
      .then((r) => r.data),

  // Publish immediately (bypass schedule)
  publishNow: (contentQueueId: string) =>
    api
      .post(`/scheduling/publish-now/${contentQueueId}`)
      .then((r) => r.data),

  // Get all scheduled content
  getScheduled: () =>
    api
      .get<{ items: ScheduledItem[]; total: number }>("/scheduling/scheduled")
      .then((r) => r.data),

  // Check worker health
  getHealth: () =>
    api
      .get<WorkerHealth>("/scheduling/health")
      .then((r) => r.data),

  // Reset published content for republishing
  resetForRepublish: (contentQueueId: string) =>
    api
      .post(`/scheduling/reset-for-republish/${contentQueueId}`)
      .then((r) => r.data),
}

// System/Quota Management API (requires admin token)
export const quotaManagementApi = {
  // Reset quota tracking for specific API
  resetQuota: (api: string, adminToken: string) =>
    axios
      .post(
        `${API_BASE}/system/quota/reset/${api}`,
        {},
        {
          headers: { Authorization: `Bearer ${adminToken}` },
        }
      )
      .then((r) => r.data),

  // Health check specific API
  healthCheck: (api: string, adminToken: string) =>
    axios
      .post(
        `${API_BASE}/system/quota/health-check/${api}`,
        {},
        {
          headers: { Authorization: `Bearer ${adminToken}` },
        }
      )
      .then((r) => r.data),
}

