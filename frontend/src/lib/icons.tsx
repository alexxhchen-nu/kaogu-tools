import type { ReactElement, ReactNode, SVGProps } from "react"

export type IconComponent = (props: SVGProps<SVGSVGElement>) => ReactElement

function IconBase({
  children,
  ...props
}: SVGProps<SVGSVGElement> & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={props.strokeWidth ?? 1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  )
}

export function ArrowRight(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </IconBase>
  )
}

export function Box(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" />
      <path d="m4 7.5 8 4.5 8-4.5" />
      <path d="M12 12v9" />
    </IconBase>
  )
}

export function Braces(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M8 4c-2 0-3 1-3 3v2c0 1-.6 1.8-1.5 2 .9.2 1.5 1 1.5 2v2c0 2 1 3 3 3" />
      <path d="M16 4c2 0 3 1 3 3v2c0 1 .6 1.8 1.5 2-.9.2-1.5 1-1.5 2v2c0 2-1 3-3 3" />
    </IconBase>
  )
}

export function ChevronRight(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="m9 18 6-6-6-6" />
    </IconBase>
  )
}

export function FileText(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z" />
      <path d="M14 3v6h6" />
      <path d="M8 13h8" />
      <path d="M8 17h6" />
    </IconBase>
  )
}

export function FileUp(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z" />
      <path d="M14 3v6h6" />
      <path d="M12 17V11" />
      <path d="m9 14 3-3 3 3" />
    </IconBase>
  )
}

export function Loader2(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M21 12a9 9 0 1 1-6.2-8.56" />
    </IconBase>
  )
}

export function MapPinned(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M9 18 3 21V6l6-3 6 3 6-3v15l-6 3-6-3Z" />
      <path d="M9 3v15" />
      <path d="M15 6v15" />
      <path d="M12 8.5c0 2.5 3 5.5 3 5.5s3-3 3-5.5a3 3 0 0 0-6 0Z" />
      <path d="M15 8.5h.01" />
    </IconBase>
  )
}

export function Play(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="m8 5 11 7-11 7V5Z" />
    </IconBase>
  )
}

export function Scissors(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="m14 10 7-7" />
      <path d="m14 14 7 7" />
      <circle cx="5" cy="7" r="3" />
      <circle cx="5" cy="17" r="3" />
      <path d="m8 8 4 4-4 4" />
    </IconBase>
  )
}

export function Search(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </IconBase>
  )
}

export function Send(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="m22 2-7 20-4-9-9-4 20-7Z" />
      <path d="M22 2 11 13" />
    </IconBase>
  )
}

export function TerminalSquare(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="m7 9 3 3-3 3" />
      <path d="M13 15h4" />
    </IconBase>
  )
}
