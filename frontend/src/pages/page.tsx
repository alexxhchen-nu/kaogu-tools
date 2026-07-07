import type { CSSProperties } from "react";
import { useMemo, useState } from "react";
import Link from "next/link";
import { ChevronRight } from "@/lib/icons";
import { SiteFooter } from "@/components/site-footer";
import { BackendStatus } from "@/components/backend-status";
import { TOOLS } from "@/lib/tools";

const nodePositions = [
  { x: 50, y: 12 },
  { x: 86, y: 36 },
  { x: 72, y: 86 },
  { x: 28, y: 86 },
  { x: 14, y: 36 },
];

export default function LandingPage() {
  const [activeSlug, setActiveSlug] = useState(TOOLS[0]?.slug ?? "");
  const activeTool = useMemo(
    () => TOOLS.find((tool) => tool.slug === activeSlug) ?? TOOLS[0],
    [activeSlug],
  );

  return (
    <div className="flex min-h-screen flex-col">
      <main className="toolbox-home flex-1">
        <section className="toolbox-stage mx-auto max-w-7xl px-5 py-10 sm:py-14">
          <div className="toolbox-title mx-auto max-w-3xl text-center">
            <p>考古工作台</p>
            <h1>考古工具箱</h1>
            <span>把文献、目录、墓葬、地图与模型收进同一个操作台。</span>
          </div>

          <div className="toolbox-map" aria-label="考古工具入口">
            <div className="toolbox-orbit" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>

            <section className="toolbox-core" aria-live="polite">
              <div className="toolbox-handle" aria-hidden="true" />
              <div className="toolbox-case">
                <div className="toolbox-case-top">
                  <span>当前工具</span>
                  <BackendStatus />
                </div>

                <div className="toolbox-compass" aria-hidden="true">
                  <span>考</span>
                </div>

                <p className="toolbox-index">{activeTool.index}</p>
                <h2>{activeTool.name}</h2>
                <p className="toolbox-summary">{activeTool.tagline}</p>
                <Link className="toolbox-open" href={activeTool.href}>
                  打开{activeTool.name}
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </div>
            </section>

            <nav className="toolbox-nodes">
              {TOOLS.map((tool, index) => {
                const Icon = tool.icon;
                const position = nodePositions[index] ?? { x: 50, y: 50 };
                const isActive = activeTool.slug === tool.slug;

                return (
                  <Link
                    key={tool.slug}
                    href={tool.href}
                    className={`toolbox-node ${isActive ? "is-active" : ""}`}
                    style={
                      {
                        "--node-x": `${position.x}%`,
                        "--node-y": `${position.y}%`,
                      } as CSSProperties
                    }
                    aria-current={isActive ? "page" : undefined}
                    onMouseEnter={() => setActiveSlug(tool.slug)}
                    onFocus={() => setActiveSlug(tool.slug)}
                  >
                    <span className="toolbox-node-icon">
                      <Icon className="h-6 w-6" />
                    </span>
                    <span className="toolbox-node-copy">
                      <span>{tool.index}</span>
                      <strong>{tool.name}</strong>
                      <em>{tool.tagline}</em>
                    </span>
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="toolbox-strip" aria-label="工具说明">
            <span>统一入口</span>
            <span>真实函数接口</span>
            <span>文献到数据</span>
            <span>地图与三维</span>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
