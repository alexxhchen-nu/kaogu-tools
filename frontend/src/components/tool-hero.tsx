import Link from 'next/link'
import { ChevronRight } from '@/lib/icons'
import type { ToolMeta } from '@/lib/tools'

export function ToolHero({ tool }: { tool: ToolMeta }) {
  const Icon = tool.icon
  return (
    <div className="bg-background">
      <div className="mx-auto max-w-6xl px-5 py-10">
        <nav className="mb-8 flex items-center gap-1.5 text-xs font-bold text-foreground/60">
          <Link href="/" className="hover:text-accent">
            首页
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="text-foreground">{tool.name}</span>
        </nav>
        <div className="grid gap-8 border-y border-foreground py-8 md:grid-cols-[auto_1fr_auto] md:items-center">
          <span className="grid h-28 w-28 shrink-0 place-items-center border border-foreground">
            <Icon className="h-12 w-12" strokeWidth={1.6} />
          </span>
          <div>
            <p className="text-sm font-black text-accent">{tool.index}</p>
            <h1 className="mt-2 font-serif text-4xl font-black leading-tight text-balance sm:text-5xl">
              {tool.name}
            </h1>
            <p className="mt-2 text-xs font-black uppercase tracking-[0.22em] text-foreground/60">
              {tool.en}
            </p>
            <p className="mt-5 max-w-2xl text-sm leading-7 text-foreground/70">
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
