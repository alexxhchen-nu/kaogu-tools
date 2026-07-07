# Kaogu Tools 功能化推进计划

## 执行原则

- 每一步只做一个小目标。
- 每一步都必须先验证通过，再进入下一步。
- 优先接不依赖第三方 API key 的功能。
- OCR、Exa、Firecrawl、Baidu OCR 等外部服务最后再接。
- 所有第三方 provider key 只放后端，不放前端。
- 不使用 `NEXT_PUBLIC_*` 暴露任何 provider key。
- 暂时继续忽略 `backend/baidu_ocr_demo.py`，不修改、不依赖它。
- 终端命令只使用 `uv`、`mise`、`brew`。

## 当前已经完成

- 已新增 FastAPI 后端入口：
  - `backend/main.py`

- 已新增后端配置文件：
  - `backend/config.py`

- 已新增环境变量模板：
  - `.env.example`

- 已接通并验证：
  - `GET /health`
  - `POST /dynamic-parser/parse`
  - `POST /modelling/generate`
  - `POST /gis/generate`

- 已验证：
  - `/health` 可以返回 `{"status": "ok"}`
  - `dynamic-parser` 可以返回墓葬 JSON、Markdown、CSV
  - `modelling` 可以上传 CSV 并返回 3D HTML
  - `gis` 可以上传 CSV 并返回地图 HTML
  - `shared/tests` 里的 parser 测试通过

- 已完成浏览器联调：
  - `/DynamicParser` 可以从前端调用后端并显示真实结果
  - `/Modelling` 可以上传 CSV、调用后端并打开 3D Blob 页面
  - `/GIS` 已改成专用上传页，可以上传 CSV、调用后端并打开地图 Blob 页面
  - `/DynamicParser` 已改成专用结果页，可以显示墓葬表格、Markdown 预览、JSON 预览和 CSV 下载按钮
  - `/Modelling` 状态面板已显示墓葬数、形制数、器物记录和最近模型入口
  - `/GIS` 结果面板已显示墓葬数、站点数、坐标模式和站点地图入口

- 已完成界面清理：
  - Next.js 开发指示器已在 `frontend/next.config.mjs` 关闭

- 当前本地端口情况：
  - `127.0.0.1:8000` 已被旧版后端占用，只暴露 `/tools/*` 路由
  - 本轮新版 FastAPI 后端运行在 `127.0.0.1:8765`
  - `frontend/.env.local` 当前指向 `http://127.0.0.1:8765`

## 下一步总目标

- 先让浏览器里的前端页面真正调用本地 FastAPI 后端。
- 最短链路先跑通：
  - 前端输入
  - 后端处理
  - 前端展示真实结果

## Step 1：确认本地后端稳定运行

- 启动后端：

```bash
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

- 如果 `8000` 已被旧服务占用，临时使用：

```bash
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload
```

- 验证：

```text
http://127.0.0.1:8000/health
```

- 通过标准：
  - 返回 `{"status":"ok"}`
  - 后端没有报错

- 通过后再进入 Step 2。

## Step 2：配置前端本地 API 地址

- 在 `frontend/.env.local` 中配置：

```bash
NEXT_PUBLIC_KAOGU_API_BASE_URL=http://127.0.0.1:8000
```

- 注意：
  - `frontend/.env.local` 不提交。
  - 不放任何 provider API key。
  - 不新增 `NEXT_PUBLIC_EXA_API_KEY`。
  - 不新增 `NEXT_PUBLIC_FIRECRAWL_API_KEY`。
  - 不新增 `NEXT_PUBLIC_BAIDU_*`。

- 通过标准：
  - 前端能找到后端地址。
  - 浏览器请求走 Kaogu 后端，而不是直接请求第三方服务。

## Step 3：先联调 DynamicParser 页面

- 页面：
  - `/DynamicParser`

- 原因：
  - 不需要上传文件。
  - 不需要第三方 key。
  - 后端接口已经验证过。
  - 最适合作为第一条真实前后端链路。

- 操作：
  - 打开 `/DynamicParser`
  - 输入一段墓葬文本
  - 点击运行
  - 前端调用 `POST /dynamic-parser/parse`

- 通过标准：
  - 页面可以显示后端返回结果。
  - 返回内容里有墓葬编号、尺寸、Markdown 或 CSV。
  - 出错时页面显示清楚错误，而不是静默失败。

- 第一版可以先显示 JSON dump。
- 通过后再做更好的表格和下载按钮。

## Step 4：联调 Modelling 页面

- 页面：
  - `/Modelling`

- 当前状态：
  - 前端已经有专用上传逻辑。
  - 后端 `POST /modelling/generate` 已经验证过。

- 操作：
  - 上传一个小 CSV。
  - 前端调用 `/modelling/generate`。
  - 后端返回 `html` 和 `stats`。
  - 前端用新标签页打开 3D HTML。

- 通过标准：
  - CSV 可以上传。
  - 新标签页可以打开 3D 模型。
  - 页面能显示生成状态。
  - 后端返回的 `total_tombs` 正确。

- 如果浏览器拦截新标签页：
  - 调整前端打开逻辑。
  - 保持用户点击行为触发窗口打开。

## Step 5：把 GIS 页面改成专用上传页面

- 页面：
  - `/GIS`

- 当前问题：
  - 现在它还是通用工具页。
  - 后端返回地图 HTML 后，通用 JSON 展示不够好用。

- 要做：
  - 改成类似 `/Modelling` 的专用页面。
  - 上传 CSV。
  - 调用 `POST /gis/generate`。
  - 后端返回 `data.sites` 和 `data.overview`。
  - 前端生成 Blob URL。
  - 新标签页打开地图。

- 通过标准：
  - 上传小 CSV 后能打开地图。
  - 单站点结果能打开。
  - 多站点结果能展示站点列表。
  - 每个站点有一个“打开地图”按钮。

## Step 6：优化 DynamicParser 结果展示

- 状态：
  - 已完成。

- 第一版 JSON dump 跑通后，再做体验优化。

- 建议展示：
  - 墓葬表格
  - JSON 预览
  - Markdown 预览
  - CSV 下载按钮

- 通过标准：
  - 用户不用读原始 JSON 也能看懂结果。
  - CSV 可以下载。
  - JSON 仍然可以复制或查看。

- 已验证：
  - `/DynamicParser` 调用 `http://127.0.0.1:8765/dynamic-parser/parse` 返回 `200`
  - 页面显示 `M1` 墓葬表格结果
  - Markdown 预览可见
  - JSON 预览保留在折叠面板中
  - CSV 下载可以实际触发

## Step 7：优化 Modelling 和 GIS 状态面板

- 状态：
  - 已完成。

- Modelling 显示：
  - 墓葬数量
  - 形制数量
  - 器物数量
  - “重新打开最近生成模型”

- GIS 显示：
  - 总墓葬数
  - 站点数
  - 坐标模式
  - 站点地图入口

- 通过标准：
  - 用户能知道生成了什么。
  - 用户可以重新打开结果。
  - 失败状态有明确原因。

- 已验证：
  - `mise exec -- pnpm --dir frontend typecheck` 通过
  - `/Modelling` 上传最小 CSV 后调用 `http://127.0.0.1:8765/modelling/generate` 返回 `200`
  - `/Modelling` 页面显示墓葬数、形制数、器物记录和“重新打开最近生成的模型”
  - `/GIS` 上传最小 CSV 后调用 `http://127.0.0.1:8765/gis/generate` 返回 `200`
  - `/GIS` 页面显示墓葬数、站点数、坐标模式和“打开地图”

## Step 8：接 OCR 第一条小闭环

- 状态：
  - 已完成第一小步。

- 当前决策：
  - OCR 输入以 PDF 为主。
  - 同时兼容小图片。
  - 第一版使用本地 PaddleOCR。
  - 不接 Baidu OCR。
  - 不修改、不依赖 `backend/baidu_ocr_demo.py`。
  - 第一版仍然是同步接口，不先做异步 job。

- 当前限制：
  - 默认 OCR 上传大小：8MB。
  - 默认 PDF 页数上限：5 页。
  - 超过页数直接返回 413，不进入 OCR。
  - 长 PDF、批量 PDF、异步队列以后再做。

- 已新增后端接口：
  - `POST /ocr/parse`

- 后端返回：
  - `text`
  - `markdown`
  - `pages`
  - `stats.filename`
  - `stats.engine`
  - `stats.page_count`
  - `stats.line_count`
  - `stats.elapsed_seconds`

- 已新增配置：
  - `KAOGU_MAX_OCR_UPLOAD_MB=8`
  - `KAOGU_MAX_OCR_PDF_PAGES=5`

- 已改前端页面：
  - `/OCR` 已从通用工具页改为专用上传页。
  - 页面支持 PDF 或图片上传。
  - 页面显示 OCR 状态、页数、文本行数、耗时、Markdown 预览和行级识别结果。
  - 页面支持下载 TXT 和 Markdown。

- 已验证：
  - `uv run python -m py_compile backend/main.py backend/config.py backend/ocr.py` 通过。
  - `mise exec -- pnpm --dir frontend typecheck` 通过。
  - `mise exec -- git diff --check` 通过。
  - PDF 页数统计可用。
  - 1 页 PDF 可以走完整 `/ocr/parse` 响应结构。
  - 超过 5 页 PDF 返回 `413`。
  - 非 PDF/图片文件返回 `400`。

- 尚未验证：
  - 尚未用真实 PaddleOCR 跑一份真实 PDF。
  - 原因是第一次运行可能下载模型，应该作为单独小步骤处理。

- 下一小步：
  - 准备一份 1 页或 2 页小 PDF。
  - 真实调用 `/ocr/parse`。
  - 确认 PaddleOCR 能在本机完成识别。
  - 再用浏览器 `/OCR` 上传同一份 PDF 做前端联调。

## Step 9：接 Exa / Firecrawl / Baidu OCR 前的安全准备

- 所有 provider 调用必须在 `backend/`。

- 后端环境变量：

```bash
EXA_API_KEY=
FIRECRAWL_API_KEY=
BAIDU_OCR_API_KEY=
BAIDU_OCR_SECRET_KEY=
BAIDU_OCR_APP_ID=
```

- 前端只允许：

```bash
NEXT_PUBLIC_KAOGU_API_BASE_URL=
```

- 上线前必须补：
  - 请求超时
  - 文件大小限制
  - rate limit
  - quota
  - 日志脱敏
  - 安全错误返回

## Step 10：部署前检查

- 后端部署到 Railway。

- 后端启动命令：

```bash
uv run uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

- 前端部署到 Netlify 或 Railway。

- 前端生产环境变量：

```bash
NEXT_PUBLIC_KAOGU_API_BASE_URL=https://your-backend-domain
```

- 通过标准：
  - 生产前端能请求生产后端。
  - 生产后端 `/health` 可访问。
  - 不暴露任何 provider key。

## 当前最推荐的下一件事

- 做 Step 8 的真实 OCR 小 PDF smoke test。

- 也就是：
  - 找一份 1 页或 2 页 PDF。
  - 先从后端直接调用 `POST /ocr/parse`。
  - 如果第一次运行下载 PaddleOCR 模型，单独记录耗时和错误。
  - 后端真实 OCR 成功后，再打开 `/OCR` 页面上传同一份 PDF。
  - 确认前端能显示 Markdown、TXT 下载和行级识别结果。
  - 继续不修改、不依赖 `backend/baidu_ocr_demo.py`。

- 这一步通过后，再考虑：
  - 长 PDF 是否改异步 job。
  - 是否加入 OCR 队列状态。
  - 是否接 MinerU 或 Baidu OCR 作为可选后端。
  - 是否把 OCR 结果一键送到 `/DynamicParser`。
