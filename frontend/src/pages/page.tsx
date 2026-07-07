import Link from "next/link";
import { ChevronRight } from "@/lib/icons";
import { SiteFooter } from "@/components/site-footer";
import { BackendStatus } from "@/components/backend-status";
import { TOOLS } from "@/lib/tools";

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <main className="toolbox-home flex-1">
        <section className="toolbox-stage mx-auto grid max-w-6xl gap-10 px-5 py-12 md:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)] md:items-center lg:gap-16 lg:py-16">
          <section className="toolbox-root" aria-label="根节点">
            <p>考古工作台</p>
            <h1>考古工具箱</h1>
            <span>统一入口，把文献、目录、墓葬、地图与模型收进同一个操作台。</span>
            <div className="toolbox-root-status">
              <BackendStatus />
            </div>
          </section>

          <nav className="toolbox-list" aria-label="考古工具入口">
            {TOOLS.map((tool) => {
              const Icon = tool.icon;

              return (
                <Link
                  key={tool.slug}
                  href={tool.href}
                  target="_blank"
                  rel="noreferrer"
                  className="toolbox-list-item"
                >
                  <span className="toolbox-list-icon">
                    <Icon className="h-6 w-6" />
                  </span>
                  <span className="toolbox-list-copy">
                    <span>{tool.index}</span>
                    <strong>{tool.name}</strong>
                    <em>{tool.tagline}</em>
                  </span>
                  <ChevronRight className="toolbox-list-arrow h-4 w-4" />
                </Link>
              );
            })}
          </nav>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
