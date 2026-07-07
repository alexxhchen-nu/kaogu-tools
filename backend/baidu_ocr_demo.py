#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import requests


TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".pnm", ".webp"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | {".pdf"}
OCR_ENDPOINTS = {
    "general_basic": "/rest/2.0/ocr/v1/general_basic",
    "accurate_basic": "/rest/2.0/ocr/v1/accurate_basic",
    "general": "/rest/2.0/ocr/v1/general",
    "accurate": "/rest/2.0/ocr/v1/accurate",
    "handwriting": "/rest/2.0/ocr/v1/handwriting",
    "table": "/rest/2.0/ocr/v1/table",
    "doc_analysis_office": "/rest/2.0/ocr/v1/doc_analysis_office",
    "ancient": "/rest/2.0/ocr/v1/ancient",
}
DEFAULT_RELEVANT_MODES = [
    "accurate_basic",
    "general",
    "handwriting",
    "table",
    "ancient",
]


class BaiduOCRClient:
    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        app_id: str | None = None,
        dpi: int = 200,
        timeout: int = 60,
        mode: str = "accurate_basic",
    ) -> None:
        self.api_key = api_key or self._get_required_env("BAIDU_OCR_API_KEY")
        self.secret_key = secret_key or self._get_required_env("BAIDU_OCR_SECRET_KEY")
        self.app_id = app_id or os.getenv("BAIDU_OCR_APP_ID", "")
        self.dpi = dpi
        self.timeout = timeout
        self.mode = mode
        self.endpoint = self._resolve_endpoint(mode)

    @staticmethod
    def _get_required_env(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"缺少环境变量: {name}")
        return value

    @staticmethod
    def _resolve_endpoint(mode: str) -> str:
        endpoint = OCR_ENDPOINTS.get(mode)
        if not endpoint:
            raise ValueError(f"不支持的 OCR 模式: {mode}")
        return f"https://aip.baidubce.com{endpoint}"

    def get_access_token(self) -> str:
        response = requests.get(
            TOKEN_URL,
            params={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"获取 access_token 失败: {json.dumps(data, ensure_ascii=False)}")
        return token

    def validate_input(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"文件不存在: {path}")
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {path.suffix}")

    def render_pdf_pages(self, pdf_path: Path) -> list[Path]:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("解析 PDF 需要安装 PyMuPDF：uv pip install pymupdf") from exc

        output_dir = Path(tempfile.mkdtemp(prefix="baidu_ocr_pdf_pages_"))
        pages: list[Path] = []

        with fitz.open(pdf_path) as doc:
            for index, page in enumerate(doc, start=1):
                zoom = self.dpi / 72
                matrix = fitz.Matrix(zoom, zoom)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                page_path = output_dir / f"page_{index:04d}.jpg"
                pixmap.save(page_path)
                pages.append(page_path)

        return pages

    def build_request_data(self, image_path: Path) -> dict[str, Any]:
        data: dict[str, Any] = {
            "image": base64.b64encode(image_path.read_bytes()).decode("utf-8")
        }
        if self.mode in {"general", "accurate"}:
            data["paragraph"] = "true"
        return data

    def call_ocr_for_image(self, image_path: Path, access_token: str) -> dict[str, Any]:
        response = requests.post(
            f"{self.endpoint}?access_token={access_token}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=self.build_request_data(image_path),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def extract_text(self, result: dict[str, Any]) -> str:
        if self.mode == "table":
            lines = []
            for row in result.get("body", []) or []:
                cells = []
                for cell in row.get("row", []) if isinstance(row, dict) else []:
                    words = cell.get("word") or cell.get("words") or ""
                    if isinstance(words, list):
                        words = " ".join(str(item) for item in words)
                    if words:
                        cells.append(str(words).strip())
                if cells:
                    lines.append("\t".join(cells))
            if lines:
                return "\n".join(lines)

        items = result.get("words_result", [])
        lines = []
        for item in items:
            if isinstance(item, dict):
                words = item.get("words") or item.get("word") or ""
                if words:
                    lines.append(str(words).strip())
            elif isinstance(item, str):
                lines.append(item.strip())

        if lines:
            return "\n".join(line for line in lines if line)

        data = result.get("data")
        if isinstance(data, dict):
            content = data.get("content")
            if isinstance(content, list):
                return "\n".join(str(item).strip() for item in content if str(item).strip())
            if isinstance(content, str):
                return content.strip()

        return ""

    def parse_file(self, path: str | Path) -> dict[str, Any]:
        input_path = Path(path).expanduser().resolve()
        self.validate_input(input_path)
        access_token = self.get_access_token()

        if input_path.suffix.lower() == ".pdf":
            image_paths = self.render_pdf_pages(input_path)
        else:
            image_paths = [input_path]

        pages = []
        for index, image_path in enumerate(image_paths, start=1):
            raw = self.call_ocr_for_image(image_path, access_token)
            pages.append(
                {
                    "page": index,
                    "mode": self.mode,
                    "source_image": str(image_path),
                    "text": self.extract_text(raw),
                    "raw": raw,
                }
            )

        return {
            "file_name": input_path.name,
            "file_path": str(input_path),
            "mode": self.mode,
            "page_count": len(pages),
            "full_text": "\n\n".join(page["text"] for page in pages if page["text"]),
            "pages": pages,
        }

    def parse_with_modes(self, path: str | Path, modes: list[str]) -> dict[str, Any]:
        results = []
        for mode in modes:
            client = BaiduOCRClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                app_id=self.app_id,
                dpi=self.dpi,
                timeout=self.timeout,
                mode=mode,
            )
            results.append(client.parse_file(path))
        input_path = Path(path).expanduser().resolve()
        return {
            "file_name": input_path.name,
            "file_path": str(input_path),
            "modes": modes,
            "results": results,
        }


def format_text_output(result: dict[str, Any]) -> str:
    if "results" in result:
        sections = []
        for mode_result in result["results"]:
            sections.append(f"\n######## MODE: {mode_result['mode']} ########\n")
            for page in mode_result["pages"]:
                sections.append(f"\n===== Page {page['page']} =====\n")
                sections.append(page["text"])
        return "\n".join(sections).strip() + "\n"

    chunks = []
    for page in result["pages"]:
        chunks.append(f"\n===== Page {page['page']} =====\n")
        chunks.append(page["text"])
    return "\n".join(chunks).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="百度 OCR 模块 demo：支持图片和 PDF")
    parser.add_argument("file", help="图片或 PDF 路径")
    parser.add_argument("-o", "--output", help="输出文件路径，不传则打印到终端")
    parser.add_argument("--json", action="store_true", help="输出完整 JSON，包括每页原始 OCR 返回")
    parser.add_argument("--dpi", type=int, default=200, help="PDF 渲染 DPI，默认 200")
    parser.add_argument(
        "--mode",
        default="accurate_basic",
        choices=sorted(OCR_ENDPOINTS.keys()),
        help="OCR 模式，默认 accurate_basic",
    )
    parser.add_argument(
        "--all-relevant",
        action="store_true",
        help="依次运行考古 PDF 可能相关的多个 OCR 接口",
    )
    args = parser.parse_args()

    client = BaiduOCRClient(dpi=args.dpi, mode=args.mode)
    result = (
        client.parse_with_modes(args.file, DEFAULT_RELEVANT_MODES)
        if args.all_relevant
        else client.parse_file(args.file)
    )

    content = json.dumps(result, ensure_ascii=False, indent=2) if args.json else format_text_output(result)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
