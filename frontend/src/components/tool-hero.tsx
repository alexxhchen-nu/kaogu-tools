import Link from 'next/link'
import { ChevronRight } from '@/lib/icons'
import type { ToolMeta } from '@/lib/tools'

export function ToolHero({ tool }: { tool: ToolMeta }) {
  const Icon = tool.icon
  return (
    <div className="tool-hero">
      <div className="tool-hero-inner">
        <nav className="tool-crumbs">
          <Link href="/" className="hover:text-accent">
            首页
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="text-foreground">{tool.name}</span>
        </nav>
        <div className="tool-hero-box">
          <span className="tool-hero-icon" data-index={tool.index}>
            <Icon className="h-11 w-11" strokeWidth={1.6} />
          </span>
          <div>
            <h1>{tool.name}</h1>
            <p className="tool-hero-kicker">{tool.en}</p>
            <p className="tool-hero-copy">{tool.description}</p>
          </div>
          <div className="tool-hero-mark">
            <span className="font-serif text-3xl font-black">考</span>
            <span className="mt-1 text-[10px]">工具</span>
          </div>
        </div>
      </div>
    </div>
  )
}
