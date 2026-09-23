/** Thin client for the FastAPI course desk running on :8000. */

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://127.0.0.1:8000'

/** One row of data/yale_som_classes.json, as served by /api/courses. */
export interface Course {
  'Course ID': string
  'Course Number': string
  'Course Title': string
  'Course Category': string
  'Course Type': string
  'Course Description': string
  'Course Session': string
  'Course Session Start date': string
  'Course Session End Date': string
  Daytimes: string
  'Timings Day': string
  'Timings StartTime': string
  'Timings EndTime': string
  'Faculty 1': string
  'Faculty 1 Email': string
  faculty_bio: string
  Room: string
  Section: string
  Units: string
  Syllabus: string
  'Old Syllabus': string
  'Bid Or Permission': string
  TermCode: string
  Visible: string
}

export interface CoursesResponse {
  count: number
  courses: Course[]
}

export interface ChatResponse {
  reply: string
  tools_used: string[]
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} — is the backend running on :8000?`)
  }
  return (await res.json()) as T
}

export function fetchCourses(query?: string, signal?: AbortSignal): Promise<CoursesResponse> {
  const suffix = query?.trim() ? `?q=${encodeURIComponent(query.trim())}` : ''
  return getJson<CoursesResponse>(`/api/courses${suffix}`, { signal })
}

export function sendChat(message: string, signal?: AbortSignal): Promise<ChatResponse> {
  return getJson<ChatResponse>('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
    signal,
  })
}
