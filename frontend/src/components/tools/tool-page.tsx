import Head from "next/head"
import { SiteFooter } from "@/components/site-footer"
import { SiteHeader } from "@/components/site-header"
import { ToolHero } from "@/components/tool-hero"
import { GenericToolWorkbench } from "@/components/tools/generic-tool-workbench"
import { getTool } from "@/lib/tools"

export function ToolPage({ slug }: { slug: string }) {
  const tool = getTool(slug)

  if (!tool) {
    return null
  }

  const { icon: _icon, ...workbenchTool } = tool

  return (
    <div className="flex min-h-screen flex-col">
      <Head>
        <title>{tool.name} · 考古工具箱</title>
        <meta name="description" content={tool.description} />
      </Head>

      <SiteHeader />
      <main className="flex-1">
        <ToolHero tool={tool} />
        <section className="mx-auto max-w-6xl px-5 pb-14">
          <GenericToolWorkbench tool={workbenchTool} />
        </section>
      </main>
      <SiteFooter />
    </div>
  )
}
