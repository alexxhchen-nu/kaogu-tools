export interface ToolRunResponse {
  ok: boolean
  message?: string
  data?: unknown
}

export function resolveEndpoint(endpoint: string) {
  const base = (
    process.env.NEXT_PUBLIC_KAOGU_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    ''
  ).replace(/\/$/, '')

  if (!base || endpoint.startsWith('http')) return endpoint
  return `${base}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`
}

async function parseResponse(res: Response): Promise<ToolRunResponse> {
  const contentType = res.headers.get('content-type') ?? ''
  const payload = contentType.includes('application/json')
    ? await res.json().catch(() => null)
    : await res.text().catch(() => '')

  if (!res.ok) {
    const message =
      typeof payload === 'object' && payload && 'detail' in payload
        ? String(payload.detail)
        : `请求失败：${res.status}`
    throw new Error(message)
  }

  return {
    ok: true,
    data: payload,
  }
}

export async function runJsonTool(endpoint: string, input: unknown) {
  const res = await fetch(resolveEndpoint(endpoint), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })

  return parseResponse(res)
}

export async function runFileTool(endpoint: string, file: File) {
  const body = new FormData()
  body.append('file', file)

  const res = await fetch(resolveEndpoint(endpoint), {
    method: 'POST',
    body,
  })

  return parseResponse(res)
}
