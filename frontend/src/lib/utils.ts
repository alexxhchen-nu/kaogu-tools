export type ClassValue =
  | string
  | number
  | false
  | null
  | undefined
  | Record<string, boolean | null | undefined>
  | ClassValue[]

export function cn(...inputs: ClassValue[]) {
  return inputs.flatMap(normalizeClassValue).filter(Boolean).join(" ")
}

function normalizeClassValue(input: ClassValue): string[] {
  if (!input) {
    return []
  }

  if (Array.isArray(input)) {
    return input.flatMap(normalizeClassValue)
  }

  if (typeof input === "object") {
    return Object.entries(input)
      .filter(([, enabled]) => Boolean(enabled))
      .map(([className]) => className)
  }

  return [String(input)]
}
