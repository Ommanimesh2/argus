'use client'
import { useEffect, useRef, useState } from 'react'
import { useAuditStore } from '@/store/audit-store'

export function CriticalFlash() {
  const findings = useAuditStore((s) => s.findings)
  const [flash, setFlash] = useState(false)
  const prevCriticals = useRef(0)

  useEffect(() => {
    const criticals = findings.filter((f) => f.severity === 'CRITICAL').length
    if (criticals > prevCriticals.current) {
      setFlash(true)
      setTimeout(() => setFlash(false), 300)
    }
    prevCriticals.current = criticals
  }, [findings])

  if (!flash) return null

  return (
    <div
      className="fixed inset-0 pointer-events-none z-[9998] transition-opacity"
      style={{ background: 'rgba(255,0,64,0.08)' }}
    />
  )
}
