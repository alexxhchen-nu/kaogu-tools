'use client'

import { useEffect, useState } from 'react'
import { resolveEndpoint } from '@/lib/api-client'
import { cn } from '@/lib/utils'

export function BackendStatus() {
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading')

  useEffect(() => {
    let active = true
    fetch(resolveEndpoint('/health'))
      .then((res) => res.json())
      .then((data) => active && setStatus(data.status === 'ok' ? 'ok' : 'error'))
      .catch(() => active && setStatus('error'))
    return () => {
      active = false
    }
  }, [])

  const label =
    status === 'loading'
      ? 'API 服务连接中'
      : status === 'ok'
        ? 'API 服务在线'
        : 'API 服务未接入'

  return (
    <span className="inline-flex items-center gap-2 text-sm text-foreground/70">
      <span
        className={cn(
          'h-2 w-2 rounded-full',
          status === 'ok' && 'bg-accent',
          status === 'loading' && 'animate-pulse bg-foreground',
          status === 'error' && 'bg-destructive',
        )}
      />
      {label}
    </span>
  )
}
