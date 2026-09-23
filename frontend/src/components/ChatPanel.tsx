import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { sendChat } from '../api'

interface Message {
  role: 'user' | 'agent'
  text: string
  toolsUsed?: string[]
  error?: boolean
}

const TOOL_LABELS: Record<string, string> = {
  search_courses: 'course catalog',
  web_search: 'web search',
}

const SUGGESTIONS = [
  'Which electives meet on Fridays?',
  'What does Managing Groups & Teams cover?',
  'Who teaches negotiation, and what is their background?',
]

export function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, pending])

  async function ask(question: string) {
    const text = question.trim()
    if (!text || pending) return

    setMessages((prev) => [...prev, { role: 'user', text }])
    setDraft('')
    setPending(true)

    try {
      const res = await sendChat(text)
      setMessages((prev) => [
        ...prev,
        { role: 'agent', text: res.reply, toolsUsed: res.tools_used },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'agent', text: (err as Error).message, error: true },
      ])
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="chat" aria-label="Course assistant">
      <header className="chat__head">
        <h2>Course assistant</h2>
        <p>Ask about courses, instructors, or meeting times.</p>
      </header>

      <div className="chat__log" ref={scrollRef}>
        {messages.length === 0 && !pending && (
          <div className="chat__empty">
            <p>Try one of these:</p>
            <ul>
              {SUGGESTIONS.map((s) => (
                <li key={s}>
                  <button type="button" className="chip" onClick={() => void ask(s)}>
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`bubble bubble--${msg.role}${msg.error ? ' bubble--error' : ''}`}
          >
            {msg.role === 'agent' ? (
              <div className="bubble__markdown">
                <Markdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // Wide tables get their own scroll area instead of
                    // squeezing course numbers into vertical slivers.
                    table: (props) => (
                      <div className="table-scroll">
                        <table {...props} />
                      </div>
                    ),
                    a: (props) => <a {...props} target="_blank" rel="noreferrer" />,
                  }}
                >
                  {msg.text}
                </Markdown>
              </div>
            ) : (
              msg.text
            )}

            {msg.toolsUsed && msg.toolsUsed.length > 0 && (
              <p className="bubble__tools">
                <span>Tools used:</span>
                {msg.toolsUsed.map((tool) => (
                  <code key={tool} title={tool}>
                    {TOOL_LABELS[tool] ?? tool}
                  </code>
                ))}
              </p>
            )}
          </div>
        ))}

        {pending && (
          <div className="bubble bubble--agent bubble--pending">
            <span className="spinner" aria-hidden="true" />
            <span>Checking the catalog…</span>
          </div>
        )}
      </div>

      <form
        className="chat__form"
        onSubmit={(e) => {
          e.preventDefault()
          void ask(draft)
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about a course, a professor, a time slot…"
          aria-label="Your question"
          disabled={pending}
        />
        <button type="submit" disabled={pending || !draft.trim()}>
          {pending ? 'Thinking…' : 'Ask'}
        </button>
      </form>
    </section>
  )
}
