import Head from "next/head";
import { FormEvent, useEffect, useRef, useState } from "react";
import { ToolHero } from "@/components/tool-hero";
import { getTool } from "@/lib/tools";

type GenerateResponse = {
  html?: string;
  url?: string;
  error?: string;
  stats?: {
    total_tombs?: number;
    shape_count?: number;
    artifact_count?: number;
  };
};

const demoModelUrl = "/models/tombs-3d-viewer.html";

function modellingEndpoint() {
  const base = process.env.NEXT_PUBLIC_KAOGU_API_BASE_URL?.replace(/\/$/, "") ?? "";
  return `${base}/modelling/generate`;
}

function writeLoadingTab(tab: Window, filename: string) {
  tab.document.open();
  tab.document.write(`<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>正在生成墓葬3D模型</title>
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
    <h1>正在生成墓葬3D模型</h1>
    <p>${filename} 上传完成后会在此标签页打开结果。</p>
  </main>
</body>
</html>`);
  tab.document.close();
}

export default function ModellingPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState("选择一个墓葬 CSV 文件，生成结果会在新标签页打开。");
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const objectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
      }
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile || isGenerating) {
      return;
    }

    const resultTab = window.open("", "_blank", "noopener,noreferrer");
    if (resultTab) {
      writeLoadingTab(resultTab, selectedFile.name);
    }

    setIsGenerating(true);
    setStatus("正在上传并生成模型...");
    setResultUrl(null);

    try {
      const body = new FormData();
      body.append("file", selectedFile);

      const response = await fetch(modellingEndpoint(), {
        method: "POST",
        body,
      });

      const payload = (await response.json()) as GenerateResponse;
      if (!response.ok || payload.error) {
        throw new Error(payload.error || `生成失败：HTTP ${response.status}`);
      }

      let targetUrl = payload.url;
      if (!targetUrl && payload.html) {
        if (objectUrlRef.current) {
          URL.revokeObjectURL(objectUrlRef.current);
        }
        const blob = new Blob([payload.html], { type: "text/html;charset=utf-8" });
        targetUrl = URL.createObjectURL(blob);
        objectUrlRef.current = targetUrl;
      }

      if (!targetUrl) {
        throw new Error("后端没有返回 url 或 html。");
      }

      if (resultTab) {
        resultTab.location.href = targetUrl;
      } else {
        window.open(targetUrl, "_blank", "noopener,noreferrer");
      }

      setResultUrl(targetUrl);
      const count = payload.stats?.total_tombs;
      setStatus(count ? `已生成 ${count} 座墓葬模型，结果已在新标签页打开。` : "结果已在新标签页打开。");
    } catch (error) {
      const message = error instanceof Error ? error.message : "生成失败。";
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

  const tool = getTool("modelling");

  if (!tool) {
    return null;
  }

  return (
    <>
      <Head>
        <title>墓葬3D建模</title>
        <meta name="description" content="上传墓葬 CSV，生成并在新标签页打开 Three.js 3D 模型。" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="tool-page-shell">
        <main className="tool-page-main">
          <ToolHero tool={tool} />

          <section className="tool-workbench-section">
            <div className="model-workbench">
              <section className="tool-panel model-panel">
                <div className="tool-panel-heading">
                  <div>
                    <h2 className="font-serif text-xl font-black">生成模型</h2>
                    <p className="mt-1 text-sm leading-7 text-foreground/70">
                      上传墓葬 CSV 后，生成结果会在新标签页打开。
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

                  <div className="actions">
                    <button type="submit" disabled={!selectedFile || isGenerating}>
                      {isGenerating ? "生成中..." : "生成并打开新标签页"}
                    </button>
                    <a href={demoModelUrl} target="_blank" rel="noreferrer">
                      打开示例模型
                    </a>
                  </div>
                </form>
              </section>

              <section className="tool-panel model-panel">
                <div className="tool-panel-heading">
                  <div>
                    <h2 className="font-serif text-xl font-black">状态</h2>
                    <p className="mt-1 text-sm leading-7 text-foreground/70">
                      生成完成后可以重新打开最近一次模型。
                    </p>
                  </div>
                </div>

                <div className="model-status-panel">
                  <p className="status">{status}</p>

                  {resultUrl ? (
                    <a className="result-link" href={resultUrl} target="_blank" rel="noreferrer">
                      重新打开最近生成的模型
                    </a>
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
