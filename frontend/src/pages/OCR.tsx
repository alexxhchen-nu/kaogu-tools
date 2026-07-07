import Head from "next/head";
import { FormEvent, useState } from "react";
import { ToolHero } from "@/components/tool-hero";
import { resolveEndpoint } from "@/lib/api-client";
import { Download, FileText, FileUp, Loader2 } from "@/lib/icons";
import { getTool } from "@/lib/tools";

type RunState = "idle" | "loading" | "done" | "error";

type OCRLine = {
  text: string;
  confidence?: number | null;
  box?: number[][] | null;
};

type OCRPage = {
  page_number: number;
  text: string;
  lines: OCRLine[];
};

type OCRStats = {
  filename?: string;
  engine?: string;
  lang?: string;
  page_count?: number;
  line_count?: number;
  elapsed_seconds?: number | null;
};

type OCRData = {
  text?: string;
  markdown?: string;
  pages?: OCRPage[];
  stats?: OCRStats;
};

type OCRResponse = {
  ok?: boolean;
  data?: OCRData;
  detail?: string;
  error?: string;
  job_id?: string;
  status?: "queued" | "running" | "done" | "error";
  message?: string;
};

const OCR_POLL_INTERVAL_MS = 1500;

function formatStat(value: number | undefined | null) {
  return Number.isFinite(value) ? String(value) : "—";
}

function formatElapsed(value: number | undefined | null) {
  return Number.isFinite(value) ? `${value}s` : "—";
}

function formatConfidence(value: number | undefined | null) {
  if (!Number.isFinite(value)) return "—";
  return `${Math.round(Number(value) * 100)}%`;
}

function downloadText(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function readOcrResponse(response: Response) {
  const payload = (await response.json().catch(() => null)) as OCRResponse | null;
  if (!response.ok || !payload || payload.error || payload.detail) {
    throw new Error(payload?.error || payload?.detail || `OCR 请求失败，状态码 ${response.status}`);
  }
  return payload;
}

export default function OCRPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [runState, setRunState] = useState<RunState>("idle");
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState("上传 PDF 或扫描图片，识别结果会在右侧显示。");
  const [result, setResult] = useState<OCRData | null>(null);
  const tool = getTool("ocr");

  if (!tool) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile || isRunning) {
      return;
    }

    setIsRunning(true);
    setRunState("loading");
    setStatus("正在上传并提交后台 OCR 任务...");
    setResult(null);

    try {
      const body = new FormData();
      body.append("file", selectedFile);

      const response = await fetch(resolveEndpoint("/ocr/parse"), {
        method: "POST",
        body,
      });
      const payload = await readOcrResponse(response);
      let data = payload.data ?? null;

      if (payload.job_id && payload.status !== "done") {
        setStatus(payload.message || "OCR 任务已提交，正在等待后台 worker...");

        while (true) {
          await sleep(OCR_POLL_INTERVAL_MS);
          const jobResponse = await fetch(resolveEndpoint(`/ocr/jobs/${payload.job_id}`));
          const jobPayload = await readOcrResponse(jobResponse);

          if (jobPayload.status === "queued") {
            setStatus(jobPayload.message || "OCR 任务排队中...");
            continue;
          }

          if (jobPayload.status === "running") {
            setStatus(jobPayload.message || "OCR 正在后台识别，页面可以继续保持打开。");
            continue;
          }

          if (jobPayload.status === "done") {
            data = jobPayload.data ?? null;
            break;
          }

          throw new Error(jobPayload.error || jobPayload.detail || "OCR 任务失败。");
        }
      }

      setResult(data);
      setRunState("done");
      setStatus(
        data?.stats?.page_count
          ? `已识别 ${data.stats.page_count} 页、${data.stats.line_count ?? 0} 行文本。`
          : "OCR 已完成。",
      );
    } catch (error) {
      setRunState("error");
      setResult(null);
      setStatus(error instanceof Error ? error.message : "OCR 失败。");
    } finally {
      setIsRunning(false);
    }
  }

  const stats = result?.stats;
  const pages = result?.pages ?? [];
  const markdown = result?.markdown ?? "";
  const text = result?.text ?? "";

  return (
    <>
      <Head>
        <title>考古文献解析 · 考古工具箱</title>
        <meta name="description" content="上传 PDF 或扫描图片，执行 OCR 并返回 Markdown 与文本行结果。" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="tool-page-shell">
        <main className="tool-page-main">
          <ToolHero tool={tool} />

          <section className="tool-workbench-section">
            <div className="model-workbench ocr-workbench">
              <section className="tool-panel model-panel">
                <div className="tool-panel-heading">
                  <div>
                    <h2 className="font-serif text-xl font-black">上传文档</h2>
                    <p className="mt-1 text-sm leading-7 text-foreground/70">
                      第一版适合页数较少的 PDF，也可上传清晰扫描图片。
                    </p>
                  </div>
                </div>

                <form className="upload-form" onSubmit={handleSubmit}>
                  <label className="file-picker">
                    <span>PDF 或图片文件</span>
                    <input
                      type="file"
                      accept={tool.acceptedTypes}
                      onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                    />
                  </label>

                  <div className="ocr-file-note">
                    <FileText className="h-4 w-4" />
                    <span>{selectedFile ? selectedFile.name : "OCR 会提交为后台任务，长文档不会阻塞主服务。"}</span>
                  </div>

                  <div className="actions">
                    <button type="submit" disabled={!selectedFile || isRunning}>
                      {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
                      {isRunning ? "识别中..." : "开始 OCR"}
                    </button>
                  </div>
                </form>
              </section>

              <section className="tool-panel model-panel ocr-results-panel">
                <div className="tool-panel-heading">
                  <div>
                    <h2 className="font-serif text-xl font-black">识别结果</h2>
                    <p className="mt-1 text-sm leading-7 text-foreground/70">
                      文本可以继续粘贴到墓葬文本抽取工具里做结构化处理。
                    </p>
                  </div>
                </div>

                <div className={`model-status-panel ocr-result-body model-status-panel--${runState}`}>
                  {runState === "idle" ? (
                    <div className="tool-empty-state compact-empty-state">
                      <p>运行后会显示页数、文本行数、耗时、Markdown 预览和行级识别结果。</p>
                    </div>
                  ) : null}

                  {runState === "loading" ? (
                    <div className="tool-empty-state compact-empty-state">
                      <Loader2 className="h-5 w-5 animate-spin" />
                      <p className="mt-3">后台 OCR 任务运行中...</p>
                    </div>
                  ) : null}

                  <p className="status">{status}</p>

                  {stats ? (
                    <dl className="stats-grid ocr-stats">
                      <div>
                        <dt>页数</dt>
                        <dd>{formatStat(stats.page_count)}</dd>
                      </div>
                      <div>
                        <dt>文本行</dt>
                        <dd>{formatStat(stats.line_count)}</dd>
                      </div>
                      <div>
                        <dt>耗时</dt>
                        <dd>{formatElapsed(stats.elapsed_seconds)}</dd>
                      </div>
                      <div>
                        <dt>引擎</dt>
                        <dd>{stats.engine ?? "—"}</dd>
                      </div>
                    </dl>
                  ) : null}

                  {result ? (
                    <>
                      <div className="parser-result-actions">
                        <button
                          type="button"
                          disabled={!text}
                          onClick={() => downloadText(text, "kaogu-ocr-result.txt", "text/plain;charset=utf-8")}
                        >
                          <Download className="h-4 w-4" />
                          下载 TXT
                        </button>
                        <button
                          type="button"
                          disabled={!markdown}
                          onClick={() =>
                            downloadText(markdown, "kaogu-ocr-result.md", "text/markdown;charset=utf-8")
                          }
                        >
                          <Download className="h-4 w-4" />
                          下载 Markdown
                        </button>
                      </div>

                      {markdown ? (
                        <details className="parser-details" open>
                          <summary>Markdown 预览</summary>
                          <pre>{markdown}</pre>
                        </details>
                      ) : null}

                      {pages.length ? (
                        <details className="parser-details">
                          <summary>行级识别结果</summary>
                          <div className="ocr-page-list">
                            {pages.map((page) => (
                              <section key={page.page_number} className="ocr-page-result">
                                <h3>第 {page.page_number} 页</h3>
                                {page.lines.length ? (
                                  <ol>
                                    {page.lines.map((line, index) => (
                                      <li key={`${page.page_number}-${index}`}>
                                        <span>{line.text}</span>
                                        <em>{formatConfidence(line.confidence)}</em>
                                      </li>
                                    ))}
                                  </ol>
                                ) : (
                                  <p>这一页没有识别到文本行。</p>
                                )}
                              </section>
                            ))}
                          </div>
                        </details>
                      ) : null}
                    </>
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
