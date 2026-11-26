// Typed client for server.py. Shapes mirror the pydantic models in src/finreq.

export type Status = 'pending_review' | 'needs_clarification' | 'approved' | 'rejected' | 'needs_regeneration'
export type Risk = 'critical' | 'high' | 'medium' | 'low'
export type Decision = 'accept' | 'reject' | 'modify' | 'regenerate'
export type Backend = 'ollama' | 'gemini' | 'groq'

export interface Evidence { source_id: string; source_title: string; excerpt: string; similarity: number }
export interface Mapping {
  regulation_or_policy: string; jurisdiction: string; required_control: string
  gap: string | null; confidence: number; evidence: Evidence[]
}
export interface Issue { issue_type: string; detail: string; related_requirement_id: string | null }
export interface Requirement {
  id: string; statement: string; categories: string[]; source_stakeholder: string; source_excerpt: string
  business_justification: string; priority: string; acceptance_criteria: string[]
  applicable_regulations: string[]; risk_level: Risk; confidence_score: number; approval_status: Status
  quality_issues: Issue[]; compliance_mappings: Mapping[]; conflicts_with: string[]; duplicate_of: string | null
}
export interface RiskItem {
  id: string; related_requirement_id: string; category: string; description: string
  likelihood: 'low' | 'medium' | 'high'; impact: 'low' | 'medium' | 'high'; risk_level: Risk; mitigation: string
}
export interface Question { topic: string; question: string; reason: string }
export interface SDLCScore { key: string; name: string; score: number; supports: string[]; against: string[] }
export interface Phase { name: string; activities: string[]; roles: string[]; deliverables: string[]; exit_gate: string; repeats: boolean }
export interface SDLC {
  factors: Record<string, number>; labels: Record<string, string>; derived: string[]
  ranking: SDLCScore[]; recommended: string; chosen: string; workflow: Phase[]
  approvers: string[]; signed: string[]; baselined: boolean
}
export interface Analysis {
  id: string; status: 'running' | 'done' | 'failed'; stages: string[]; error: string | null; started: number; elapsed: number
  settings: { name: string; stakeholder_role: string; domain_tag: string; backend: Backend; model: string | null; ask_clarifying_questions: boolean }
  transcript?: string; requirements?: Requirement[]; risks?: RiskItem[]; questions?: Question[]; sdlc?: SDLC
}
export interface ProjectSummary {
  id: string; name: string; status: Analysis['status']; started: number
  requirements: number; decided: number
  sdlc: { name: string; signed: number; approvers: number; baselined: boolean } | null
}
export interface Config {
  backends: Record<Backend, string>; default_backend: Backend
  gemini_key_set: boolean; gemini_key_env: string; groq_key_set: boolean; groq_key_env: string
  reviewer_roles: string[]; stakeholder_roles: string[]; sample_transcript: string
}
export interface AuditEvent { id: string; agent: string; event_type: string; payload: string; timestamp: string }
export interface DecisionRecord { id: string; target_type: string; target_id: string; action: string; actor_role: string; note: string; timestamp: string }

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail
      : Array.isArray(body.detail) ? body.detail.map((d: { msg: string }) => d.msg).join('; ')
      : `The server answered ${res.status}.`
    throw new Error(detail)
  }
  return (res.status === 204 ? undefined : res.json()) as Promise<T>
}

const post = <T>(path: string, body: unknown) => call<T>(path, { method: 'POST', body: JSON.stringify(body) })

export const api = {
  config: () => call<Config>('/api/config'),
  projects: () => call<ProjectSummary[]>('/api/analyses'),
  start: (body: {
    transcript: string; name: string; stakeholder_role: string; domain_tag: string
    backend: string; model: string | null; ask_clarifying_questions: boolean
  }) => post<{ id: string }>('/api/analyses', body),
  get: (id: string) => call<Analysis>(`/api/analyses/${id}`),
  groqModels: () => call<{ id: string; name: string }[]>('/api/groq/models'),
  ollamaModels: () => call<{ id: string; name: string }[]>('/api/ollama/models'),
  // Removes the project only; its decisions and model calls stay in the audit trail.
  remove: (id: string) => call<void>(`/api/analyses/${id}`, { method: 'DELETE' }),
  decide: (id: string, reqId: string, body: { action: Decision; actor_role: string; note?: string; statement?: string }) =>
    post<Analysis>(`/api/analyses/${id}/requirements/${reqId}/decision`, body),
  bulkAccept: (id: string, actor_role: string) => post<Analysis>(`/api/analyses/${id}/bulk-accept`, { actor_role }),
  sdlc: (id: string, body: { factors?: Record<string, number>; chosen?: string }) =>
    call<Analysis>(`/api/analyses/${id}/sdlc`, { method: 'PUT', body: JSON.stringify(body) }),
  signoff: (id: string, actor_role: string) => post<Analysis>(`/api/analyses/${id}/sdlc/signoff`, { actor_role }),
  exportUrl: (id: string) => `/api/analyses/${id}/export`,
  // With an id: only that analysis's decisions and the model calls made during its run.
  audit: (analysisId?: string) => call<{ events: AuditEvent[]; decisions: DecisionRecord[] }>(
    analysisId ? `/api/audit?analysis=${encodeURIComponent(analysisId)}` : '/api/audit'),
}

export const roleLabel = (role: string) => {
  const s = role.replace(/_/g, ' ')
  return s.charAt(0).toUpperCase() + s.slice(1)
}
