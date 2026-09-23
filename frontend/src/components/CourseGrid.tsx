import type { Course } from '../api'
import { CourseCard } from './CourseCard'

interface Props {
  courses: Course[]
  loading: boolean
  error: string | null
}

export function CourseGrid({ courses, loading, error }: Props) {
  if (error) {
    return <p className="notice notice--error">{error}</p>
  }
  if (loading) {
    return (
      <div className="grid">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="course-card course-card--skeleton" />
        ))}
      </div>
    )
  }
  if (courses.length === 0) {
    return <p className="notice">No courses match that search.</p>
  }
  return (
    <div className="grid">
      {courses.map((course) => (
        <CourseCard
          key={`${course['Course ID']}-${course.Section}-${course['Course Session']}`}
          course={course}
        />
      ))}
    </div>
  )
}
