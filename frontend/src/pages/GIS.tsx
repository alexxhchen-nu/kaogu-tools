import Head from "next/head";
import { FormEvent, useEffect, useRef, useState } from "react";
import { ToolHero } from "@/components/tool-hero";
import { resolveEndpoint } from "@/lib/api-client";
import { getTool } from "@/lib/tools";

type CoordMode = "auto" | "exact" | "jitter" | "none";

type GISStats = {
  total_tombs?: number;
  site_count?: number;
  sites?: Record<string, number>;
  coord_mode?: CoordMode;
};

type GISResponse = {
  ok?: boolean;
  data?: {
    sites?: Record<string, string>;
    overview?: string | null;
    stats?: GISStats;
  };
  detail?: string;
  error?: string;
};

type SiteMapResult = {
  key: string;
  count?: number;
  url: string;
};

function writeLoadingTab(tab: Window, filename: string) {
  tab.document.open();
  tab.document.write(`<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>正在生成遗址空间地图</title>
  <style>
    @font-face {
      font-family: "Noto Sans SC";
      src: url("/fonts/Noto/NotoSansSC-VariableFont_wght.ttf") format("truetype");
      font-style: normal;
      font-weight: 100 900;
      font-display: swap;
    }

    @font-face {
      font-family: "Noto Serif SC";
      src: url("/fonts/Noto/NotoSerifSC-Regular.ttf") format("truetype");
      font-style: normal;
      font-weight: 400;
      font-display: swap;
    }

    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #141417;
      color: #e8e4da;
      font-family: "Noto Sans SC", system-ui, sans-serif;
    }
    main { max-width: 520px; padding: 32px; line-height: 1.7; }
    h1 { margin: 0 0 8px; font-family: "Noto Serif SC", serif; font-size: 22px; }
    p { color: #aaa28f; }
  </style>
</head>
<body>
  <main>
    <h1>正在生成遗址空间地图</h1>
    <p>${filename} 上传完成后会在此标签页打开结果。</p>
  </main>
</body>
</html>`);
  tab.document.close();
}

function revokeUrls(urls: string[]) {
  for (const url of urls) {
    URL.revokeObjectURL(url);
  }
}

export default function GISPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState("选择一个包含遗址、墓葬或坐标字段的 CSV 文件。");
  const [isGenerating, setIsGenerating] = useState(false);
  const [coordMode, setCoordMode] = useState<CoordMode>("auto");
  const [includeOverview, setIncludeOverview] = useState(false);
  const [stats, setStats] = useState<GISStats | null>(null);
  const [siteMaps, setSiteMaps] = useState<SiteMapResult[]>([]);
  const [overviewUrl, setOverviewUrl] = useState<string | null>(null);
  const objectUrlsRef = useRef<string[]>([]);

  useEffect(() => {
    return () => {
      revokeUrls(objectUrlsRef.current);
    };
  }, []);

  function replaceGeneratedUrls(nextUrls: string[]) {
    revokeUrls(objectUrlsRef.current);
    objectUrlsRef.current = nextUrls;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile || isGenerating) {
      return;
    }

    const resultTab = window.open("about:blank", "_blank");
    if (resultTab) {
      resultTab.opener = null;
      writeLoadingTab(resultTab, selectedFile.name);
    }

    setIsGenerating(true);
    setStatus("正在上传并生成地图...");
    setStats(null);
    setSiteMaps([]);
    setOverviewUrl(null);

    try {
      const body = new FormData();
      body.append("file", selectedFile);
      body.append("overview", includeOverview ? "true" : "false");
      body.append("coord_mode", coordMode);

      const response = await fetch(resolveEndpoint("/gis/generate"), {
        method: "POST",
        body,
      });

      const payload = (await response.json()) as GISResponse;
      if (!response.ok || payload.error || payload.detail) {
        throw new Error(payload.error || payload.detail || `生成失败：HTTP ${response.status}`);
      }

      const sites = payload.data?.sites ?? {};
      const generatedUrls: string[] = [];
      const nextSiteMaps = Object.entries(sites).map(([key, html]) => {
        const url = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
        generatedUrls.push(url);
        return {
          key,
          count: payload.data?.stats?.sites?.[key],
          url,
        };
      });

      let nextOverviewUrl: string | null = null;
      if (payload.data?.overview) {
        nextOverviewUrl = URL.createObjectURL(new Blob([payload.data.overview], { type: "text/html;charset=utf-8" }));
        generatedUrls.push(nextOverviewUrl);
      }

      if (!nextOverviewUrl && nextSiteMaps.length === 0) {
        throw new Error("后端没有返回可打开的地图 HTML。");
      }

      replaceGeneratedUrls(generatedUrls);
      setSiteMaps(nextSiteMaps);
      setOverviewUrl(nextOverviewUrl);
      setStats(payload.data?.stats ?? null);

      const targetUrl = nextOverviewUrl ?? nextSiteMaps[0]?.url;
      if (targetUrl) {
        if (resultTab) {
          resultTab.location.replace(targetUrl);
        } else {
          window.open(targetUrl, "_blank", "noopener,noreferrer");
        }
      }

      const total = payload.data?.stats?.total_tombs;
      const siteCount = payload.data?.stats?.site_count ?? nextSiteMaps.length;
      setStatus(
        total
          ? `已生成 ${total} 座墓葬、${siteCount} 个站点地图。`
          : `已生成 ${siteCount} 个站点地图。`,
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "生成失败。";
      replaceGeneratedUrls([]);
      if (resultTab) {
        resultTab.document.open();
        resultTab.document.write(`<pre style="white-space:pre-wrap;font:14px monospace;padding:24px">${message}</pre>`);
        resultTab.document.close();
      }
      setStatus(message);
    } finally {
      setIsGenerating(false);
    }
  }

  const tool = getTool("gis");

  if (!tool) {
    return null;
  }

  return (
    <>
      <Head>
        <title>遗址空间分析 · 考古工具箱</title>
        <meta name="description" content="上传墓葬或遗址 CSV，生成可打开的交互式 GIS 地图。" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="tool-page-shell">
        <main className="tool-page-main">
          <ToolHero tool={tool} />

          <section className="tool-workbench-section">
            <div className="model-workbench gis-workbench">
              <section className="tool-panel model-panel">
                <div className="tool-panel-heading">
                  <div>
                    <h2 className="font-serif text-xl font-black">生成地图</h2>
                    <p className="mt-1 text-sm leading-7 text-foreground/70">
                      上传 CSV 后生成站点地图，结果会在新标签页打开。
                    </p>
                  </div>
                </div>

                <form className="upload-form" onSubmit={handleSubmit}>
                  <label className="file-picker">
                    <span>CSV 数据文件</span>
                    <input
                      type="file"
                      accept=".csv,text/csv"
                      onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                    />
                  </label>

                  <div className="gis-options">
                    <label className="field-group">
                      <span>坐标模式</span>
                      <select value={coordMode} onChange={(event) => setCoordMode(event.target.value as CoordMode)}>
                        <option value="auto">自动检测</option>
                        <option value="exact">使用精确坐标</option>
                        <option value="jitter">站点中心偏移</option>
                        <option value="none">站点中心</option>
                      </select>
                    </label>

                    <label className="checkbox-field">
                      <input
                        type="checkbox"
                        checked={includeOverview}
                        onChange={(event) => setIncludeOverview(event.target.checked)}
                      />
                      <span>同时生成总览地图</span>
                    </label>
                  </div>

                  <div className="actions">
                    <button type="submit" disabled={!selectedFile || isGenerating}>
                      {isGenerating ? "生成中..." : "生成并打开地图"}
                    </button>
                  </div>
                </form>
              </section>

              <section className="tool-panel model-panel">
                <div className="tool-panel-heading">
                  <div>
                    <h2 className="font-serif text-xl font-black">结果</h2>
                    <p className="mt-1 text-sm leading-7 text-foreground/70">
                      生成后可以重新打开总览或单站点地图。
                    </p>
                  </div>
                </div>

                <div className="model-status-panel gis-results-panel">
                  <p className="status">{status}</p>

                  {stats ? (
                    <dl className="stats-grid">
                      <div>
                        <dt>墓葬数</dt>
                        <dd>{stats.total_tombs ?? 0}</dd>
                      </div>
                      <div>
                        <dt>站点数</dt>
                        <dd>{stats.site_count ?? siteMaps.length}</dd>
                      </div>
                      <div>
                        <dt>坐标模式</dt>
                        <dd>{stats.coord_mode ?? coordMode}</dd>
                      </div>
                    </dl>
                  ) : null}

                  {overviewUrl ? (
                    <a className="result-link" href={overviewUrl} target="_blank" rel="noreferrer">
                      打开总览地图
                    </a>
                  ) : null}

                  {siteMaps.length > 0 ? (
                    <div className="site-result-list">
                      {siteMaps.map((site) => (
                        <div className="site-result-row" key={site.key}>
                          <div>
                            <strong>{site.key}</strong>
                            <span>{site.count ? `${site.count} 座墓葬` : "站点地图"}</span>
                          </div>
                          <a href={site.url} target="_blank" rel="noreferrer">
                            打开地图
                          </a>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              </section>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
