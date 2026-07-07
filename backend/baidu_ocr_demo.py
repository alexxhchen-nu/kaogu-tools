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
OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".pnm", ".webp"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | {".pdf"}


class BaiduOCRClient:
    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        app_id: str | None = None,
        dpi: int = 200,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key or self._get_required_env("BAIDU_OCR_API_KEY")
        self.secret_key = secret_key or self._get_required_env("BAIDU_OCR_SECRET_KEY")
        self.app_id = app_id or os.getenv("BAIDU_OCR_APP_ID", "")
        self.dpi = dpi
        self.timeout = timeout

    @staticmethod
    def _get_required_env(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"缺少环境变量: {name}")
        return value

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

    def call_ocr_for_image(self, image_path: Path, access_token: str) -> dict[str, Any]:
        image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        response = requests.post(
            f"{OCR_URL}?access_token={access_token}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"image": image_base64},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def extract_text(result: dict[str, Any]) -> str:
        return "\n".join(
            item.get("words", "").strip()
            for item in result.get("words_result", [])
            if item.get("words", "").strip()
        )

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
                    "source_image": str(image_path),
                    "text": self.extract_text(raw),
                    "raw": raw,
                }
            )

        return {
            "file_name": input_path.name,
            "file_path": str(input_path),
            "page_count": len(pages),
            "full_text": "\n\n".join(page["text"] for page in pages if page["text"]),
            "pages": pages,
        }


def format_text_output(result: dict[str, Any]) -> str:
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
    args = parser.parse_args()

    client = BaiduOCRClient(dpi=args.dpi)
    result = client.parse_file(args.file)

    content = (
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.json
        else format_text_output(result)
    )

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
