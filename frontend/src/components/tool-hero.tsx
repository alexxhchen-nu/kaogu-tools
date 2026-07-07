import Link from 'next/link'
import { ChevronRight } from '@/lib/icons'
import type { ToolMeta } from '@/lib/tools'

export function ToolHero({ tool }: { tool: ToolMeta }) {
  const Icon = tool.icon
  return (
    <div className="bg-background">
      <div className="mx-auto max-w-[var(--site-max-width)] px-[var(--site-gutter)] py-[var(--page-block)]">
        <nav className="mb-6 flex items-center gap-1.5 text-xs font-bold text-foreground/60">
          <Link href="/" className="hover:text-accent">
            首页
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="text-foreground">{tool.name}</span>
        </nav>
        <div className="grid gap-6 border-y border-foreground py-7 md:grid-cols-[auto_1fr_auto] md:items-center">
          <span className="grid h-24 w-24 shrink-0 place-items-center border border-foreground">
            <Icon className="h-11 w-11" strokeWidth={1.6} />
          </span>
          <div>
            <h1 className="font-serif text-4xl font-black leading-tight text-balance sm:text-5xl">
              {tool.name}
            </h1>
            <p className="mt-2 text-xs font-black uppercase text-foreground/60">
              {tool.en}
            </p>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-foreground/70">
              {tool.description}
            </p>
          </div>
          <div className="hidden h-24 w-24 flex-col items-center justify-center rounded-full border border-foreground outline outline-1 outline-offset-3 outline-foreground md:flex">
            <span className="font-serif text-3xl font-black">考</span>
            <span className="mt-1 text-[10px]">工具</span>
          </div>
        </div>
      </div>
    </div>
  )
}
