export interface Note {
  path: string
  title: string
  type: string
  body: string
  tags: string[]
  people: string[]
  folder: string
  created_at: string
  updated_at: string
}

export interface ActionItem {
  id: number
  note_path: string
  text: string
  done: boolean
  due_date: string | null
  assignee_path: string | null
}

export interface Attachment {
  id: number
  note_path: string
  filename: string
  file_path: string
  created_at: string
}

export interface CollapsePrefs {
  [key: string]: boolean
}

export interface PersonSummary {
  path: string
  title: string
  updated_at: string
  open_actions: number
}

export interface MeetingSummary {
  path: string
  title: string
  meeting_date: string
  participant_count: number
  open_actions: number
}

export interface ProjectSummary {
  path: string
  title: string
  updated_at: string
  open_actions: number
}

export interface BrainHealth {
  score: number
  total_notes: number
  orphan_count: number
  orphans: { path: string; title: string }[]
  empty_count: number
  empty_notes: { path: string; title: string }[]
  broken_link_count: number
  broken_links: { source: string; target: string }[]
  duplicate_count: number
  duplicate_candidates: { a: string; b: string; similarity: number }[]
}
