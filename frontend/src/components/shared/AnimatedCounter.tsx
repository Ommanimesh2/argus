'use client'
import { useEffect, useRef, useState } from 'react'

export function AnimatedCounter({ value, className }: { value: number; className?: string }) {
  const [display, setDisplay] = useState(value)
  const prev = useRef(value)

  useEffect(() => {
    if (value === prev.current) return
    const diff = value - prev.current
    const steps = Math.min(Math.abs(diff), 20)
    let step = 0
    const interval = setInterval(() => {
      step++
      setDisplay(Math.round(prev.current + (diff * step) / steps))
      if (step >= steps) {
        clearInterval(interval)
        prev.current = value
      }
    }, 30)
    return () => clearInterval(interval)
  }, [value])

  return <span className={className}>{display}</span>
}
