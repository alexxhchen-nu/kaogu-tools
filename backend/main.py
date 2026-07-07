import contextlib
import io
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .dynamic_parser import auto_parse
from .modelling import generate_tomb_model
from .nsbd_gis import generate_gis
from .ocr import IMAGE_EXTENSIONS, PDF_EXTENSION, document_to_markdown, parse as parse_ocr


settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DynamicParserRequest(BaseModel):
    text: str = Field(..., min_length=1)
    report_name: str = "manual-input"


async def save_upload_to_temp(
    file: UploadFile,
    temp_dir: Path,
    *,
    allowed_suffixes: set[str],
    max_bytes: int | None = None,
    max_mb: int | None = None,
) -> Path:
    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_suffixes:
        expected = ", ".join(sorted(allowed_suffixes))
        raise HTTPException(status_code=400, detail=f"文件类型不支持，请上传 {expected} 文件。")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空。")
    upload_limit = max_bytes or settings.max_upload_bytes
    upload_limit_mb = max_mb or settings.max_upload_mb
    if len(content) > upload_limit:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大，请上传不超过 {upload_limit_mb}MB 的文件。",
        )

    target = temp_dir / f"upload{suffix}"
    target.write_bytes(content)
    return target


def serialize_ocr_document(document: object, *, filename: str) -> dict[str, object]:
    pages = []
    line_count = 0

    for page in getattr(document, "pages", []):
        lines = [
            {
                "text": line.text,
                "confidence": line.confidence,
                "box": line.box,
            }
            for line in page.lines
        ]
        line_count += len(lines)
        pages.append(
            {
                "page_number": page.page_number,
                "text": page.text,
                "lines": lines,
            }
        )

    markdown = document_to_markdown(document)
    source_name = Path(getattr(document, "source", filename)).name
    if source_name != filename:
        markdown = markdown.replace(f"# {source_name}", f"# {filename}", 1)

    return {
        "text": getattr(document, "text", ""),
        "markdown": markdown,
        "pages": pages,
        "stats": {
            "filename": filename,
            "engine": getattr(document, "engine", "PaddleOCR"),
            "lang": getattr(document, "lang", "ch"),
            "page_count": len(pages),
            "line_count": line_count,
            "elapsed_seconds": getattr(document, "elapsed_seconds", None),
        },
    }


def count_pdf_pages(path: Path) -> int:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="PDF OCR 需要 pypdfium2 才能读取页数和渲染页面。",
        ) from exc

    try:
        pdf = pdfium.PdfDocument(str(path))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF 文件无法读取：{exc}") from exc

    try:
        return len(pdf)
    finally:
        pdf.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/dynamic-parser/parse")
def parse_dynamic_tombs(payload: DynamicParserRequest) -> dict[str, object]:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="请输入需要抽取的文本。")

    try:
        parser = auto_parse(payload.report_name.strip() or "manual-input", text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"墓葬文本抽取失败：{exc}") from exc

    return {
        "ok": True,
        "data": {
            "json": parser.to_json(),
            "markdown": parser.to_markdown_string(),
            "csv": parser.to_csv_string(),
        },
    }


@app.post("/ocr/parse")
async def parse_ocr_document(file: UploadFile = File(...)) -> dict[str, object]:
    filename = file.filename or "upload"

    with tempfile.TemporaryDirectory(prefix="kaogu-ocr-upload-") as temp_root:
        upload_path = await save_upload_to_temp(
            file,
            Path(temp_root),
            allowed_suffixes=set(IMAGE_EXTENSIONS) | {PDF_EXTENSION},
            max_bytes=settings.max_ocr_upload_bytes,
            max_mb=settings.max_ocr_upload_mb,
        )

        if upload_path.suffix.lower() == PDF_EXTENSION:
            page_count = count_pdf_pages(upload_path)
            if page_count > settings.max_ocr_pdf_pages:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"PDF 页数过多，当前同步 OCR 最多支持 "
                        f"{settings.max_ocr_pdf_pages} 页。"
                    ),
                )

        try:
            documents = parse_ocr(
                upload_path,
                lang="ch",
                workers=1,
                enable_angle_cls=True,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=f"OCR 引擎暂不可用：{exc}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"OCR 识别失败：{exc}") from exc

    if not documents:
        raise HTTPException(status_code=422, detail="OCR 没有返回可解析结果。")

    return {
        "ok": True,
        "data": serialize_ocr_document(documents[0], filename=filename),
    }


@app.post("/modelling/generate")
async def generate_model(file: UploadFile = File(...)) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="kaogu-model-") as temp_root:
        csv_path = await save_upload_to_temp(
            file,
            Path(temp_root),
            allowed_suffixes={".csv"},
        )
        result = generate_tomb_model(
            [csv_path],
            write_files=False,
            return_html=True,
        )

    stats = result.get("stats", {})
    if isinstance(stats, dict) and stats.get("error"):
        raise HTTPException(status_code=400, detail=str(stats["error"]))

    return {
        "html": result.get("html"),
        "stats": stats,
    }


@app.post("/gis/generate")
async def generate_gis_map(
    file: UploadFile = File(...),
    overview: bool = Form(False),
    coord_mode: str = Form("auto"),
) -> dict[str, object]:
    if coord_mode not in {"auto", "exact", "jitter", "none"}:
        raise HTTPException(status_code=400, detail="coord_mode 必须是 auto、exact、jitter 或 none。")

    with tempfile.TemporaryDirectory(prefix="kaogu-gis-") as temp_root:
        csv_path = await save_upload_to_temp(
            file,
            Path(temp_root),
            allowed_suffixes={".csv"},
        )
        with contextlib.redirect_stdout(io.StringIO()):
            result = generate_gis(
                [csv_path],
                write_files=False,
                return_html=True,
                overview=overview,
                coord_mode=coord_mode,
            )

    stats = result.get("stats", {})
    if isinstance(stats, dict) and stats.get("error"):
        raise HTTPException(status_code=400, detail=str(stats["error"]))

    return {
        "ok": True,
        "data": {
            "sites": result.get("sites", {}),
            "overview": result.get("overview"),
            "stats": stats,
        },
    }
