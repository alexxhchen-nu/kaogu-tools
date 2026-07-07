import Head from "next/head"
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
    <div className="tool-page-shell">
      <Head>
        <title>{`${tool.name} · 考古工具箱`}</title>
        <meta name="description" content={tool.description} />
      </Head>

      <main className="tool-page-main">
        <ToolHero tool={tool} />
        <section className="tool-workbench-section">
          <GenericToolWorkbench tool={workbenchTool} />
        </section>
      </main>
    </div>
  )
}
