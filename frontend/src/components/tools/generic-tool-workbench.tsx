'use client'

import type { ReactNode, RefObject } from 'react'
import { useRef, useState } from 'react'
import {
  Braces,
  FileUp,
  Loader2,
  Play,
  Search,
  Send,
  TerminalSquare,
} from '@/lib/icons'
import { runFileTool, runJsonTool } from '@/lib/api-client'
import type { ToolInputMode, ToolMeta } from '@/lib/tools'
import { cn } from '@/lib/utils'

type RunState = 'idle' | 'loading' | 'done' | 'error'
type WorkbenchTool = Omit<ToolMeta, 'icon'>

export function GenericToolWorkbench({ tool }: { tool: WorkbenchTool }) {
  const [input, setInput] = useState(tool.exampleInput)
  const [file, setFile] = useState<File | null>(null)
  const [state, setState] = useState<RunState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<unknown>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function run() {
    setState('loading')
    setError(null)
    setResult(null)

    try {
      const response =
        tool.inputMode === 'file'
          ? await runFileToolWithSelection()
          : await runJsonTool(tool.endpoint, buildPayload(tool.inputMode, input))

      setResult(response.data)
      setState('done')
    } catch (err) {
      setError(err instanceof Error ? err.message : '工具运行失败。')
      setState('error')
    }
  }

  async function runFileToolWithSelection() {
    if (!file) {
      throw new Error('请先选择一个文件。')
    }
    return runFileTool(tool.endpoint, file)
  }

  const Icon =
    tool.inputMode === 'file'
      ? FileUp
      : tool.inputMode === 'json'
        ? Braces
        : tool.inputMode === 'query'
          ? Search
          : TerminalSquare

  return (
    <div className="tool-workbench">
      <section className="tool-panel">
        <div className="tool-panel-heading">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center border border-foreground">
            <Icon className="h-5 w-5" strokeWidth={1.7} />
          </span>
          <div>
            <h2 className="font-serif text-xl font-black">输入</h2>
            <p className="mt-1 text-sm leading-7 text-foreground/70">
              这里保留通用交互逻辑。把 endpoint 接到你的真实函数后，就可以替换下方示例输入或定制专用控件。
            </p>
          </div>
        </div>

        <div className="tool-input-body">
          {tool.inputMode === 'file' ? (
            <FileInput
              acceptedTypes={tool.acceptedTypes}
              file={file}
              onPick={() => fileInputRef.current?.click()}
              onFile={setFile}
              refEl={fileInputRef}
            />
          ) : (
            <TextInput mode={tool.inputMode} value={input} onChange={setInput} />
          )}
        </div>

        <div className="tool-endpoint">
          <p className="text-xs font-black text-foreground/60">
            接口路径
          </p>
          <code className="mt-1 block break-all font-mono text-sm text-foreground">
            {tool.endpoint}
          </code>
        </div>

        <button
          onClick={run}
          disabled={state === 'loading'}
          className="tool-run-button"
        >
          {state === 'loading' ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : tool.inputMode === 'query' ? (
            <Search className="h-4 w-4" />
          ) : tool.inputMode === 'text' ? (
            <Send className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          运行工具
        </button>
      </section>

      <section className="tool-panel">
        <div className="tool-panel-heading">
          <div>
            <h2 className="font-serif text-xl font-black">结果</h2>
            <p className="mt-1 text-sm leading-7 text-foreground/70">
              {tool.resultHint}
            </p>
          </div>
        </div>

        <div className="tool-result-body">
          {state === 'idle' && (
            <EmptyState text="运行工具后，后端返回的数据会显示在这里。" />
          )}

          {state === 'loading' && (
            <EmptyState
              text="正在等待后端返回结果..."
              icon={<Loader2 className="h-5 w-5 animate-spin" />}
            />
          )}

          {state === 'error' && error && (
            <div className="border border-accent bg-background p-4 text-sm text-accent">
              {error}
              <p className="mt-2 text-xs leading-6 text-foreground/70">
                如果后端还没接入，这是正常的。保留当前 endpoint，等你的 Python 或 API 服务实现对应路由即可。
              </p>
            </div>
          )}

          {state === 'done' && (
            <pre className="tool-result-output">
              {formatResult(result)}
            </pre>
          )}
        </div>
      </section>
    </div>
  )
}

function buildPayload(mode: ToolInputMode, input: string) {
  if (mode === 'json') {
    return JSON.parse(input)
  }

  if (mode === 'query') {
    return { query: input }
  }

  return { text: input }
}

function formatResult(result: unknown) {
  if (typeof result === 'string') return result
  return JSON.stringify(result, null, 2)
}

function FileInput({
  acceptedTypes,
  file,
  onPick,
  onFile,
  refEl,
}: {
  acceptedTypes?: string
  file: File | null
  onPick: () => void
  onFile: (file: File) => void
  refEl: RefObject<HTMLInputElement | null>
}) {
  return (
    <div
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault()
        const dropped = e.dataTransfer.files?.[0]
        if (dropped) onFile(dropped)
      }}
      onClick={onPick}
      className="file-dropzone"
    >
      <FileUp className="h-8 w-8" strokeWidth={1.6} />
      <p className="mt-4 font-serif text-base font-black">
        {file ? file.name : '点击或拖拽文件到这里'}
      </p>
      <p className="mt-1 text-sm text-foreground/60">
        {file
          ? `${(file.size / 1024 / 1024).toFixed(2)} MB`
          : acceptedTypes ?? '按你的后端能力配置格式'}
      </p>
      <input
        ref={refEl}
        type="file"
        accept={acceptedTypes}
        className="hidden"
        onChange={(e) => {
          const picked = e.target.files?.[0]
          if (picked) onFile(picked)
        }}
      />
    </div>
  )
}

function TextInput({
  mode,
  value,
  onChange,
}: {
  mode: ToolInputMode
  value: string
  onChange: (value: string) => void
}) {
  const isJson = mode === 'json'

  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      spellCheck={false}
      className={cn(
        'tool-textarea',
        isJson && 'font-mono text-xs',
      )}
    />
  )
}

function EmptyState({
  text,
  icon,
}: {
  text: string
  icon?: ReactNode
}) {
  return (
    <div className="tool-empty-state">
      {icon ?? <TerminalSquare className="h-5 w-5" strokeWidth={1.5} />}
      <p className="mt-3">{text}</p>
    </div>
  )
}
