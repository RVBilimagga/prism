import { useState } from 'react'
import { MessagesSquare, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import type { Question } from '@/lib/api'
import { Pill } from '../pills'

interface Props {
  open: boolean; onOpenChange: (o: boolean) => void; questions: Question[]; stakeholder: string
  onSubmit: (answers: Record<string, string>) => void
}

// The stakeholder's follow-up questions. Answers are appended to the transcript and
// the whole analysis runs again (a new analysis; this one stays as it is).
export function QuestionsSheet({ open, onOpenChange, questions, stakeholder, onSubmit }: Props) {
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const answered = Object.values(answers).filter(a => a.trim()).length
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 p-0 sm:max-w-lg">
        <SheetHeader className="border-b px-6 py-5">
          <SheetTitle className="flex items-center gap-2 text-lg"><MessagesSquare className="size-5 text-primary" aria-hidden />Follow-up questions</SheetTitle>
          <SheetDescription>
            Ask the {stakeholder.toLowerCase()} these, then type the answers. They are added to the transcript and the analysis runs again.
            Leave a question blank to skip it.
          </SheetDescription>
        </SheetHeader>
        <ol className="grid flex-1 content-start gap-5 overflow-y-auto px-6 py-5">
          {questions.map((q, i) => (
            <li key={q.question} className="grid gap-2">
              <label htmlFor={`q-${i}`} className="grid gap-1.5">
                <Pill className="w-fit">{q.topic.replace(/_/g, ' ')}</Pill>
                <span className="font-medium">{q.question}</span>
                {q.reason && <span className="text-subtle-foreground">{q.reason}</span>}
              </label>
              <Textarea id={`q-${i}`} rows={2} value={answers[q.question] ?? ''} placeholder="Their answer"
                        onChange={e => setAnswers({ ...answers, [q.question]: e.target.value })} />
            </li>
          ))}
        </ol>
        <SheetFooter className="border-t px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <span className="text-subtle-foreground">{answered} of {questions.length} answered</span>
          <Button disabled={!answered} onClick={() => { onSubmit(answers); onOpenChange(false) }}>
            <RotateCcw aria-hidden />Re-run with {answered || ''} {answered === 1 ? 'answer' : 'answers'}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
