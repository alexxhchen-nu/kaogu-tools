"""
Fast OCR parsing utilities backed by PaddleOCR.

The module is intentionally dependency-light at import time. PaddleOCR and PDF
rendering libraries are imported only when OCR is executed, which keeps app
startup fast and lets callers install optional backends as needed.

Examples:
    python backend/ocr.py ./report.pdf --out ./ocr-output --format md json txt
    python backend/ocr.py ./scans --lang ch --workers 4 --device gpu
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
PDF_EXTENSION = ".pdf"
DEFAULT_FORMATS = ("md",)
_ENGINE_CACHE: dict[tuple[str, str | None, bool], "PaddleOCREngine"] = {}
_ENGINE_CACHE_LOCK = threading.Lock()


@dataclass(slots=True)
class OCRLine:
    text: str
    confidence: float | None = None
    box: list[list[float]] | None = None


@dataclass(slots=True)
class OCRPage:
    page_number: int
    source: str
    text: str
    lines: list[OCRLine]


@dataclass(slots=True)
class OCRDocument:
    source: str
    engine: str
    lang: str
    pages: list[OCRPage]
    elapsed_seconds: float

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text)


def parse(
    source: str | os.PathLike[str],
    *,
    lang: str = "ch",
    device: str | None = None,
    workers: int | None = None,
    pdf_dpi: int = 180,
    enable_angle_cls: bool = True,
    reuse_engine: bool = False,
) -> list[OCRDocument]:
    """Run OCR against a file or directory and return structured documents.

    Args:
        source: Image file, PDF file, or directory containing images/PDFs.
        lang: PaddleOCR language code. Use "ch" for Chinese.
        device: Optional execution device, e.g. "cpu", "gpu", "gpu:0".
        workers: Number of source files to process concurrently. A value above
            one creates one PaddleOCR instance per worker.
        pdf_dpi: Rendering resolution for PDFs when local rendering is needed.
        enable_angle_cls: Enables text-line angle classification where the
            installed PaddleOCR version supports it.
        reuse_engine: Reuse a cached PaddleOCR instance for single-worker runs.
    """

    paths = discover_inputs(source)
    if not paths:
        raise FileNotFoundError(f"No OCR inputs found under: {source}")

    worker_count = normalize_workers(workers, len(paths))
    started = time.perf_counter()

    if worker_count == 1:
        engine = (
            get_cached_engine(
                lang=lang,
                device=device,
                enable_angle_cls=enable_angle_cls,
            )
            if reuse_engine
            else PaddleOCREngine(
                lang=lang, device=device, enable_angle_cls=enable_angle_cls
            )
        )
        return [
            engine.parse_path(path, pdf_dpi=pdf_dpi, started=started) for path in paths
        ]

    documents: list[OCRDocument] = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(
                _parse_path_worker,
                path,
                lang,
                device,
                enable_angle_cls,
                pdf_dpi,
                started,
            ): path
            for path in paths
        }
        for future in as_completed(futures):
            documents.append(future.result())

    return sorted(documents, key=lambda doc: doc.source)


class PaddleOCREngine:
    """Small compatibility wrapper around PaddleOCR v2 and v3 APIs."""

    def __init__(
        self,
        *,
        lang: str = "ch",
        device: str | None = None,
        enable_angle_cls: bool = True,
    ) -> None:
        self.lang = lang
        self.device = device
        self.enable_angle_cls = enable_angle_cls
        self._ocr = self._build_engine()
        self.api = "predict" if hasattr(self._ocr, "predict") else "ocr"

    def parse_path(
        self,
        path: Path,
        *,
        pdf_dpi: int = 180,
        started: float | None = None,
    ) -> OCRDocument:
        started = time.perf_counter() if started is None else started
        if path.suffix.lower() == PDF_EXTENSION:
            pages = self._parse_pdf(path, pdf_dpi=pdf_dpi)
        else:
            pages = [self._parse_image(path, page_number=1, source=str(path))]

        return OCRDocument(
            source=str(path),
            engine=f"PaddleOCR/{self.api}",
            lang=self.lang,
            pages=pages,
            elapsed_seconds=round(time.perf_counter() - started, 3),
        )

    def _build_engine(self) -> Any:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:  # pragma: no cover - depends on local env
            raise RuntimeError(
                "PaddleOCR is not installed. Install the OCR extra with "
                "`uv sync --extra ocr` or `pip install 'kaogu-tools[ocr]'`."
            ) from exc

        errors: list[Exception] = []
        configs = [
            self._v3_config(),
            self._v2_config(show_log=False),
            self._v2_config(),
        ]

        for config in configs:
            try:
                return PaddleOCR(**config)
            except TypeError as exc:
                errors.append(exc)

        details = "; ".join(str(error) for error in errors)
        raise RuntimeError(
            f"Unable to initialize PaddleOCR with supported options: {details}"
        )

    def _v3_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "lang": self.lang,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": self.enable_angle_cls,
        }
        if self.device:
            config["device"] = self.device
        return config

    def _v2_config(self, *, show_log: bool | None = None) -> dict[str, Any]:
        config: dict[str, Any] = {
            "lang": self.lang,
            "use_angle_cls": self.enable_angle_cls,
        }
        if show_log is not None:
            config["show_log"] = show_log
        if self.device:
            config["use_gpu"] = self.device.startswith("gpu")
        return config

    def _parse_pdf(self, path: Path, *, pdf_dpi: int) -> list[OCRPage]:
        image_paths: list[Path] = []
        with tempfile.TemporaryDirectory(prefix="kaogu-ocr-") as temp_dir:
            image_paths = render_pdf_pages(path, Path(temp_dir), dpi=pdf_dpi)
            return [
                self._parse_image(image_path, page_number=index, source=str(path))
                for index, image_path in enumerate(image_paths, start=1)
            ]

    def _parse_image(self, path: Path, *, page_number: int, source: str) -> OCRPage:
        raw_result = self._predict(path)
        lines = normalize_ocr_result(raw_result)
        text = lines_to_text(lines)
        return OCRPage(page_number=page_number, source=source, text=text, lines=lines)

    def _predict(self, path: Path) -> Any:
        if self.api == "predict":
            return self._ocr.predict(input=str(path))
        return self._ocr.ocr(str(path), cls=self.enable_angle_cls)


def get_cached_engine(
    *,
    lang: str = "ch",
    device: str | None = None,
    enable_angle_cls: bool = True,
) -> PaddleOCREngine:
    """Return one shared OCR engine per compatible configuration."""
    key = (lang, device, enable_angle_cls)
    with _ENGINE_CACHE_LOCK:
        engine = _ENGINE_CACHE.get(key)
        if engine is None:
            engine = PaddleOCREngine(
                lang=lang,
                device=device,
                enable_angle_cls=enable_angle_cls,
            )
            _ENGINE_CACHE[key] = engine
        return engine


def _parse_path_worker(
    path: Path,
    lang: str,
    device: str | None,
    enable_angle_cls: bool,
    pdf_dpi: int,
    started: float,
) -> OCRDocument:
    engine = PaddleOCREngine(
        lang=lang, device=device, enable_angle_cls=enable_angle_cls
    )
    return engine.parse_path(path, pdf_dpi=pdf_dpi, started=started)


def discover_inputs(source: str | os.PathLike[str]) -> list[Path]:
    path = Path(source).expanduser().resolve()
    if path.is_file():
        if is_supported_input(path):
            return [path]
        raise ValueError(f"Unsupported OCR input: {path}")

    if not path.is_dir():
        raise FileNotFoundError(f"OCR source does not exist: {path}")

    return sorted(
        file for file in path.rglob("*") if file.is_file() and is_supported_input(file)
    )


def is_supported_input(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix == PDF_EXTENSION or suffix in IMAGE_EXTENSIONS


def normalize_workers(workers: int | None, input_count: int) -> int:
    if workers is None:
        workers = min(input_count, max(1, (os.cpu_count() or 2) // 2))
    return max(1, min(workers, input_count))


def render_pdf_pages(path: Path, output_dir: Path, *, dpi: int = 180) -> list[Path]:
    """Render PDF pages to PNGs using pypdfium2 or PyMuPDF."""

    try:
        return render_pdf_pages_with_pdfium(path, output_dir, dpi=dpi)
    except ImportError:
        pass

    try:
        return render_pdf_pages_with_pymupdf(path, output_dir, dpi=dpi)
    except ImportError as exc:  # pragma: no cover - depends on local env
        raise RuntimeError(
            "PDF input requires either `pypdfium2` or `PyMuPDF` to render pages. "
            "Install one of them, or pass image files directly."
        ) from exc


def render_pdf_pages_with_pdfium(
    path: Path, output_dir: Path, *, dpi: int
) -> list[Path]:
    import pypdfium2 as pdfium

    output_paths: list[Path] = []
    pdf = pdfium.PdfDocument(str(path))
    scale = dpi / 72
    try:
        for index in range(len(pdf)):
            image = pdf[index].render(scale=scale).to_pil()
            output_path = output_dir / f"page-{index + 1:04d}.png"
            image.save(output_path)
            output_paths.append(output_path)
    finally:
        pdf.close()
    return output_paths


def render_pdf_pages_with_pymupdf(
    path: Path, output_dir: Path, *, dpi: int
) -> list[Path]:
    import fitz

    output_paths: list[Path] = []
    document = fitz.open(path)
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    try:
        for index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            output_path = output_dir / f"page-{index:04d}.png"
            pixmap.save(output_path)
            output_paths.append(output_path)
    finally:
        document.close()
    return output_paths


def normalize_ocr_result(raw_result: Any) -> list[OCRLine]:
    """Normalize PaddleOCR v2/v3 outputs into OCRLine objects."""

    lines = normalize_v3_result(raw_result)
    if lines:
        return sort_lines(lines)

    lines = normalize_v2_result(raw_result)
    if lines:
        return sort_lines(lines)

    return []


def normalize_v3_result(raw_result: Any) -> list[OCRLine]:
    lines: list[OCRLine] = []
    results = raw_result if isinstance(raw_result, list) else [raw_result]

    for result in results:
        data = result_to_dict(result)
        if not data:
            continue

        rec_texts = data.get("rec_texts") or data.get("texts") or []
        rec_scores = data.get("rec_scores") or data.get("scores") or []
        rec_boxes = (
            data.get("rec_polys")
            or data.get("rec_boxes")
            or data.get("dt_polys")
            or data.get("boxes")
            or []
        )

        for index, text in enumerate(rec_texts):
            normalized = str(text).strip()
            if not normalized:
                continue
            lines.append(
                OCRLine(
                    text=normalized,
                    confidence=as_float(item_at(rec_scores, index)),
                    box=normalize_box(item_at(rec_boxes, index)),
                )
            )

    return lines


def normalize_v2_result(raw_result: Any) -> list[OCRLine]:
    entries = flatten_v2_entries(raw_result)
    lines: list[OCRLine] = []

    for entry in entries:
        if not is_v2_entry(entry):
            continue

        box = normalize_box(entry[0])
        text_info = entry[1]
        if isinstance(text_info, (tuple, list)):
            text = str(text_info[0]).strip() if text_info else ""
            confidence = as_float(text_info[1]) if len(text_info) > 1 else None
        else:
            text = str(text_info).strip()
            confidence = None

        if text:
            lines.append(OCRLine(text=text, confidence=confidence, box=box))

    return lines


def result_to_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result

    for attr in ("json", "res"):
        value = getattr(result, attr, None)
        if isinstance(value, dict):
            return value

    if hasattr(result, "to_dict"):
        value = result.to_dict()
        if isinstance(value, dict):
            return value

    return {}


def flatten_v2_entries(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []

    if value and all(is_v2_entry(item) for item in value):
        return value

    flattened: list[Any] = []
    for item in value:
        if is_v2_entry(item):
            flattened.append(item)
        elif isinstance(item, list):
            flattened.extend(flatten_v2_entries(item))
    return flattened


def is_v2_entry(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], list)
        and isinstance(value[1], (tuple, list))
    )


def sort_lines(lines: Sequence[OCRLine]) -> list[OCRLine]:
    return sorted(
        lines, key=lambda line: (box_top(line.box), box_left(line.box), line.text)
    )


def lines_to_text(lines: Sequence[OCRLine], *, y_gap: float = 14) -> str:
    if not lines:
        return ""

    if all(line.box is None for line in lines):
        return "\n".join(line.text for line in lines if line.text)

    grouped: list[list[OCRLine]] = []
    for line in sort_lines(lines):
        if not grouped:
            grouped.append([line])
            continue

        previous_y = box_top(grouped[-1][-1].box)
        current_y = box_top(line.box)
        if current_y - previous_y > y_gap:
            grouped.append([line])
        else:
            grouped[-1].append(line)

    text_lines = [" ".join(item.text for item in group).strip() for group in grouped]
    return "\n".join(text_line for text_line in text_lines if text_line)


def normalize_box(value: Any) -> list[list[float]] | None:
    if value is None:
        return None

    if hasattr(value, "tolist"):
        value = value.tolist()

    if not isinstance(value, list):
        return None

    if len(value) == 4 and all(is_number(item) for item in value):
        left, top, right, bottom = [float(item) for item in value]
        return [[left, top], [right, top], [right, bottom], [left, bottom]]

    points: list[list[float]] = []
    for point in value:
        if hasattr(point, "tolist"):
            point = point.tolist()
        if isinstance(point, (tuple, list)) and len(point) >= 2:
            x, y = point[0], point[1]
            if is_number(x) and is_number(y):
                points.append([float(x), float(y)])

    return points or None


def box_top(box: list[list[float]] | None) -> float:
    if not box:
        return 0.0
    return min(point[1] for point in box)


def box_left(box: list[list[float]] | None) -> float:
    if not box:
        return 0.0
    return min(point[0] for point in box)


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def item_at(values: Any, index: int) -> Any:
    if hasattr(values, "tolist"):
        values = values.tolist()
    if isinstance(values, (tuple, list)) and index < len(values):
        return values[index]
    return None


def write_outputs(
    documents: Sequence[OCRDocument],
    output_dir: str | os.PathLike[str],
    *,
    formats: Iterable[str] = DEFAULT_FORMATS,
) -> list[Path]:
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for document in documents:
        stem = Path(document.source).stem
        selected_formats = {item.lower().lstrip(".") for item in formats}

        if "json" in selected_formats:
            json_path = output_path / f"{stem}.json"
            json_path.write_text(
                json.dumps(asdict(document), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            written.append(json_path)

        if "txt" in selected_formats:
            txt_path = output_path / f"{stem}.txt"
            txt_path.write_text(document.text, encoding="utf-8")
            written.append(txt_path)

        if "md" in selected_formats or "markdown" in selected_formats:
            md_path = output_path / f"{stem}.md"
            md_path.write_text(document_to_markdown(document), encoding="utf-8")
            written.append(md_path)

    return written


def document_to_markdown(document: OCRDocument) -> str:
    title = Path(document.source).name
    parts = [
        f"# {title}",
        "",
        f"- Engine: {document.engine}",
        f"- Language: {document.lang}",
        f"- Pages: {len(document.pages)}",
        f"- Elapsed seconds: {document.elapsed_seconds}",
        "",
    ]

    for page in document.pages:
        if len(document.pages) > 1:
            parts.extend([f"## Page {page.page_number}", ""])
        parts.extend([page.text.strip(), ""])

    return "\n".join(parts).strip() + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fast PaddleOCR parser for images and PDFs."
    )
    parser.add_argument("source", help="Image, PDF, or directory to OCR.")
    parser.add_argument(
        "-o",
        "--out",
        default="ocr-output",
        help="Directory for output files. Defaults to ./ocr-output.",
    )
    parser.add_argument(
        "-f",
        "--format",
        nargs="+",
        default=list(DEFAULT_FORMATS),
        choices=["md", "markdown", "txt", "json"],
        help="One or more output formats.",
    )
    parser.add_argument(
        "--lang", default="ch", help="PaddleOCR language code. Defaults to ch."
    )
    parser.add_argument(
        "--device", default=None, help="Optional device, e.g. cpu, gpu, gpu:0."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Concurrent file workers. Defaults to roughly half CPU count.",
    )
    parser.add_argument(
        "--pdf-dpi",
        type=int,
        default=180,
        help="PDF render DPI. Higher values improve accuracy but cost time/memory.",
    )
    parser.add_argument(
        "--no-angle-cls",
        action="store_true",
        help="Disable text-line angle classification for maximum speed.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    documents = parse(
        args.source,
        lang=args.lang,
        device=args.device,
        workers=args.workers,
        pdf_dpi=args.pdf_dpi,
        enable_angle_cls=not args.no_angle_cls,
    )
    written = write_outputs(documents, args.out, formats=args.format)

    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
