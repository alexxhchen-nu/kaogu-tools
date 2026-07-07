export function SiteFooter() {
  return (
    <footer className="bg-background">
      <div className="mx-auto flex max-w-[var(--site-max-width)] flex-col gap-3 px-[var(--site-gutter)] pb-7 pt-3 text-xs text-foreground/60 sm:flex-row sm:items-center sm:justify-between">
        <p>
          © 2026 考古工具箱
        </p>
        <p>
          数据仅供演示与教学之用，不代表正式考古结论。
        </p>
      </div>
    </footer>
  )
}
