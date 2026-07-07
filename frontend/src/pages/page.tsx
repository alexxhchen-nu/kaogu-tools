import Link from "next/link";
import { ChevronRight } from "@/lib/icons";
import { BackendStatus } from "@/components/backend-status";
import { TOOLS } from "@/lib/tools";

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <main className="toolbox-home">
        <section className="toolbox-stage">
          <section className="toolbox-root" aria-label="根节点">
            <h1>考古工具箱</h1>
            <div className="toolbox-root-divider" aria-hidden="true" />
            <div className="toolbox-root-copy">
              <span>统一入口，把文献、目录、墓葬、地图与模型收进同一个操作台。</span>
              <div className="toolbox-root-status">
                <BackendStatus />
              </div>
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
    </div>
  );
}
