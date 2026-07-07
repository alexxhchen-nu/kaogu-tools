# 考古工具箱功能化联调计划

## 目标

把当前前端工具页面与 Python 后端能力连接起来，形成可本地运行、可测试、可部署的完整应用。当前阶段先规划 API 接口、前后端契约、开发顺序与风险控制。

明确约束：暂时忽略 `backend/baidu_ocr_demo.py`，不修改、不导入、不依赖该文件。

## 当前状态

- 前端是 Next.js 应用，位于 `frontend/`。
- 后端是 Python 脚本集合，位于 `backend/`。
- 前端已有通用 API 客户端：`frontend/src/lib/api-client.ts`。
- 前端工具元数据已经定义 endpoint：
  - `/ocr/parse`
  - `/library/search`
  - `/dynamic-parser/parse`
  - `/modelling/generate`
  - `/gis/generate`
- 目前还没有统一 FastAPI 服务入口。
- `资料库检索` 当前主要依赖 `shared/data_catalogue.json` 和前端静态筛选逻辑。
- `三维建模` 前端已经有自定义上传逻辑，期望后端返回 `html` 或 `url`。

## 总体架构

本阶段采用“薄 API 层 + 复用现有业务函数”的方式：

- 新增 FastAPI 入口，例如 `backend/main.py`。
- API 层只负责：
  - 接收请求
  - 校验输入
  - 保存临时上传文件
  - 调用现有后端函数
  - 统一返回 JSON 或 HTML 字符串
  - 处理错误
- 核心解析、建模、GIS、OCR 逻辑继续保留在现有模块中。

## 后端 API 设计

### 1. 健康检查

`GET /health`

返回：

```json
{
  "status": "ok"
}
```

用途：

- 供前端检测 API 是否在线。
- 供部署平台健康检查。

### 2. 墓葬文本抽取

`POST /dynamic-parser/parse`

请求：

```json
{
  "text": "M1，长方形竖穴土坑墓。墓口长3.4、宽1.8、深2.1米。",
  "report_name": "manual-input"
}
```

后端调用：

```python
backend.dynamic_parser.auto_parse(report_name, text)
```

返回：

```json
{
  "ok": true,
  "data": {
    "json": {},
    "markdown": "...",
    "csv": "..."
  }
}
```

第一优先级原因：

- 不需要文件上传。
- 不依赖重型 OCR 环境。
- 最容易做单元测试和前后端联调。

### 3. 墓葬三维建模

`POST /modelling/generate`

请求：

- `multipart/form-data`
- 字段：`file`
- 文件类型：CSV

后端调用：

```python
backend.modelling.generate_tomb_model(
    [temp_csv_path],
    write_files=False,
    return_html=True,
)
```

返回：

```json
{
  "html": "<!doctype html>...",
  "stats": {
    "total_csv_files": 1,
    "total_tombs": 12,
    "shape_count": 4,
    "artifact_count": 30
  }
}
```

说明：

- 保持前端 `Modelling.tsx` 当前预期。
- 第一版直接返回 HTML 字符串，前端用 Blob URL 在新标签页打开。
- 后续如果生成文件较大，再改成对象存储 URL。

### 4. 遗址空间分析

`POST /gis/generate`

请求：

- `multipart/form-data`
- 字段：`file`
- 文件类型：CSV
- 可选字段：
  - `overview`
  - `coord_mode`

后端调用：

```python
backend.nsbd_gis.generate_gis(
    [temp_csv_path],
    write_files=False,
    return_html=True,
    overview=False,
)
```

返回：

```json
{
  "ok": true,
  "data": {
    "sites": {
      "site-key": "<!doctype html>..."
    },
    "overview": null,
    "stats": {
      "total_tombs": 12,
      "site_count": 1
    }
  }
}
```

前端建议：

- 类似三维建模，收到 HTML 后在新标签页打开。
- 如果返回多个 site，前端显示站点列表，每个站点一个“打开地图”按钮。

### 5. 考古文献解析 OCR

`POST /ocr/parse`

请求：

- `multipart/form-data`
- 字段：`file`
- 支持 PDF 或图片

后端调用：

```python
backend.ocr.parse(temp_file_path)
```

返回：

```json
{
  "ok": true,
  "data": {
    "documents": [],
    "markdown": "...",
    "text": "..."
  }
}
```

风险与限制：

- OCR 依赖重，启动慢。
- PDF 可能很大，同步接口容易超时。
- 第一版建议限制文件大小和页数。
- 后续可以升级为任务队列：
  - `POST /ocr/jobs`
  - `GET /ocr/jobs/{job_id}`
  - `GET /ocr/jobs/{job_id}/result`

### 6. 资料库检索

`POST /library/search`

短期策略：

- 保留当前前端静态检索逻辑。
- 后端接口不是第一优先级。

后续可做：

```json
{
  "query": "战国 唐县 墓地",
  "series": "nsbd"
}
```

返回：

```json
{
  "ok": true,
  "data": {
    "results": []
  }
}
```

可扩展方向：

- 从 `shared/data_catalogue.json` 服务端读取。
- 支持全文索引 Markdown。
- 支持返回 PDF、Markdown、CSV 的 CDN 链接。
- 后续接向量检索或关键词高亮。

## 前端配置

继续使用已有环境变量：

```env
NEXT_PUBLIC_KAOGU_API_BASE_URL=http://localhost:8000
```

本地开发：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`

生产部署：

- 前端部署到 Netlify 或 Railway。
- 后端部署到 Railway。
- 在前端部署环境中设置 `NEXT_PUBLIC_KAOGU_API_BASE_URL` 为后端公网地址。

## 依赖调整

`pyproject.toml` 需要补充：

```toml
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "python-multipart",
    "pydantic-settings"
]
```

保留现有解析依赖：

- `paddleocr`
- `paddlepaddle`
- `pypdfium2`
- `chonkie`

注意：

- OCR 相关依赖较重，可以后续考虑拆分 optional dependency。
- 部署时需要确认 Railway 镜像是否能正确安装 PaddlePaddle。

## 实施顺序

### 阶段一：建立 API 骨架

1. 新增 `backend/main.py`。
2. 加入 FastAPI app。
3. 实现 `GET /health`。
4. 配置 CORS，允许本地 `http://localhost:3000`。
5. 添加后端启动命令文档。

验收标准：

- `uvicorn backend.main:app --reload` 可启动。
- `GET http://localhost:8000/health` 返回 `{ "status": "ok" }`。
- 前端 `BackendStatus` 能识别 API 在线。

### 阶段二：接入墓葬文本抽取

1. 实现 `POST /dynamic-parser/parse`。
2. 修正测试导入路径。
3. 增加 FastAPI TestClient 测试。
4. 前端保留 JSON 展示，先保证可用。

验收标准：

- 输入示例墓葬文本后，返回墓葬列表。
- 返回 Markdown 和 CSV 字符串。
- 测试通过。

### 阶段三：接入三维建模

1. 实现 `POST /modelling/generate`。
2. 保存上传 CSV 到临时目录。
3. 调用 `generate_tomb_model(..., return_html=True, write_files=False)`。
4. 返回 `html` 和 `stats`。
5. 验证前端可打开新标签页模型。

验收标准：

- 上传 CSV 后生成 Three.js HTML。
- 前端新标签页打开模型。
- 失败时前端显示清晰错误。

### 阶段四：接入 GIS

1. 实现 `POST /gis/generate`。
2. 调用 `generate_gis(..., return_html=True, write_files=False)`。
3. 前端改造成地图结果打开方式。

验收标准：

- 上传 CSV 后生成地图 HTML。
- 单站点和多站点返回都能处理。

### 阶段五：接入 OCR

1. 实现 `POST /ocr/parse`。
2. 增加文件大小限制。
3. 使用临时目录保存上传文件。
4. 调用 `backend.ocr.parse`。
5. 返回 text、markdown、json。

验收标准：

- 上传小 PDF 或图片可返回 OCR 文本。
- 错误信息对用户可读。
- 不阻塞其他轻量接口。

### 阶段六：前端结果展示优化

1. `墓葬文本抽取`：显示墓葬表格、JSON、CSV 下载。
2. `OCR`：显示 Markdown/text 预览，提供 JSON 下载。
3. `GIS`：显示地图入口。
4. `三维建模`：保留新标签页打开逻辑，补充统计摘要。
5. 所有工具统一 loading、error、success 状态。

## 测试计划

### 后端测试

- `GET /health`
- `POST /dynamic-parser/parse`
- `POST /modelling/generate`
- `POST /gis/generate`
- `POST /ocr/parse` 小样本测试

### 前端测试

- API base URL 配置正确。
- 后端未启动时显示友好错误。
- 后端启动后各工具页面能提交请求。
- 三维建模和 GIS 返回 HTML 后能打开新标签页。

### 回归测试

- `pnpm typecheck`
- 后端单元测试
- FastAPI 路由 smoke test
- 关键页面浏览器截图检查：
  - `/`
  - `/OCR`
  - `/DynamicParser`
  - `/Modelling`
  - `/GIS`
  - `/Library`

## 部署计划

### 后端 Railway

需要配置：

- Python 版本：3.12
- 启动命令：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

需要确认：

- PaddleOCR/PaddlePaddle 是否能在 Railway 环境安装。
- 如果 OCR 安装失败，可以先部署不含 OCR 的 API，后续单独处理 OCR worker。

### 前端 Netlify 或 Railway

需要配置：

```env
NEXT_PUBLIC_KAOGU_API_BASE_URL=https://your-backend-domain
```

构建命令：

```bash
pnpm install
pnpm run build
```

## 风险

1. **OCR 性能风险**
   - 大 PDF 可能导致超时。
   - PaddleOCR 依赖重，部署可能失败。
   - 缓解：先限制文件大小，后续改异步任务。

2. **HTML 返回体过大**
   - 三维建模和 GIS 直接返回 HTML，数据大时响应会变重。
   - 缓解：第一版先用 HTML 字符串，后续改对象存储 URL。

3. **CORS 与环境变量**
   - 本地和生产 API 地址不同。
   - 缓解：统一使用 `NEXT_PUBLIC_KAOGU_API_BASE_URL`。

4. **测试路径不一致**
   - 当前测试中存在旧导入路径。
   - 缓解：修正测试引用，保证测试直接覆盖当前模块。

## 下一步

建议下一步从阶段一开始实施：

1. 添加 FastAPI 依赖。
2. 新增 `backend/main.py`。
3. 实现 `/health`。
4. 启动后端并让前端状态检测通过。

完成后再接入 `dynamic-parser`，这是最快能验证“前端调用后端并返回真实结果”的路径。
