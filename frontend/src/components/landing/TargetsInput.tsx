'use client'
import { useState, KeyboardEvent } from 'react'
import { X } from 'lucide-react'

interface TargetsInputProps {
  label: string
  placeholder: string
  values: string[]
  onChange: (values: string[]) => void
}

export function TargetsInput({ label, placeholder, values, onChange }: TargetsInputProps) {
  const [input, setInput] = useState('')

  const add = () => {
    const trimmed = input.trim()
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed])
    }
    setInput('')
  }

  const remove = (v: string) => onChange(values.filter((x) => x !== v))

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      add()
    }
    if (e.key === 'Backspace' && !input && values.length) {
      remove(values[values.length - 1])
    }
  }

  return (
    <div>
      <label className="block text-sm font-medium text-slate-400 mb-2 uppercase tracking-wider">
        {label}
      </label>
      <div
        className="min-h-[44px] flex flex-wrap gap-2 items-center p-2 rounded-lg border"
        style={{ background: '#111118', borderColor: '#2a2a3a' }}
      >
        {values.map((v) => (
          <span
            key={v}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-terminal"
            style={{
              background: 'rgba(0,212,255,0.1)',
              color: '#00d4ff',
              border: '1px solid rgba(0,212,255,0.3)',
            }}
          >
            {v}
            <button type="button" onClick={() => remove(v)} className="hover:opacity-70">
              <X size={10} />
            </button>
          </span>
        ))}
        <input
          className="flex-1 min-w-[120px] bg-transparent text-sm text-slate-300 outline-none placeholder:text-slate-600 font-terminal"
          placeholder={values.length === 0 ? placeholder : 'Add more...'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKey}
          onBlur={add}
        />
      </div>
      <p className="text-xs text-slate-600 mt-1">Press Enter or comma to add</p>
    </div>
  )
}
