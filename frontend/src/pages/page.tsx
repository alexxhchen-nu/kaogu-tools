import Link from "next/link";
import { ChevronRight } from "@/lib/icons";
import { TOOLS } from "@/lib/tools";

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <main className="toolbox-home">
        <section className="toolbox-stage">
          <section className="toolbox-root" aria-label="根节点">
            <h1>考古工具箱</h1>
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
                  <span className="toolbox-list-media" data-index={tool.index}>
                    <span className="toolbox-list-icon">
                      <Icon className="h-12 w-12" />
                    </span>
                  </span>
                  <span className="toolbox-list-copy">
                    <strong>{tool.name}</strong>
                    <em>{tool.tagline}</em>
                    <span className="toolbox-list-actions">
                      <span className="toolbox-list-button">打开工具</span>
                      <span className="toolbox-list-meta">{tool.en}</span>
                    </span>
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
