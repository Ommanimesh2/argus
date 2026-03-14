import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'ARGUS — Autonomous Security Auditor',
  description: 'AI-powered AWS infrastructure security auditing agent',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="min-h-screen antialiased" style={{ background: '#0a0a0f' }} suppressHydrationWarning>
        {children}
      </body>
    </html>
  )
}
