export interface PathActionItem {
  id: number;
  action_type: 'watch' | 'recheck' | 'expand' | 'alternatives' | 'archive' | 'resolve';
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface SavedPathListItem {
  id: string;
  summary_path: string[] | null;
  path_signature: string | null;
  status: 'watching' | 'active' | 'archived' | 'resolved';
  latest_headline: string;
  recheck_count: number;
  path_length: number;
  created_at: string;
  updated_at: string;
}

export interface SavedPathDetail {
  id: string;
  path_nodes: string[];
  summary_path: string[] | null;
  path_signature: string | null;
  edge_snapshot: EdgeSnapshot[] | null;
  why_now_snapshot: WhyNowSnapshot | null;
  source_center: string | null;
  source_slot: string | null;
  status: 'watching' | 'active' | 'archived' | 'resolved';
  recheck_count: number;
  created_at: string;
  updated_at: string;
  actions: PathActionItem[];
}

export interface EdgeSnapshot {
  from: string;
  to: string;
  type: string | null;
  truth_score: number | null;
  status: string;
}

export interface WhyNowSnapshot {
  headline: string;
  signals: Array<{ type: string; count?: number; delta?: number }>;
  generated_at: string;
  strong_edges: number;
  total_edges: number;
  suggested_action?: string;
}

export interface WatchPathInput {
  path_nodes: string[];
  source_center?: string;
  source_slot?: string;
}

export interface RecheckResponse {
  headline: string;
  strengthened: EdgeDiff[];
  weakened: EdgeDiff[];
  unchanged: EdgeDiff[];
  broken_edges: EdgeDiff[];
  path_intact: boolean;
  suggested_action: string;
  suggested_reason: string;
  updated_why_now: WhyNowSnapshot;
  status: string;
  recheck_count: number;
}

export interface EdgeDiff {
  from: string;
  to: string;
  type: string | null;
  old_status: string | null;
  new_status: string | null;
  old_score: number | null;
  new_score: number | null;
}

export interface ExpandResponse {
  source_ticker: string;
  candidates: ExpandCandidate[];
  total_found: number;
}

export interface ExpandCandidate {
  ticker: string;
  name: string;
  sector: string;
  relation_type: string | null;
  truth_score: number | null;
  relation_status: string | null;
  heat_score: number | null;
  basis_summary: string;
  why_summary: string;
}

export interface AlternativesResponse {
  target_ticker: string;
  neighbor_constraints: {
    before: { ticker: string; relation_type: string } | null;
    after: { ticker: string; relation_type: string } | null;
  };
  alternatives: AlternativeCandidate[];
  total_found: number;
}

export interface AlternativeCandidate {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  overlap_count: number;
  relation_before: { rel_type: string; truth_score: number | null; status: string | null } | null;
  relation_after: { rel_type: string; truth_score: number | null; status: string | null } | null;
  why_summary: string;
}
