import Head from "next/head";
import { FormEvent, useEffect, useRef, useState } from "react";

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
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #141417;
      color: #e8e4da;
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
    }
    main { max-width: 520px; padding: 32px; line-height: 1.7; }
    h1 { margin: 0 0 8px; font-size: 22px; }
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

  return (
    <>
      <Head>
        <title>墓葬3D建模</title>
        <meta name="description" content="上传墓葬 CSV，生成并在新标签页打开 Three.js 3D 模型。" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <main className="model-page">
        <section className="model-panel">
          <div className="model-heading">
            <p>考古工具 / 3D 建模</p>
            <h1>墓葬3D建模</h1>
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

          <p className="status">{status}</p>

          {resultUrl ? (
            <a className="result-link" href={resultUrl} target="_blank" rel="noreferrer">
              重新打开最近生成的模型
            </a>
          ) : null}
        </section>
      </main>

      <style jsx>{`
        .model-page {
          min-height: 100vh;
          padding: 28px;
          background:
            linear-gradient(90deg, rgba(184, 68, 47, 0.08) 0 1px, transparent 1px 100%),
            var(--paper);
          background-size: 24px 100%, auto;
        }

        .model-panel {
          max-width: 720px;
          border: 1px solid var(--line);
          background: var(--panel);
          padding: 28px;
          box-shadow: var(--shadow);
        }

        .model-heading {
          padding-bottom: 18px;
          border-bottom: 2px solid var(--ink);
        }

        .model-heading p {
          margin: 0 0 6px;
          color: var(--muted);
          font-size: 14px;
        }

        .model-heading h1 {
          margin: 0;
          color: var(--ink);
          font-size: 34px;
          font-weight: 400;
          letter-spacing: 0;
        }

        .upload-form {
          display: grid;
          gap: 18px;
          margin-top: 24px;
        }

        .file-picker {
          display: grid;
          gap: 8px;
          color: var(--muted);
        }

        .file-picker input {
          min-height: 48px;
          border: 1px solid var(--line);
          background: var(--paper);
          color: var(--ink);
          padding: 10px;
        }

        .actions {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          align-items: center;
        }

        .actions button,
        .actions a,
        .result-link {
          min-height: 42px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border: 1px solid var(--ink);
          background: var(--ink);
          color: var(--panel);
          padding: 0 16px;
          text-decoration: none;
          cursor: pointer;
        }

        .actions a,
        .result-link {
          background: transparent;
          color: var(--ink);
        }

        .actions button:disabled {
          cursor: not-allowed;
          opacity: 0.48;
        }

        .status {
          margin: 18px 0 0;
          color: var(--muted);
          line-height: 1.7;
        }

        .result-link {
          margin-top: 16px;
        }

        @media (max-width: 640px) {
          .model-page {
            padding: 16px;
          }

          .model-panel {
            padding: 20px;
          }

          .model-heading h1 {
            font-size: 28px;
          }
        }
      `}</style>
    </>
  );
}
