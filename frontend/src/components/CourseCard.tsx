import { useState } from 'react'

import type { Course } from '../api'

const DAY_LABELS: Record<string, string> = {
  Mo: 'Mon',
  Tu: 'Tue',
  We: 'Wed',
  Th: 'Thu',
  Fr: 'Fri',
  Sa: 'Sat',
  Su: 'Sun',
}

function formatDays(course: Course): string {
  const codes = (course['Timings Day'] ?? '').split(',').filter(Boolean)
  if (codes.length === 0) return ''
  return codes.map((code) => DAY_LABELS[code.trim()] ?? code.trim()).join(' · ')
}

function formatTime(course: Course): string {
  const start = course['Timings StartTime']?.trim()
  const end = course['Timings EndTime']?.trim()
  if (!start || !end) return ''
  return `${start} – ${end}`
}

/** "fall-1" -> "Fall 1" */
function formatSession(session: string): string {
  if (!session) return ''
  return session
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function CourseCard({ course }: { course: Course }) {
  const [expanded, setExpanded] = useState(false)

  const days = formatDays(course)
  const time = formatTime(course)
  const room = course.Room?.trim()
  const faculty = course['Faculty 1']?.trim()
  const email = course['Faculty 1 Email']?.trim()
  const description = course['Course Description']?.trim()
  const category = course['Course Category']?.trim()
  const units = course.Units?.trim()
  const syllabus = course.Syllabus?.trim() || course['Old Syllabus']?.trim()

  const isLong = description.length > 260
  const shown = expanded || !isLong ? description : `${description.slice(0, 260).trimEnd()}…`

  return (
    <article className="course-card">
      <header className="course-card__head">
        <span className="course-card__number">{course['Course Number']}</span>
        {category && <span className={`pill pill--${category.toLowerCase()}`}>{category}</span>}
      </header>

      <h3 className="course-card__title">{course['Course Title']}</h3>

      {faculty && (
        <p className="course-card__faculty">
          {email ? <a href={`mailto:${email}`}>{faculty}</a> : faculty}
        </p>
      )}

      <dl className="course-card__meta">
        {days && (
          <div>
            <dt>Days</dt>
            <dd>{days}</dd>
          </div>
        )}
        {time && (
          <div>
            <dt>Time</dt>
            <dd>{time}</dd>
          </div>
        )}
        {room && (
          <div>
            <dt>Room</dt>
            <dd>{room}</dd>
          </div>
        )}
        {course['Course Session'] && (
          <div>
            <dt>Session</dt>
            <dd>{formatSession(course['Course Session'])}</dd>
          </div>
        )}
        {units && (
          <div>
            <dt>Units</dt>
            <dd>{units}</dd>
          </div>
        )}
      </dl>

      {description && (
        <p className="course-card__desc">
          {shown}{' '}
          {isLong && (
            <button
              type="button"
              className="linkish"
              onClick={() => setExpanded((prev) => !prev)}
            >
              {expanded ? 'Show less' : 'Read more'}
            </button>
          )}
        </p>
      )}

      {syllabus && (
        <a className="course-card__syllabus" href={syllabus} target="_blank" rel="noreferrer">
          Syllabus ↗
        </a>
      )}
    </article>
  )
}
