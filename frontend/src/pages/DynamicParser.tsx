import Head from "next/head";
import { FormEvent, useMemo, useState } from "react";
import { ToolHero } from "@/components/tool-hero";
import { resolveEndpoint } from "@/lib/api-client";
import { Download, Loader2, Send } from "@/lib/icons";
import { getTool } from "@/lib/tools";

type RunState = "idle" | "loading" | "done" | "error";

type Artifact = {
  "器物编号"?: string;
  "器物名称"?: string;
  "材质"?: string;
  "器型"?: string;
  "数量"?: number | string;
  "特征描述"?: string;
};

type TombRecord = {
  "墓葬编号"?: string;
  "年代"?: string;
  "墓向"?: string;
  "墓葬形制"?: string;
  "墓口长"?: number | string | null;
  "墓口宽"?: number | string | null;
  "墓深"?: number | string | null;
  "发掘位置"?: string;
  "层位"?: string;
  "备注"?: string;
  "随葬器物"?: Artifact[];
};

type ParserData = {
  json?: {
    "墓葬列表"?: TombRecord[];
    "原始文本片段"?: string;
  };
  markdown?: string;
  csv?: string;
};

type ParserResponse = {
  ok?: boolean;
  data?: ParserData;
  detail?: string;
  error?: string;
};

const exampleInput = `## M1
M1位于东区，年代战国。墓向南北向。墓口长2.5米，宽1.2米，深3.0米。
埋葬方式土坑竖穴墓。封土直径4米。保存状态较好。出土器物2件：陶罐1件，铜剑1件。`;

function formatValue(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function formatDimensions(tomb: TombRecord) {
  const length = formatValue(tomb["墓口长"]);
  const width = formatValue(tomb["墓口宽"]);
  const depth = formatValue(tomb["墓深"]);

  if (length === "—" && width === "—" && depth === "—") {
    return "—";
  }

  return `${length} × ${width} × ${depth}`;
}

function artifactSummary(artifacts: Artifact[] | undefined) {
  if (!artifacts?.length) return "—";

  return artifacts
    .map((artifact) => {
      const name = artifact["器物名称"] || artifact["器型"] || "未命名器物";
      const count = artifact["数量"];
      return count ? `${name}${count}件` : name;
    })
    .join("、");
}

function downloadCsv(csv: string) {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = `kaogu-dynamic-parser-${Date.now()}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function DynamicParserPage() {
  const [text, setText] = useState(exampleInput);
  const [state, setState] = useState<RunState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ParserData | null>(null);

  const tool = getTool("dynamic-parser");
  const tombs = result?.json?.["墓葬列表"] ?? [];
  const artifactCount = useMemo(
    () => tombs.reduce((total, tomb) => total + (tomb["随葬器物"]?.length ?? 0), 0),
    [tombs],
  );

  if (!tool) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = text.trim();

    if (!trimmed || state === "loading") {
      return;
    }

    setState("loading");
    setError(null);
    setResult(null);

    try {
      const response = await fetch(resolveEndpoint("/dynamic-parser/parse"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmed, report_name: "manual-input" }),
      });
      const payload = (await response.json()) as ParserResponse;

      if (!response.ok || payload.error || payload.detail) {
        throw new Error(payload.error || payload.detail || `抽取失败：HTTP ${response.status}`);
      }

      setResult(payload.data ?? null);
      setState("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "墓葬文本抽取失败。");
      setState("error");
    }
  }

  return (
    <>
      <Head>
        <title>墓葬文本抽取 · 考古工具箱</title>
        <meta name="description" content="从墓葬报告文本中抽取墓葬、尺寸与随葬器物字段。" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="tool-page-shell">
        <main className="tool-page-main">
          <ToolHero tool={tool} />

          <section className="tool-workbench-section">
            <div className="model-workbench parser-workbench">
              <section className="tool-panel model-panel">
                <div className="tool-panel-heading">
                  <div>
                    <h2 className="font-serif text-xl font-black">输入文本</h2>
                    <p className="mt-1 text-sm leading-7 text-foreground/70">
                      粘贴墓葬段落、Markdown 或发掘简报正文。
                    </p>
                  </div>
                </div>

                <form className="parser-form" onSubmit={handleSubmit}>
                  <textarea
                    className="tool-textarea parser-textarea"
                    value={text}
                    onChange={(event) => setText(event.target.value)}
                    spellCheck={false}
                  />

                  <div className="actions">
                    <button type="submit" disabled={!text.trim() || state === "loading"}>
                      {state === "loading" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                      {state === "loading" ? "抽取中..." : "抽取墓葬信息"}
                    </button>
                  </div>
                </form>
              </section>

              <section className="tool-panel model-panel parser-results-panel">
                <div className="tool-panel-heading">
                  <div>
                    <h2 className="font-serif text-xl font-black">抽取结果</h2>
                    <p className="mt-1 text-sm leading-7 text-foreground/70">
                      结果可继续导出为 CSV，用于三维建模或 GIS 分析。
                    </p>
                  </div>
                </div>

                <div className="parser-result-body">
                  {state === "idle" ? (
                    <div className="tool-empty-state">
                      <p>运行后会显示墓葬表格、Markdown 和 CSV 导出入口。</p>
                    </div>
                  ) : null}

                  {state === "loading" ? (
                    <div className="tool-empty-state">
                      <Loader2 className="h-5 w-5 animate-spin" />
                      <p className="mt-3">正在等待后端返回结构化结果...</p>
                    </div>
                  ) : null}

                  {state === "error" && error ? (
                    <div className="parser-error">{error}</div>
                  ) : null}

                  {state === "done" && result ? (
                    <>
                      <dl className="stats-grid parser-stats">
                        <div>
                          <dt>墓葬数</dt>
                          <dd>{tombs.length}</dd>
                        </div>
                        <div>
                          <dt>器物记录</dt>
                          <dd>{artifactCount}</dd>
                        </div>
                        <div>
                          <dt>CSV</dt>
                          <dd>{result.csv ? "可下载" : "—"}</dd>
                        </div>
                      </dl>

                      {tombs.length > 0 ? (
                        <div className="parser-table-wrap">
                          <table className="parser-table">
                            <thead>
                              <tr>
                                <th>编号</th>
                                <th>年代</th>
                                <th>形制</th>
                                <th>墓向</th>
                                <th>尺寸 长×宽×深</th>
                                <th>随葬器物</th>
                              </tr>
                            </thead>
                            <tbody>
                              {tombs.map((tomb, index) => (
                                <tr key={`${tomb["墓葬编号"] ?? "tomb"}-${index}`}>
                                  <td>{formatValue(tomb["墓葬编号"])}</td>
                                  <td>{formatValue(tomb["年代"])}</td>
                                  <td>{formatValue(tomb["墓葬形制"])}</td>
                                  <td>{formatValue(tomb["墓向"])}</td>
                                  <td>{formatDimensions(tomb)}</td>
                                  <td>{artifactSummary(tomb["随葬器物"])}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="parser-empty-result">后端返回成功，但没有识别到墓葬记录。</div>
                      )}

                      <div className="parser-result-actions">
                        <button
                          type="button"
                          disabled={!result.csv}
                          onClick={() => {
                            if (result.csv) downloadCsv(result.csv);
                          }}
                        >
                          <Download className="h-4 w-4" />
                          下载 CSV
                        </button>
                      </div>

                      {result.markdown ? (
                        <details className="parser-details" open>
                          <summary>Markdown 预览</summary>
                          <pre>{result.markdown}</pre>
                        </details>
                      ) : null}

                      <details className="parser-details">
                        <summary>JSON 预览</summary>
                        <pre>{JSON.stringify(result.json ?? result, null, 2)}</pre>
                      </details>
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
