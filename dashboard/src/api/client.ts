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
  created_at: string
  event_title: string | null
  event_source: string | null
  event_published_at: string | null
  has_evaluation: boolean
  evaluation_verdict: string | null
  event?: Event
  evaluation?: Evaluation
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

// API Functions
export const statsApi = {
  getDashboard: () => api.get<DashboardStats>("/stats/dashboard").then((r) => r.data),
  getSummary: () => api.get("/stats/summary").then((r) => r.data),
  getHitlProgress: () => api.get("/stats/hitl-progress").then((r) => r.data),
}

export const eventsApi = {
  list: (page = 1, pageSize = 20, source?: string) =>
    api
      .get<PaginatedResponse<Event>>("/events", {
        params: { page, page_size: pageSize, source },
      })
      .then((r) => r.data),
  get: (eventId: string) => api.get<Event>(`/events/${eventId}`).then((r) => r.data),
  getSources: () => api.get("/events/sources/list").then((r) => r.data),
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
