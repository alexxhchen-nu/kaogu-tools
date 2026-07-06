"""
Single-file archaeological parser for tomb reports.
Combines the previous `app/parser/tomb_parser.py` and `app/parser/extractors.py` logic.
"""

import re
import json
import csv
import io
from typing import Optional, Dict, Union

try:
    import chonkie
except ImportError:  # pragma: no cover - optional dependency fallback
    chonkie = None


# Tomb type patterns
TOMB_TYPES = [
    "土坑竖穴砖椁墓", "梯形土坑竖穴墓", "长方形土坑竖穴墓", "土坑竖穴墓",
    "土坑洞室墓", "砖室墓", "舟形墓", "砖、石室墓", "石室墓",
    "土坑墓", "洞室墓", "竖穴土坑墓", "砖椁墓", "木椁墓", "崖墓", "土洞墓",
    "梯形土坑竖穴", "长方形土坑竖穴", "土坑竖穴",
]

# Dynasty keywords
DYNASTY_KEYWORDS = {
    '商': '商代', '周': '周代', '西周': '西周', '东周': '东周',
    '春秋': '春秋', '战国': '战国',
    '秦': '秦代', '汉': '汉代', '西汉': '西汉', '东汉': '东汉',
    '三国': '三国', '魏晋': '魏晋', '晋': '晋代',
    '南朝': '南朝', '北朝': '北朝', '十六国': '十六国',
    '隋': '隋代', '唐': '唐代', '五代': '五代',
    '宋': '宋代', '北宋': '北宋', '南宋': '南宋',
    '辽': '辽代', '金': '金代', '西夏': '西夏',
    '元': '元代', '明': '明代', '清': '清代',
    '近现代': '近现代', '现代': '近现代',
}


class WebTombParser:
    """In-memory parser with export utilities. No file I/O."""

    def __init__(self, report_name: str, content: str):
        self.report_name = report_name
        self.text = content
        self.lines = content.splitlines(keepends=True)
        self.tombs: list[dict] = []
        self.source_note = ""

    # ------------------------------------------------------------------
    # Tomb management
    # ------------------------------------------------------------------

    def add_tomb(self, tomb: dict):
        defaults = {
            "墓葬编号": "", "年代": "", "墓向": "", "墓葬形制": "",
            "墓口长": None, "墓口宽": None, "墓深": None,
            "发掘位置": "", "层位": "", "备注": "",
            "随葬器物": [], "schema_fields": {}
        }
        entry = {**defaults, **tomb}
        art_defaults = {
            "器物编号": "", "器物名称": "", "材质": "", "器型": "",
            "数量": 1, "特征描述": ""
        }
        entry["随葬器物"] = [
            {**art_defaults, **a} for a in entry.get("随葬器物", [])
        ]
        self.tombs.append(entry)

    def add_tombs(self, tombs: list[dict]):
        for t in tombs:
            self.add_tomb(t)

    # ------------------------------------------------------------------
    # Search helpers
    # ------------------------------------------------------------------

    def grep(self, pattern: str, flags=0) -> list[tuple[int, str]]:
        results = []
        for i, line in enumerate(self.lines):
            if re.search(pattern, line, flags):
                results.append((i + 1, line.rstrip()))
        return results

    def grep_context(self, pattern: str, before: int = 3, after: int = 10) -> list[str]:
        matches = []
        for i, line in enumerate(self.lines):
            if re.search(pattern, line):
                start = max(0, i - before)
                end = min(len(self.lines), i + after + 1)
                block = ''.join(self.lines[start:end])
                matches.append(block)
        return matches

    def get_section(self, start_line: int, end_line: int) -> str:
        return ''.join(self.lines[start_line - 1:end_line])

    # ------------------------------------------------------------------
    # Classification utilities
    # ------------------------------------------------------------------

    @staticmethod
    def classify_material(name: str) -> str:
        rules = [
            (['陶', '泥质', '灰陶', '红陶'], "陶器"),
            (['瓷', '白胎', '青花', '釉', '窑'], "瓷器"),
            (['铜', '青铜', '銅'], "青铜器"),
            (['铁', '鐵'], "铁器"),
            (['玉', '石', '玛瑙', '绿松石', '翡翠'], "玉石器"),
            (['骨', '角', '牙'], "骨角牙器"),
            (['漆', '木'], "漆木器"),
            (['金', '银'], "金银器"),
            (['钱', '币', '铢', '宝', '贝'], "货币"),
            (['料', '琉璃', '玻璃'], "料器"),
        ]
        for keywords, material in rules:
            if any(k in name for k in keywords):
                return material
        return "其他"

    @staticmethod
    def classify_vessel_type(name: str) -> str:
        types = {
            '罐': '罐', '壶': '壶', '瓶': '瓶', '盆': '盆', '碗': '碗',
            '盘': '盘', '杯': '杯', '尊': '尊', '罍': '罍', '瓮': '瓮',
            '鬲': '鬲', '豆': '豆', '簋': '簋', '爵': '爵', '斝': '斝',
            '觚': '觚', '鼎': '鼎', '洗': '洗', '炉': '炉', '灯': '灯',
            '枕': '枕', '碟': '碟', '盏': '盏', '缸': '缸', '盒': '盒',
            '戈': '戈', '矛': '矛', '剑': '剑', '刀': '刀', '镞': '镞',
            '戟': '戟', '弩机': '弩机',
            '斧': '斧', '锛': '锛', '凿': '凿', '铲': '铲', '锄': '锄',
            '镰': '镰', '纺轮': '纺轮', '锥': '锥',
            '璧': '璧', '琮': '琮', '璜': '璜', '玦': '玦', '环': '环',
            '串珠': '串珠', '珠': '串珠', '坠': '坠饰', '带钩': '带钩',
            '带扣': '带扣', '带饰': '带饰', '耳坠': '耳坠', '耳环': '耳环',
            '手镯': '手镯', '镯': '手镯', '簪': '簪', '钗': '簪',
            '扣': '扣饰', '铃': '铃', '鼓': '鼓', '磬': '磬',
            '印': '印章', '镜': '镜', '钱': '钱币', '币': '钱币',
            '俑': '俑', '案': '案', '台': '台',
        }
        for key, val in types.items():
            if key in name:
                return val
        return name

    @staticmethod
    def parse_num(s: str) -> Optional[Union[float, str]]:
        if not s:
            return None
        s = s.strip()
        if '~' in s:
            parts = s.split('~')
            try:
                return round((float(parts[0]) + float(parts[1])) / 2, 2)
            except ValueError:
                return s
        try:
            return float(s)
        except ValueError:
            return s

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 800) -> list[str]:
        """Split text into chunks using Chonkie when available, otherwise fall back to sentence-based splitting."""
        if chonkie is not None:
            try:
                splitter = chonkie.SemanticChunker()
                chunks = splitter.create(text)
                return [getattr(chunk, "text", str(chunk)) for chunk in chunks]
            except Exception:
                pass

        sentences = re.split(r'(?<=[。！？])\s+', text.strip())
        chunks = []
        current = ""
        for sentence in sentences:
            if not sentence:
                continue
            if len(current) + len(sentence) <= chunk_size:
                current = f"{current} {sentence}".strip()
            else:
                if current:
                    chunks.append(current)
                current = sentence
        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def discover_schema_fields(text: str) -> dict:
        """Discover field/value pairs from report text without hard-coding a fixed schema."""
        fields: Dict[str, str] = {}
        chunks = WebTombParser.chunk_text(text)

        for chunk in chunks:
            # 1) Explicit label/value pairs such as "字段名：值"
            for pattern in [
                r'([A-Za-z\u4e00-\u9fff]{2,12})\s*[:：]\s*([^\n\r；。]+)',
                r'([A-Za-z\u4e00-\u9fff]{2,12})\s*（([^）]+)）',
            ]:
                for m in re.finditer(pattern, chunk):
                    label = m.group(1).strip()
                    value = re.sub(r'\s+', '', m.group(2)).strip()
                    if label and value and len(value) <= 80:
                        fields[label] = value

            # 2) Weakly structured archaeology phrases without punctuation.
            for label in ["埋葬方式", "保存状态", "封土直径", "封土", "葬式", "墓室", "墓道", "墓主", "发掘位置", "层位"]:
                m = re.search(rf'{label}([^，。；、\n]+)', chunk)
                if m:
                    value = re.sub(r'\s+', '', m.group(1)).strip('：:，。；、')
                    if value:
                        fields[label] = value

            # 3) Dimension-like labels that appear in prose.
            for label, pattern in [
                ("墓口长", r'墓口长([0-9.]+(?:~[0-9.]+)?米?)'),
                ("墓口宽", r'墓口宽([0-9.]+(?:~[0-9.]+)?米?)'),
                ("墓深", r'墓深([0-9.]+(?:~[0-9.]+)?米?)'),
            ]:
                m = re.search(pattern, chunk)
                if m:
                    fields[label] = m.group(1)

        return fields

    @staticmethod
    def extract_dimensions(text: str) -> dict:
        result: Dict[str, Optional[Union[float, str]]] = {"墓口长": None, "墓口宽": None, "墓深": None}

        m = re.search(
            r'(?:南北)?长\s*([\d.]+)\s*[、，]\s*(?:东西)?宽\s*([\d.]+(?:~[\d.]+)?)\s*[、，]\s*(?:残)?深\s*([\d.]+(?:~[\d.]+)?)',
            text
        )
        if m:
            result["墓口长"] = WebTombParser.parse_num(m.group(1))
            result["墓口宽"] = WebTombParser.parse_num(m.group(2))
            result["墓深"] = WebTombParser.parse_num(m.group(3))
            return result

        m = re.search(
            r'(?:南北)?长\s*(?:约)?([\d.]+)\s*米',
            text
        )
        if m:
            result["墓口长"] = WebTombParser.parse_num(m.group(1))

        m_widths = re.findall(r'(?:头端|足端|东西)?宽\s*(?:约)?([\d.]+(?:~[\d.]+)?)\s*米?', text)
        if m_widths:
            vals = [WebTombParser.parse_num(w) for w in m_widths]
            nums = [v for v in vals if isinstance(v, (int, float))]
            if nums:
                result["墓口宽"] = round(sum(nums) / len(nums), 2)
            else:
                result["墓口宽"] = vals[0]
        else:
            m = re.search(r'(?:东西)?宽\s*([\d.]+(?:~[\d.]+)?)', text)
            if m:
                result["墓口宽"] = WebTombParser.parse_num(m.group(1))

        m = re.search(r'(?:残)?深\s*(?:约)?([\d.]+(?:~[\d.]+)?)\s*米?', text)
        if m:
            result["墓深"] = WebTombParser.parse_num(m.group(1))

        return result

    @staticmethod
    def extract_direction(text: str) -> str:
        for pattern in [
            r'方向\s*\$?\s*(\d+)\s*\^?\{?\\?circ\}?\s*\$?°?',
            r'方向\s*(\d+)\s*°',
            r'方向\s*(\d+)(?=[。，,\s])',
            r'方向\s*(南北向|东西向|南向|北向|东向|西向)',
        ]:
            m = re.search(pattern, text)
            if m:
                val = m.group(1)
                return f"{val}°" if val.isdigit() else val
        return ""

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def sort_tombs(self):
        def key(t):
            id_str = t['墓葬编号']
            m = re.search(r'(\d+)$', id_str)
            if m:
                prefix = re.sub(r'\d+$', '', id_str) or 'Z'
                return (prefix, int(m.group(1)))
            return (id_str, 0)
        self.tombs.sort(key=key)

    # ------------------------------------------------------------------
    # Export methods (return strings/bytes, no file I/O)
    # ------------------------------------------------------------------

    def to_json(self) -> dict:
        self.sort_tombs()
        return {
            "墓葬列表": self.tombs,
            "原始文本片段": self.source_note or f"来源：{self.report_name}，共提取{len(self.tombs)}座墓葬"
        }

    def to_json_string(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False, indent=2)

    def to_csv_string(self) -> str:
        self.sort_tombs()
        output = io.StringIO()
        headers = [
            "墓葬编号", "年代", "墓向", "墓葬形制", "墓口长", "墓口宽", "墓深",
            "发掘位置", "层位", "备注",
            "器物编号", "器物名称", "材质", "器型", "数量", "特征描述"
        ]
        w = csv.writer(output)
        w.writerow(headers)
        for t in self.tombs:
            base = [
                t.get(k, '') for k in [
                    '墓葬编号', '年代', '墓向', '墓葬形制',
                    '墓口长', '墓口宽', '墓深', '发掘位置', '层位', '备注'
                ]
            ]
            arts = t.get('随葬器物', [])
            if arts:
                for a in arts:
                    row = base + [a.get(k, '') for k in [
                        '器物编号', '器物名称', '材质', '器型', '数量', '特征描述'
                    ]]
                    w.writerow(row)
            else:
                w.writerow(base + [''] * 6)
        return '\ufeff' + output.getvalue()

    def to_markdown_string(self) -> str:
        self.sort_tombs()
        parts = []
        parts.append(f"# 墓葬数据 — {self.report_name}\n")
        parts.append(f"共提取 **{len(self.tombs)}** 条墓葬记录\n")

        parts.append("## 概览\n")
        parts.append("| 墓葬编号 | 年代 | 形制 | 尺寸(长×宽×深) | 随葬品数 |")
        parts.append("|----------|------|------|----------------|----------|")
        for t in self.tombs:
            dim = ""
            l = t.get('墓口长')
            w = t.get('墓口宽')
            d = t.get('墓深')
            if l or w:
                dim = f"{l or ''}×{w or ''}×{d or ''}m"
            parts.append(
                f"| {t['墓葬编号']} | {t.get('年代', '')} | "
                f"{t.get('墓葬形制', '')} | {dim} | "
                f"{len(t.get('随葬器物', []))} |"
            )

        parts.append("\n## 详细记录\n")
        for t in self.tombs:
            parts.append(f"### {t['墓葬编号']}\n")
            for label in ['年代', '墓向', '墓葬形制', '墓口长', '墓口宽',
                          '墓深', '发掘位置', '层位', '备注']:
                val = t.get(label, '')
                if val:
                    parts.append(f"- **{label}**: {val}")
            arts = t.get('随葬器物', [])
            if arts:
                parts.append(f"\n**随葬器物** ({len(arts)}件)\n")
                parts.append("| 编号 | 名称 | 材质 | 器型 | 数量 | 特征描述 |")
                parts.append("|------|------|------|------|------|----------|")
                for a in arts:
                    desc = a.get('特征描述', '')
                    if len(desc) > 80:
                        desc = desc[:80] + '...'
                    parts.append(
                        f"| {a.get('器物编号', '')} | {a.get('器物名称', '')} | "
                        f"{a.get('材质', '')} | {a.get('器型', '')} | "
                        f"{a.get('数量', '')} | {desc} |"
                    )
            parts.append("")

        return '\n'.join(parts)


def detect_report_type(content: str) -> str:
    """Detect whether the report is tomb-focused or a site report."""
    lines = content.splitlines(keepends=True)

    tomb_header_count = 0
    for line in lines:
        stripped = line.lstrip()
        if re.match(r'^#{1,3}\s*(?:[一二三四五六七八九十百千]+[、．.\s]+\s*)?(?:\d+[、．.\s]+\s*)?(M\s*\d+)\b', stripped):
            tomb_header_count += 1

    desc_count = len(re.findall(r'M\s*\d+\s*位于', content))

    if tomb_header_count >= 1 or desc_count >= 1:
        return "tomb_focused"

    prefixed = len(re.findall(r'[A-Z]+M\d+', content))
    if prefixed >= 5:
        return "prefixed_ids"

    return "site_report"


def detect_dynasty_chapters(content: str) -> list[tuple[int, int, str]]:
    """Detect dynasty chapter boundaries from headers."""
    lines = content.splitlines(keepends=True)
    chapters = []

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        m = re.match(r'^#+\s*第([二三四五六七八九十百]+)章', stripped)
        if m:
            chapter_num = m.group(1)
            dynasty = ""
            nearby = ' '.join(lines[i:min(i+3, len(lines))])
            for kw, name in DYNASTY_KEYWORDS.items():
                if kw in nearby:
                    dynasty = name
                    break
            chapters.append((i + 1, chapter_num, dynasty))

    result = []
    for idx, (start, num, dynasty) in enumerate(chapters):
        if idx + 1 < len(chapters):
            end = chapters[idx + 1][0] - 1
        else:
            end = len(lines)
        result.append((start, end, dynasty))

    return result


def get_dynasty_from_context(line_num: int, chapters: list[tuple[int, int, str]]) -> str:
    """Get dynasty for a given line number based on chapter boundaries."""
    for start, end, dynasty in chapters:
        if start <= line_num <= end:
            return dynasty
    return ""


def extract_tomb_type(text: str) -> str:
    """Extract tomb type from description text."""
    text_no_space = text.replace(' ', '')
    for t in TOMB_TYPES:
        if t in text_no_space:
            return t
    return ""


def extract_artifacts_from_desc(text: str, tomb_id: str) -> list[dict]:
    """Extract artifacts from tomb description paragraph."""
    artifacts = []
    if '无随葬品' in text or '未发现' in text and '随葬品' in text:
        return artifacts

    m = re.search(r'随葬品有(.+?)(?:$|(?:图\d|图版))', text, re.DOTALL)
    if m:
        desc = m.group(1)
    else:
        desc = text

    SKIP_WORDS = {'随葬', '随葬品', '随葬品为', '随葬品有', '随葬品共', '随葬的',
                  '墓主', '其中', '口含', '放置', '出土', '发现', '位于',
                  '品为', '品有', '品共', '的', '左侧', '右侧', '足部', '头部',
                  '足端', '头端', '保存', '较差', '较好', '墓底', '墓口'}

    seen_names = set()

    for m in re.finditer(r'(\d+)\s*(?:件|枚|把|具|颗|面)\s*([\u4e00-\u9fff]{2,5}?)(?=[，。；、（(）)图版\s\n]|位于|置于|放|在|墓|$)', desc):
        name = m.group(2).strip()
        count = int(m.group(1))
        if not name or name in SKIP_WORDS or name in seen_names:
            continue
        if not (WebTombParser.classify_material(name) != '其他' or
                WebTombParser.classify_vessel_type(name) != name):
            continue
        seen_names.add(name)
        artifacts.append({
            "器物编号": f"{tomb_id}:{len(artifacts)+1}",
            "器物名称": name,
            "材质": WebTombParser.classify_material(name),
            "器型": WebTombParser.classify_vessel_type(name),
            "数量": count,
            "特征描述": ""
        })

    for m in re.finditer(r'([\u4e00-\u9fff]{2,6})\s*(\d+)\s*(?:件|枚|把|具|颗)', desc):
        name = m.group(1).strip()
        name = re.sub(r'^(?:其中|随葬|出土)', '', name)
        name = name.strip()
        count = int(m.group(2))
        if not name or name in SKIP_WORDS or name in seen_names:
            continue
        if not (WebTombParser.classify_material(name) != '其他' or
                WebTombParser.classify_vessel_type(name) != name):
            continue
        seen_names.add(name)
        artifacts.append({
            "器物编号": f"{tomb_id}:{len(artifacts)+1}",
            "器物名称": name,
            "材质": WebTombParser.classify_material(name),
            "器型": WebTombParser.classify_vessel_type(name),
            "数量": count,
            "特征描述": ""
        })

    return artifacts


def extract_detailed_artifacts(text: str, tomb_id: str) -> list[dict]:
    """Extract detailed artifact descriptions."""
    artifacts = []
    pattern = r'^([\u4e00-\u9fff]+)\s+(\d+)\s*件[。.]?\s*(?:（(M\d+:\d+(?:-\d+)?)）)?\s*(.+?)(?=\n\n|\n<|\n##|\Z)'

    for m in re.finditer(pattern, text, re.MULTILINE | re.DOTALL):
        name = m.group(1)
        name = re.sub(r'^其中', '', name)
        count = int(m.group(2))
        item_id = m.group(3) if m.group(3) else f"{tomb_id}:{len(artifacts)+1}"
        desc = m.group(4).strip()
        desc = re.sub(r'图\s*[\d-]+', '', desc)
        desc = re.sub(r'图版\s*[\d-]+', '', desc)
        desc = desc.strip()

        artifacts.append({
            "器物编号": item_id,
            "器物名称": name,
            "材质": WebTombParser.classify_material(name),
            "器型": WebTombParser.classify_vessel_type(name),
            "数量": count,
            "特征描述": desc[:200] if desc else ""
        })

    return artifacts


def parse_tomb_focused(parser: WebTombParser, content: str) -> None:
    """Parse a tomb-focused report with M+number headers."""
    lines = content.splitlines(keepends=True)
    chapters = detect_dynasty_chapters(content)

    tomb_headers = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        m = re.match(r'^#{1,3}\s*(?:[一二三四五六七八九十百千]+[、．.\s]+\s*)?(?:\d+[、．.\s]+\s*)?(M\s*\d+)\b', stripped)
        if m:
            tomb_id = m.group(1).replace(' ', '')
            tomb_headers.append((i + 1, tomb_id))

    for idx, (line_num, tomb_id) in enumerate(tomb_headers):
        start_line = line_num - 1
        if idx + 1 < len(tomb_headers):
            end_line = tomb_headers[idx + 1][0] - 1
        else:
            end_line = len(lines)

        tomb_text = ''.join(lines[start_line:end_line])
        tomb_text_clean = re.sub(r'<div[^>]*>.*?</div>', ' ', tomb_text, flags=re.DOTALL)
        tomb_text_clean = re.sub(r'\s+', ' ', tomb_text_clean)

        dynasty = get_dynasty_from_context(line_num, chapters)

        if not dynasty:
            for kw, name in DYNASTY_KEYWORDS.items():
                if kw in tomb_text[:200]:
                    dynasty = name
                    break

        desc_match = re.search(r'(M\s*\d+\s*位于.+?(?:图\s*[\d-]+[）\)]))', tomb_text_clean, re.DOTALL)
        if not desc_match:
            desc_match = re.search(r'(M\s*\d+\s*位于.+?)(?=\n##|\n<div|\n\n\n|\Z)', tomb_text, re.DOTALL)

        if not desc_match:
            parser.add_tomb({
                "墓葬编号": tomb_id,
                "年代": dynasty,
                "备注": "描述未找到",
            })
            continue

        desc = desc_match.group(1)
        direction = WebTombParser.extract_direction(desc)
        tomb_type = extract_tomb_type(tomb_text_clean)
        dims = WebTombParser.extract_dimensions(desc)
        schema_fields = WebTombParser.discover_schema_fields(tomb_text)

        notes = []
        if '被盗' in desc or '盗扰' in desc:
            notes.append("盗扰")
        if '迁葬' in desc:
            notes.append("迁葬")
        if '合葬' in desc:
            notes.append("合葬")
        if '打破' in desc:
            notes.append("被打破")

        artifacts = extract_artifacts_from_desc(desc, tomb_id)
        detailed = extract_detailed_artifacts(tomb_text, tomb_id)
        if detailed and not artifacts:
            artifacts = detailed
        elif detailed:
            detailed_dict = {a['器物名称']: a for a in detailed}
            for a in artifacts:
                if a['器物名称'] in detailed_dict:
                    d = detailed_dict[a['器物名称']]
                    if d['特征描述'] and not a['特征描述']:
                        a['特征描述'] = d['特征描述']
                    if d['器物编号'] and ':' in d['器物编号']:
                        a['器物编号'] = d['器物编号']

        tomb_payload = {
            "墓葬编号": tomb_id,
            "年代": dynasty,
            "墓向": direction,
            "墓葬形制": tomb_type,
            "墓口长": dims["墓口长"],
            "墓口宽": dims["墓口宽"],
            "墓深": dims["墓深"],
            "发掘位置": "",
            "层位": "",
            "备注": "；".join(notes) if notes else "",
            "随葬器物": artifacts,
            "schema_fields": schema_fields,
        }
        parser.add_tomb(tomb_payload)


def parse_prefixed_ids(parser: WebTombParser, content: str) -> None:
    """Parse reports with prefixed tomb IDs (e.g., YSTG4AM1)."""
    lines = content.splitlines(keepends=True)
    tomb_pattern = re.compile(r'([A-Z]+M(\d+))')
    seen_ids = set()

    for i, line in enumerate(lines):
        for m in tomb_pattern.finditer(line):
            full_id = m.group(1)
            if full_id in seen_ids:
                continue
            seen_ids.add(full_id)

            start = max(0, i - 2)
            end = min(len(lines), i + 8)
            context = ''.join(lines[start:end])

            direction = WebTombParser.extract_direction(context)
            tomb_type = extract_tomb_type(context)
            dims = WebTombParser.extract_dimensions(context)

            dynasty = ""
            for kw, name in DYNASTY_KEYWORDS.items():
                if kw in context[:300]:
                    dynasty = name
                    break

            schema_fields = WebTombParser.discover_schema_fields(context)
            parser.add_tomb({
                "墓葬编号": full_id,
                "年代": dynasty,
                "墓向": direction,
                "墓葬形制": tomb_type,
                "墓口长": dims["墓口长"],
                "墓口宽": dims["墓口宽"],
                "墓深": dims["墓深"],
                "备注": "",
                "schema_fields": schema_fields,
            })


def parse_site_report(parser: WebTombParser, content: str) -> None:
    """Parse site reports where tombs are mentioned incidentally."""
    lines = content.splitlines(keepends=True)
    seen_ids = set()

    for i, line in enumerate(lines):
        for m in re.finditer(r'\b(M\s*(\d+))\b', line):
            tomb_id = m.group(1).replace(' ', '')
            if tomb_id in seen_ids:
                continue
            seen_ids.add(tomb_id)

            start = max(0, i - 2)
            end = min(len(lines), i + 6)
            context = ''.join(lines[start:end])

            direction = WebTombParser.extract_direction(context)
            tomb_type = extract_tomb_type(context)
            dims = WebTombParser.extract_dimensions(context)

            dynasty = ""
            for kw, name in DYNASTY_KEYWORDS.items():
                if kw in context[:300]:
                    dynasty = name
                    break

            artifacts = extract_artifacts_from_desc(context, tomb_id)
            schema_fields = WebTombParser.discover_schema_fields(context)
            parser.add_tomb({
                "墓葬编号": tomb_id,
                "年代": dynasty,
                "墓向": direction,
                "墓葬形制": tomb_type,
                "墓口长": dims["墓口长"],
                "墓口宽": dims["墓口宽"],
                "墓深": dims["墓深"],
                "备注": "",
                "随葬器物": artifacts,
                "schema_fields": schema_fields,
            })

    for i, line in enumerate(lines):
        m = re.search(r'(现代|近现代).*?(\d+)\s*座', line)
        if m:
            dynasty = m.group(1)
            count = int(m.group(2))
            parser.add_tomb({
                "墓葬编号": f"{dynasty}墓葬群",
                "年代": "近现代",
                "备注": f"报告记载共发现{count}座墓葬",
            })


def auto_parse(report_name: str, content: str) -> WebTombParser:
    """Main entry point: auto-detect report type and parse."""
    content = re.sub(r'<div[^>]*>.*?</div>', ' ', content, flags=re.DOTALL)

    lines = content.split('\n')
    merged = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            merged.append('')
            continue
        if merged:
            prev = merged[-1].rstrip()
            if prev and re.search(r'[\d.~]$', prev) and re.match(r'^[米厘米毫寸尺丈]', stripped):
                merged[-1] = prev + stripped
                continue
            if prev and re.search(r'[\d]$', prev) and re.match(r'^[，、。；：的和及与米]', stripped):
                merged[-1] = prev + stripped
                continue
        merged.append(line)
    content = '\n'.join(merged)

    parser = WebTombParser(report_name, content)
    report_type = detect_report_type(content)

    if report_type == "tomb_focused":
        parse_tomb_focused(parser, content)
    elif report_type == "prefixed_ids":
        parse_prefixed_ids(parser, content)
    else:
        parse_site_report(parser, content)

    parser.sort_tombs()

    total_artifacts = sum(len(t.get('随葬器物', [])) for t in parser.tombs)
    parser.source_note = (
        f"来源：{report_name}，"
        f"共提取{len(parser.tombs)}座墓葬，"
        f"{total_artifacts}件随葬器物。"
        f"报告类型：{report_type}"
    )

    return parser
