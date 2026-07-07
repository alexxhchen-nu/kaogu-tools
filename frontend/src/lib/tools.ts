import { Box, Braces, FileText, MapPinned, Search } from "@/lib/icons"
import type { IconComponent } from "@/lib/icons"

export type ToolInputMode = 'file' | 'text' | 'json' | 'query'

export interface ToolMeta {
  slug: string
  href: string
  name: string
  en: string
  tagline: string
  description: string
  icon: IconComponent
  endpoint: string
  inputMode: ToolInputMode
  acceptedTypes?: string
  exampleInput: string
  resultHint: string
  index: string
}

export const TOOLS: ToolMeta[] = [
  {
    slug: 'ocr',
    href: '/OCR',
    name: '考古文献解析',
    en: '文献解析工作台',
    tagline: '上传 PDF 或图片，提取结构、图表与关键信息',
    description:
      '面向发掘报告、简报、图录与扫描件的解析入口。前端负责上传、任务状态和结果预览，后端可以接入 OCR、版面分析、表格抽取或大模型结构化流程。',
    icon: FileText,
    endpoint: '/ocr/parse',
    inputMode: 'file',
    acceptedTypes: '.pdf,image/*',
    exampleInput: '上传一份考古报告 PDF 或扫描图片',
    resultHint: '建议返回 Markdown、结构化 JSON、图片/表格清单与可下载产物链接。',
    index: '一',
  },
  {
    slug: 'library',
    href: '/Library',
    name: '资料库检索',
    en: '资料目录工作台',
    tagline: '跨文献、遗址、墓葬与器物记录进行统一检索',
    description:
      '集中浏览已整理的考古文献目录，直接打开 PDF、Markdown 解析结果与 CSV 数据。这个入口保留原有目录功能，同时套入新的门户导航。',
    icon: Search,
    endpoint: '/library/search',
    inputMode: 'query',
    exampleInput: '战国 唐县 墓地',
    resultHint: '目录页本身已经提供本地筛选；如接入后端，可返回命中记录、来源片段、筛选项和详情页链接。',
    index: '二',
  },
  {
    slug: 'dynamic-parser',
    href: '/DynamicParser',
    name: '墓葬文本抽取',
    en: '文本抽取工作台',
    tagline: '从报告文本中抽取墓葬、器物与尺寸字段',
    description:
      '对应 backend/dynamic_parser.py 的结构化抽取能力。适合粘贴 OCR 后的 Markdown、简报正文或墓葬段落，输出可继续建模或制表的 JSON/CSV 数据。',
    icon: Braces,
    endpoint: '/dynamic-parser/parse',
    inputMode: 'text',
    exampleInput: 'M1，长方形竖穴土坑墓。墓口长3.4、宽1.8、深2.1米，随葬陶罐1件。',
    resultHint: '建议返回墓葬编号、年代、形制、尺寸、墓向、随葬器物和 parser 置信说明。',
    index: '三',
  },
  {
    slug: 'modelling',
    href: '/Modelling',
    name: '墓葬三维建模',
    en: '三维建模工作台',
    tagline: '输入墓葬形制与尺寸，生成可检查的三维模型',
    description:
      '为墓葬结构数据、CSV 或人工录入参数预留的建模入口。后端可以生成 Three.js 场景配置、GLB 文件、剖面图或校验报告。',
    icon: Box,
    endpoint: '/modelling/generate',
    inputMode: 'file',
    acceptedTypes: '.csv,text/csv',
    exampleInput: '上传包含墓葬编号、墓葬形制、墓口长、墓口宽、墓深等列的 CSV 文件',
    resultHint: '建议返回模型 URL、场景 JSON、尺寸校验、风险提示与预览截图。',
    index: '四',
  },
  {
    slug: 'gis',
    href: '/GIS',
    name: '遗址空间分析',
    en: '空间分析工作台',
    tagline: '把地名、坐标和遗址属性转成可探索地图',
    description:
      '为 GIS、地点消歧、路线和空间聚类分析预留的交互入口。适合接 GeoJSON、地图瓦片、行政区划和自定义空间分析服务。',
    icon: MapPinned,
    endpoint: '/gis/generate',
    inputMode: 'file',
    acceptedTypes: '.csv,text/csv',
    exampleInput: '上传包含遗址、墓葬、坐标或地点字段的 CSV 文件',
    resultHint: '建议返回 GeoJSON、地点匹配置信度、地图视图范围和未匹配地名。',
    index: '五',
  },
]

export function getTool(slug: string): ToolMeta | undefined {
  return TOOLS.find((t) => t.slug === slug)
}
