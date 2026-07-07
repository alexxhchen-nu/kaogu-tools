'use client'

import Link from 'next/link'
import { useRouter } from 'next/router'
import { TOOLS } from '@/lib/tools'
import { cn } from '@/lib/utils'

export function SiteHeader() {
  const { pathname } = useRouter()
  const leftTools = TOOLS.slice(0, 2)
  const rightTools = TOOLS.slice(2)

  return (
    <header className="sticky top-0 z-40 bg-background">
      <div className="mx-auto max-w-6xl px-5 pt-3">
        <div className="double-rule h-2" />
        <div className="grid min-h-28 grid-cols-[auto_1fr_auto] items-center gap-5 border-b border-foreground md:grid-cols-[1fr_auto_1fr]">
          <div className="flex items-center gap-8">
            <Link
              href="/"
              className="hidden h-9 w-9 items-center justify-center border border-foreground font-serif text-lg font-black md:flex"
              aria-label="考古工具箱首页"
            >
              考
            </Link>
            <HeaderLinks tools={leftTools} pathname={pathname} align="left" />
          </div>

          <Link
            href="/"
            className="flex h-24 w-24 flex-col items-center justify-center rounded-full border border-foreground outline outline-1 outline-offset-3 outline-foreground"
            aria-label="考古工具箱首页"
          >
            <span className="font-serif text-4xl font-black leading-none">
              考
            </span>
            <span className="mt-2 text-[9px] font-bold">工具箱</span>
          </Link>

          <div className="flex items-center justify-end gap-8">
            <HeaderLinks tools={rightTools} pathname={pathname} align="right" />
            <span className="hidden text-xs font-bold md:block">考古 · 数据</span>
          </div>
        </div>

        <nav className="grid grid-cols-2 gap-px border-b border-foreground py-3 text-sm font-bold md:hidden">
          {TOOLS.map((tool) => {
            const active = pathname === tool.href
            return (
              <Link
                key={tool.slug}
                href={tool.href}
                className={cn(
                  'px-2 py-1',
                  active ? 'text-accent' : 'text-foreground',
                )}
              >
                {tool.name}
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}

function HeaderLinks({
  tools,
  pathname,
  align,
}: {
  tools: typeof TOOLS
  pathname: string
  align: 'left' | 'right'
}) {
  return (
    <nav
      className={cn(
        'hidden flex-1 items-center gap-10 md:flex',
        align === 'right' && 'justify-end',
      )}
    >
      {tools.map((tool) => {
        const active = pathname === tool.href
        return (
          <Link
            key={tool.slug}
            href={tool.href}
            className={cn(
              'text-sm font-black transition-colors hover:text-accent',
              active && 'text-accent',
            )}
          >
            {tool.name}
          </Link>
        )
      })}
    </nav>
  )
}
