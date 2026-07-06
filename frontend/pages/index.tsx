import fs from "node:fs/promises";
import path from "node:path";
import Head from "next/head";
import type { GetStaticProps, InferGetStaticPropsType } from "next";
import { useEffect, useMemo, useState } from "react";

type SeriesId = "all" | "nsbd" | "hebei";
type BookSeriesId = Exclude<SeriesId, "all">;

type Book = {
  id: string;
  series: BookSeriesId;
  title: string;
  filename: string;
  markdownFilename?: string;
  csvFilename?: string;
  tags: string[];
  description: string;
};

type Catalogue = {
  _meta: {
    description: string;
    version: string;
    lastUpdated: string;
    sources: {
      pdf: string;
      parsing: string;
    };
  };
  baseUrls: {
    pdf: string;
    markdown: string;
    csv: string;
  };
  seriesMeta: Record<
    BookSeriesId,
    {
      label: string;
      color: string;
      description: string;
    }
  >;
  books: Book[];
};

const seriesOrder: SeriesId[] = ["all", "nsbd", "hebei"];

function buildAssetUrl(baseUrl: string, filename?: string) {
  if (!filename) {
    return null;
  }

  const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  return `${encodeURI(normalizedBase)}${encodeURIComponent(filename)}`;
}

export const getStaticProps: GetStaticProps<{ catalogue: Catalogue }> = async () => {
  const cataloguePath = path.join(process.cwd(), "..", "shared", "data_catalogue.json");
  const raw = await fs.readFile(cataloguePath, "utf8");
  const catalogue = JSON.parse(raw) as Catalogue;

  return {
    props: {
      catalogue,
    },
  };
};

export default function HomePage({
  catalogue,
}: InferGetStaticPropsType<typeof getStaticProps>) {
  const [query, setQuery] = useState("");
  const [activeSeries, setActiveSeries] = useState<SeriesId>("all");
  const [selectedBookId, setSelectedBookId] = useState<string | null>(
    catalogue.books[0]?.id ?? null,
  );
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [seriesMenuOpen, setSeriesMenuOpen] = useState(false);

  const visibleBooks = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return catalogue.books.filter((book) => {
      const matchesSeries = activeSeries === "all" || book.series === activeSeries;
      if (!matchesSeries) {
        return false;
      }

      if (!normalizedQuery) {
        return true;
      }

      const haystack = [book.title, book.description, ...book.tags].join(" ").toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [activeSeries, catalogue.books, query]);

  useEffect(() => {
    if (!visibleBooks.some((book) => book.id === selectedBookId)) {
      setSelectedBookId(visibleBooks[0]?.id ?? null);
    }
  }, [selectedBookId, visibleBooks]);

  const seriesSummary =
    activeSeries === "all" ? "全部目录" : catalogue.seriesMeta[activeSeries].label;

  const seriesDescription =
    activeSeries === "all"
      ? catalogue._meta.description
      : catalogue.seriesMeta[activeSeries].description;

  return (
    <>
      <Head>
        <title>考古工具目录</title>
        <meta
          name="description"
          content="考古文献目录，集中查看 PDF、Markdown 解析结果与 CSV 数据。"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className={sidebarCollapsed ? "shell is-sidebar-collapsed" : "shell"}>
        <button
          className="sidebar-tab"
          type="button"
          aria-expanded={!sidebarCollapsed}
          aria-controls="catalogue-sidebar"
          onClick={() => setSidebarCollapsed((current) => !current)}
        >
          <span>{sidebarCollapsed ? "展开目录" : "收起目录"}</span>
        </button>

        <aside className="sidebar fixed flex flex-col gap-6 p-7" id="catalogue-sidebar">
          <div className="brand">
            <p className="text-sm text-[var(--muted)]">考古工具 / 文献目录</p>
            <h1>考古库</h1>
          </div>

          <label className="search-field grid gap-2 text-[var(--muted)]">
            <span>检索标题、标签与摘要</span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="例如：战国 / 唐县 / 墓地"
            />
          </label>

          <div className="filters grid gap-2" aria-label="系列筛选">
            {seriesOrder.map((series) => {
              const isActive = activeSeries === series;
              const label = series === "all" ? "全部目录" : catalogue.seriesMeta[series].label;

              return (
                <button
                  key={series}
                  type="button"
                  className={`filter px-3 ${isActive ? "is-active" : ""}`}
                  data-series={series}
                  aria-pressed={isActive}
                  onClick={() => {
                    setActiveSeries(series);
                    setSeriesMenuOpen(false);
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>

          <div className="grid gap-2 text-sm text-[var(--muted)]">
            <span>当前范围</span>
            <p className="leading-6 text-[var(--ink)]">{seriesDescription}</p>
          </div>

          <div className="grid gap-2 text-sm text-[var(--muted)]">
            <span>目录概况</span>
            <p className="text-[var(--ink)]">
              {visibleBooks.length} / {catalogue.books.length} 册
            </p>
          </div>
        </aside>

        <main className="workspace">
          <section className="catalogue">
            <header className="section-heading sticky flex">
              <div className="grid gap-1">
                <h2 className="text-4xl font-normal text-[var(--ink)]">文献目录</h2>
                <p className="section-note relative">
                  {seriesSummary} · {visibleBooks.length} 册 · 更新于 {catalogue._meta.lastUpdated}
                </p>
              </div>

              <div className="series-picker">
                <button
                  type="button"
                  className="series-chip"
                  data-series={activeSeries}
                  aria-haspopup="true"
                  aria-expanded={seriesMenuOpen}
                  onClick={() => setSeriesMenuOpen((current) => !current)}
                >
                  {seriesSummary}
                </button>

                {seriesMenuOpen ? (
                  <div className="series-menu" role="menu">
                    {seriesOrder.map((series) => {
                      const isActive = activeSeries === series;
                      const label =
                        series === "all" ? "全部目录" : catalogue.seriesMeta[series].label;

                      return (
                        <button
                          key={series}
                          type="button"
                          role="menuitemradio"
                          aria-checked={isActive}
                          className={`series-option ${isActive ? "is-active" : ""}`}
                          data-series={series}
                          onClick={() => {
                            setActiveSeries(series);
                            setSeriesMenuOpen(false);
                          }}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            </header>

            <div className="book-list">
              {visibleBooks.length === 0 ? (
                <p className="empty-state">没有匹配结果，换一个地名、时代或遗址关键词试试。</p>
              ) : (
                visibleBooks.map((book) => {
                  const isSelected = selectedBookId === book.id;
                  const pdfUrl = buildAssetUrl(catalogue.baseUrls.pdf, book.filename);
                  const markdownUrl = buildAssetUrl(
                    catalogue.baseUrls.markdown,
                    book.markdownFilename,
                  );
                  const csvUrl = buildAssetUrl(catalogue.baseUrls.csv, book.csvFilename);

                  return (
                    <article
                      key={book.id}
                      className={`book-row ${isSelected ? "is-expanded" : ""}`}
                      data-series={book.series}
                    >
                      <button
                        type="button"
                        className={`book-card ${isSelected ? "is-selected" : ""}`}
                        onClick={() => setSelectedBookId(book.id)}
                        aria-pressed={isSelected}
                      >
                        <div className="grid gap-2">
                          <strong>{book.title}</strong>
                          <div className="book-meta">
                            {catalogue.seriesMeta[book.series].label} · {book.tags.join(" / ")}
                          </div>
                        </div>
                        <div className="book-meta">{book.description}</div>
                      </button>

                      <div className="book-node" aria-hidden="true" />

                      <div className="book-actions">
                        <a
                          className={`action-link${pdfUrl ? "" : " is-disabled"}`}
                          href={pdfUrl ?? undefined}
                          target="_blank"
                          rel="noreferrer"
                        >
                          原始 PDF
                        </a>
                        <div className="action-divider" />
                        <a
                          className={`action-link${markdownUrl ? "" : " is-disabled"}`}
                          href={markdownUrl ?? undefined}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Markdown
                        </a>
                        <a
                          className={`action-link${csvUrl ? "" : " is-disabled"}`}
                          href={csvUrl ?? undefined}
                          target="_blank"
                          rel="noreferrer"
                        >
                          CSV
                        </a>
                      </div>
                    </article>
                  );
                })
              )}
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
