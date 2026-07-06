#!/usr/bin/env python3
"""
墓葬3D建模生成器 - CSV -> self-contained Three.js HTML

用法:
  python modelling.py data/hebei-1.csv --outdir output --title 河北墓葬3D建模
  python modelling.py data/ --outdir output

编程式API:
  from modelling import generate_tomb_model
  result = generate_tomb_model(["data/hebei-1.csv"], outdir="output")
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


__version__ = "0.1.0"

ARTIFACT_COLUMNS = ["器物编号", "器物名称", "材质", "器型", "数量", "特征描述"]
TOMB_COLUMNS = [
    "墓葬编号",
    "年代",
    "墓向",
    "墓葬形制",
    "墓口长",
    "墓口宽",
    "墓深",
    "发掘位置",
    "层位",
    "备注",
]

ERA_COLORS = {
    "新石器时代": "#6b7280",
    "夏": "#78716c",
    "商": "#78716c",
    "周": "#0e7490",
    "春秋": "#0e7490",
    "战国": "#0e7490",
    "秦": "#dc2626",
    "汉": "#b45309",
    "三国": "#475569",
    "晋": "#7c3aed",
    "南北朝": "#0369a1",
    "隋": "#9333ea",
    "唐": "#15803d",
    "宋": "#7c3aed",
    "辽": "#059669",
    "金": "#059669",
    "元": "#be185d",
    "明": "#dc2626",
    "清": "#ca8a04",
}


def parse_num(value: Any) -> float | None:
    """Parse dimensions like 2.72, 0.25-0.27, 2.1~2.4, or strings with 米."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("米", "").replace("ｍ", "").replace("m", "")
    text = text.replace("－", "-").replace("—", "-").replace("～", "~")
    match = re.search(r"(\d+(?:\.\d+)?)(?:\s*[-~]\s*(\d+(?:\.\d+)?))?", text)
    if not match:
        return None
    first = float(match.group(1))
    second = float(match.group(2)) if match.group(2) else None
    if second is not None:
        return round((first + second) / 2, 3)
    return first


def collect_csv_files(inputs: list[str | Path]) -> list[Path]:
    """Collect CSV files from path inputs."""
    csv_files: list[Path] = []
    for inp in inputs:
        path = Path(inp)
        if path.is_dir():
            csv_files.extend(sorted(path.glob("*.csv")))
        elif path.is_file() and path.suffix.lower() == ".csv":
            csv_files.append(path)
    return csv_files


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = "" if value is None else str(value).strip()
        if text:
            return text
    return ""


def _artifact_label(artifact: dict[str, str]) -> str:
    name = artifact.get("器物名称", "")
    material = artifact.get("材质", "")
    vessel_type = artifact.get("器型", "")
    qty = artifact.get("数量", "")

    if not name:
        return ""

    parts = [name]
    attrs = [x for x in [material, vessel_type] if x and x not in name]
    if attrs:
        parts.append(f"（{' / '.join(attrs)}）")
    if qty and qty != "1":
        parts.append(f"×{qty}")
    return "".join(parts)


def _model_tier(tomb: dict[str, Any]) -> str:
    has_dims = any(tomb.get(k) for k in ["length", "width", "depth"])
    has_notes = bool(tomb.get("备注"))
    if has_dims and has_notes:
        return "full"
    if has_dims:
        return "parametric"
    return "schematic"


def aggregate_tombs(csv_files: list[str | Path]) -> list[dict[str, Any]]:
    """Aggregate artifact-row CSV data into tomb-level records."""
    tombs: dict[str, dict[str, Any]] = {}
    artifact_seen: dict[str, set[str]] = {}

    for csv_file in csv_files:
        path = Path(csv_file)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row_index, row in enumerate(reader, start=2):
                tomb_id = _first_nonempty(
                    row.get("墓葬编号"),
                    row.get("编号"),
                    row.get("id"),
                    row.get("name"),
                    f"{path.stem}-{row_index}",
                )
                if tomb_id not in tombs:
                    length = parse_num(row.get("墓口长"))
                    width = parse_num(row.get("墓口宽"))
                    depth = parse_num(row.get("墓深"))
                    tombs[tomb_id] = {
                        "id": tomb_id,
                        "name": _first_nonempty(row.get("墓葬形制"), tomb_id),
                        "source": path.name,
                        "年代": _first_nonempty(row.get("年代"), row.get("时代")),
                        "墓向": _first_nonempty(row.get("墓向"), row.get("方向")),
                        "墓葬形制": _first_nonempty(row.get("墓葬形制"), row.get("形制")),
                        "墓口长": _first_nonempty(row.get("墓口长")),
                        "墓口宽": _first_nonempty(row.get("墓口宽")),
                        "墓深": _first_nonempty(row.get("墓深")),
                        "length": length,
                        "width": width,
                        "depth": depth,
                        "发掘位置": _first_nonempty(row.get("发掘位置"), row.get("地点")),
                        "层位": _first_nonempty(row.get("层位")),
                        "备注": _first_nonempty(row.get("备注"), row.get("描述")),
                        "器物": [],
                        "artifacts": [],
                    }
                    artifact_seen[tomb_id] = set()
                else:
                    tomb = tombs[tomb_id]
                    for key in ["年代", "墓向", "墓葬形制", "墓口长", "墓口宽", "墓深", "发掘位置", "层位", "备注"]:
                        if not tomb.get(key):
                            tomb[key] = _first_nonempty(row.get(key))
                    for raw_key, num_key in [("墓口长", "length"), ("墓口宽", "width"), ("墓深", "depth")]:
                        if tomb.get(num_key) is None:
                            tomb[num_key] = parse_num(row.get(raw_key))

                artifact = {key: _first_nonempty(row.get(key)) for key in ARTIFACT_COLUMNS}
                label = _artifact_label(artifact)
                if label and label not in artifact_seen[tomb_id]:
                    artifact_seen[tomb_id].add(label)
                    tombs[tomb_id]["器物"].append(label)
                    tombs[tomb_id]["artifacts"].append(artifact)

    result = list(tombs.values())
    for tomb in result:
        tomb["model_tier"] = _model_tier(tomb)
    result.sort(key=lambda item: (item.get("source", ""), item.get("id", "")))
    return result


def _safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def render_tomb_model_html(tombs: list[dict[str, Any]], *, title: str = "墓葬3D建模") -> str:
    """Render a standalone Three.js viewer."""
    tombs_json = _safe_json(tombs)
    colors_json = _safe_json(ERA_COLORS)
    escaped_title = html.escape(title)

    template = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__ - 考古可视化</title>
<style>
* { box-sizing:border-box; }
html, body { margin:0; height:100%; overflow:hidden; }
body {
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
  color:#e8e4da; background:#141417;
}
button, input { font:inherit; }
.shell { display:grid; grid-template-columns:340px minmax(0,1fr); height:100vh; }
.sidebar {
  min-width:0; background:#1f211e; border-right:1px solid rgba(255,255,255,.12);
  display:flex; flex-direction:column;
}
.sidebar header { padding:16px 18px 14px; border-bottom:1px solid rgba(255,255,255,.1); }
.eyebrow { margin:0 0 4px; color:#aaa28f; font-size:12px; }
h1 { margin:0; font-size:20px; line-height:1.25; font-weight:650; letter-spacing:0; }
.stats { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; padding:12px 18px; border-bottom:1px solid rgba(255,255,255,.1); }
.stat { background:#292a26; border:1px solid rgba(255,255,255,.08); border-radius:6px; padding:8px; }
.stat strong { display:block; font-size:18px; color:#fff; }
.stat span { color:#aaa28f; font-size:11px; }
.controls { padding:12px 18px; display:grid; gap:10px; border-bottom:1px solid rgba(255,255,255,.1); }
.search { width:100%; border:1px solid rgba(255,255,255,.16); border-radius:6px; background:#151612; color:#fff; padding:9px 10px; outline:none; }
.filter-row { display:flex; gap:8px; flex-wrap:wrap; }
.chip {
  border:1px solid rgba(255,255,255,.14); color:#ddd4c2; background:#282923;
  border-radius:6px; padding:6px 9px; cursor:pointer;
}
.chip.is-active { background:#d6a84f; border-color:#d6a84f; color:#17130b; }
.tomb-list { flex:1; overflow:auto; padding:10px; }
.tomb-item {
  width:100%; text-align:left; color:inherit; cursor:pointer; border:1px solid transparent;
  background:transparent; border-radius:6px; padding:10px; display:grid; gap:5px;
}
.tomb-item:hover { background:rgba(255,255,255,.06); }
.tomb-item.is-active { background:rgba(214,168,79,.13); border-color:rgba(214,168,79,.45); }
.tomb-title { color:#fff; font-weight:650; line-height:1.35; }
.tomb-meta { color:#aaa28f; font-size:12px; line-height:1.45; }
.badge { display:inline-block; width:max-content; border-radius:4px; padding:2px 6px; color:#fff; font-size:11px; }
.viewer { position:relative; min-width:0; height:100vh; background:#121316; }
#canvas-container { position:absolute; inset:0 0 190px 0; }
.toolbar {
  position:absolute; top:12px; left:12px; right:12px; display:flex; gap:8px; z-index:4; flex-wrap:wrap;
}
.tool {
  border:1px solid rgba(255,255,255,.16); background:rgba(31,33,30,.86); color:#eee;
  border-radius:6px; padding:8px 10px; cursor:pointer; backdrop-filter:blur(8px);
}
.tool.is-active { background:#d6a84f; color:#17130b; border-color:#d6a84f; }
.info-panel {
  position:absolute; left:0; right:0; bottom:0; min-height:190px; max-height:190px; overflow:auto;
  background:#1b1c19; border-top:1px solid rgba(255,255,255,.12); padding:16px 20px;
  display:grid; grid-template-columns:minmax(240px,380px) minmax(0,1fr); gap:20px;
}
.info-panel h2 { margin:0 0 6px; font-size:18px; line-height:1.3; letter-spacing:0; }
.muted { color:#aaa28f; }
.dim-grid { display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; }
.dim { min-width:74px; background:#272822; border:1px solid rgba(255,255,255,.08); border-radius:6px; padding:8px; }
.dim strong { display:block; font-size:17px; color:#f4d58b; }
.dim span { color:#aaa28f; font-size:11px; }
.desc { margin:0; color:#d9d0bf; line-height:1.6; font-size:13px; }
.artifact-line { margin-top:8px; color:#aaa28f; font-size:12px; line-height:1.5; }
.empty { padding:24px; color:#aaa28f; }
@media (max-width: 780px) {
  .shell { grid-template-columns:1fr; grid-template-rows:280px minmax(0,1fr); }
  .sidebar { border-right:0; border-bottom:1px solid rgba(255,255,255,.12); }
  .info-panel { grid-template-columns:1fr; max-height:220px; }
  #canvas-container { bottom:220px; }
}
</style>
</head>
<body>
<div class="shell">
  <aside class="sidebar">
    <header>
      <p class="eyebrow">考古工具 / 3D 建模</p>
      <h1>__TITLE__</h1>
    </header>
    <div class="stats">
      <div class="stat"><strong id="stat-total">0</strong><span>墓葬</span></div>
      <div class="stat"><strong id="stat-shapes">0</strong><span>形制</span></div>
      <div class="stat"><strong id="stat-visible">0</strong><span>筛选</span></div>
    </div>
    <div class="controls">
      <input id="search" class="search" type="search" placeholder="检索编号、形制、地点、器物">
      <div class="filter-row" id="era-filters"></div>
    </div>
    <div id="tomb-list" class="tomb-list"></div>
  </aside>
  <main class="viewer">
    <div class="toolbar">
      <button id="fit-btn" class="tool" type="button">重置视角</button>
      <button id="clip-btn" class="tool" type="button">截面</button>
      <button id="label-btn" class="tool is-active" type="button">标签</button>
    </div>
    <div id="canvas-container"></div>
    <section id="info-panel" class="info-panel"></section>
  </main>
</div>

<script type="importmap">
{ "imports": { "three": "https://unpkg.com/three@0.164.1/build/three.module.js", "three/addons/": "https://unpkg.com/three@0.164.1/examples/jsm/" } }
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const tombs = __TOMBS_JSON__;
const ERA_COLORS = __COLORS_JSON__;

const container = document.getElementById('canvas-container');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x121316);
scene.fog = new THREE.Fog(0x121316, 45, 160);

const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 500);
const renderer = new THREE.WebGLRenderer({ antialias:true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI * 0.88;

scene.add(new THREE.AmbientLight(0x56504a, 0.9));
const keyLight = new THREE.DirectionalLight(0xffe5bd, 1.25);
keyLight.position.set(18, 24, 14);
keyLight.castShadow = true;
scene.add(keyLight);
const fillLight = new THREE.DirectionalLight(0x8ca6ff, 0.35);
fillLight.position.set(-16, 9, -14);
scene.add(fillLight);

const grid = new THREE.GridHelper(80, 40, 0x555144, 0x2d2e2a);
scene.add(grid);
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(80, 80),
  new THREE.MeshStandardMaterial({ color:0x181a17, roughness:1 })
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.02;
ground.receiveShadow = true;
scene.add(ground);

const tombGroup = new THREE.Group();
scene.add(tombGroup);
let labelsVisible = true;
let activeIndex = 0;
let visibleIndexes = tombs.map((_, i) => i);
let activeEra = '全部';
let clipActive = false;
const clipPlane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
}

function num(value) {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (!value) return null;
  const text = String(value).replace(/[米ｍm]/g, '').replace(/[－—]/g, '-').replace(/～/g, '~');
  const match = text.match(/(\d+(?:\.\d+)?)(?:\s*[-~]\s*(\d+(?:\.\d+)?))?/);
  if (!match) return null;
  const first = Number(match[1]);
  const second = match[2] ? Number(match[2]) : null;
  return second ? (first + second) / 2 : first;
}

function eraKey(era) {
  const text = String(era || '');
  return Object.keys(ERA_COLORS).find((key) => text.includes(key)) || '未知';
}

function colorFor(tomb) {
  const color = ERA_COLORS[eraKey(tomb.年代)] || '#8d8b83';
  return Number.parseInt(color.slice(1), 16);
}

function hexColor(color) {
  return '#' + color.toString(16).padStart(6, '0');
}

function dimsFor(tomb) {
  const shape = `${tomb.墓葬形制 || tomb.name || ''}${tomb.备注 || ''}`;
  let length = num(tomb.length) ?? num(tomb.墓口长);
  let width = num(tomb.width) ?? num(tomb.墓口宽);
  let depth = num(tomb.depth) ?? num(tomb.墓深);

  if (!length || !width || !depth) {
    if (/石棺/.test(shape)) { length ||= 1.7; width ||= 0.35; depth ||= 0.4; }
    else if (/圆|六角|八角/.test(shape)) { length ||= 3; width ||= length; depth ||= 2.7; }
    else if (/竖穴|土坑/.test(shape)) { length ||= 3.4; width ||= 1.5; depth ||= 2; }
    else if (/多室/.test(shape)) { length ||= 12; width ||= 6; depth ||= 3; }
    else { length ||= 3; width ||= 2; depth ||= 2; }
  }
  const maxDim = Math.max(length, width, depth);
  const scale = maxDim > 30 ? 0.22 : maxDim > 12 ? 0.38 : 1;
  return { length, width, depth, scale };
}

function wallMat(color, opacity=0.55) {
  return new THREE.MeshStandardMaterial({
    color, transparent:true, opacity, roughness:0.72, side:THREE.DoubleSide, depthWrite:false
  });
}
function solidMat(color) {
  return new THREE.MeshStandardMaterial({ color, roughness:0.62 });
}
function floorMat(color=0x4a3a2a) {
  return new THREE.MeshStandardMaterial({ color, roughness:0.92 });
}
function roofMat(color, opacity=0.38) {
  return new THREE.MeshStandardMaterial({
    color, transparent:true, opacity, roughness:0.65, side:THREE.DoubleSide, depthWrite:false
  });
}

function clearTomb() {
  while (tombGroup.children.length) {
    const child = tombGroup.children[0];
    child.traverse((node) => {
      if (node.geometry) node.geometry.dispose();
      if (node.material) {
        const mats = Array.isArray(node.material) ? node.material : [node.material];
        mats.forEach((mat) => mat.dispose && mat.dispose());
      }
    });
    tombGroup.remove(child);
  }
}

function addMesh(mesh, x=0, y=0, z=0) {
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  tombGroup.add(mesh);
  return mesh;
}

function addLabel(text, position, color=0xffffff) {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 112;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'rgba(15,16,15,0.78)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = 'rgba(255,255,255,0.22)';
  ctx.strokeRect(1, 1, canvas.width - 2, canvas.height - 2);
  ctx.fillStyle = hexColor(color);
  ctx.font = '600 32px "PingFang SC", sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(String(text).slice(0, 24), 256, 56);
  const texture = new THREE.CanvasTexture(canvas);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map:texture, transparent:true }));
  sprite.position.copy(position);
  sprite.scale.set(4.8, 1.05, 1);
  sprite.userData.isLabel = true;
  sprite.visible = labelsVisible;
  tombGroup.add(sprite);
}

function addDoorFrame(width, height, z, color=0x6b4226) {
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(width, height, 0.1), solidMat(color)), 0, height / 2, z);
  for (const x of [-width * 0.4, width * 0.4]) {
    addMesh(new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, height, 10), solidMat(color)), x, height / 2, z - 0.02);
  }
  for (const x of [-width * 0.28, 0, width * 0.28]) {
    addMesh(new THREE.Mesh(new THREE.BoxGeometry(width * 0.18, 0.12, 0.14), solidMat(0x8b5a2b)), x, height + 0.12, z - 0.02);
  }
}

function buildRectangular(tomb) {
  const color = colorFor(tomb);
  const { length, width, depth, scale } = dimsFor(tomb);
  const L = length * scale, W = width * scale, H = depth * scale;
  const wallT = Math.max(0.08, Math.min(L, W) * 0.035);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, 0.12, W), floorMat()), 0, 0.06, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, H, wallT), wallMat(color)), 0, H / 2, -W / 2);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, H, wallT), wallMat(color)), 0, H / 2, W / 2);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(wallT, H, W), wallMat(color)), -L / 2, H / 2, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(wallT, H, W), wallMat(color)), L / 2, H / 2, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, 0.14, W), roofMat(color)), 0, H + 0.07, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L * 0.55, 0.2, W * 0.36), floorMat(0x5a4a3a)), 0, 0.2, 0);
  addLabel(tomb.墓葬形制 || tomb.name || tomb.id, new THREE.Vector3(0, H + 1.25, 0), color);
}

function buildCircular(tomb, segments=32) {
  const color = colorFor(tomb);
  const { length, width, depth, scale } = dimsFor(tomb);
  const radius = Math.max(length, width) * scale / 2;
  const H = depth * scale;
  addMesh(new THREE.Mesh(new THREE.CylinderGeometry(radius + 0.18, radius + 0.25, 0.18, segments), floorMat()), 0, 0.09, 0);
  addMesh(new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, H, segments, 1, true), wallMat(color)), 0, H / 2 + 0.18, 0);
  addMesh(new THREE.Mesh(new THREE.SphereGeometry(radius, segments, 12, 0, Math.PI * 2, 0, Math.PI / 2), roofMat(color)), 0, H + 0.18, 0);
  const floor = new THREE.Mesh(new THREE.CircleGeometry(radius, segments), floorMat(0x3a3a3a));
  floor.rotation.x = -Math.PI / 2;
  addMesh(floor, 0, 0.2, 0);
  addMesh(new THREE.Mesh(new THREE.CylinderGeometry(radius * 0.58, radius * 0.58, 0.22, segments), floorMat(0x5a4a3a)), 0, 0.32, 0);
  if (/仿木|门楼|斗栱/.test(`${tomb.墓葬形制 || ''}${tomb.备注 || ''}`)) addDoorFrame(radius * 0.65, Math.min(H * 0.75, 2), -radius + 0.08);
  addLabel(tomb.墓葬形制 || tomb.name || tomb.id, new THREE.Vector3(0, H + radius + 0.9, 0), color);
}

function buildPyramidRoof(tomb) {
  buildRectangular(tomb);
  const color = colorFor(tomb);
  const { length, width, depth, scale } = dimsFor(tomb);
  const S = Math.max(length, width) * scale;
  const H = depth * scale;
  addMesh(new THREE.Mesh(new THREE.ConeGeometry(S * 0.6, Math.max(0.9, S * 0.45), 4), roofMat(color)), 0, H + Math.max(0.55, S * 0.23), 0).rotation.y = Math.PI / 4;
}

function buildMultiChamber(tomb) {
  const color = colorFor(tomb);
  const { length, width, depth, scale } = dimsFor(tomb);
  const L = length * scale, W = width * scale, H = depth * scale;
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, 0.14, W), floorMat()), 0, 0.07, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, H, 0.14), wallMat(color, 0.5)), 0, H / 2, -W / 2);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, H, 0.14), wallMat(color, 0.5)), 0, H / 2, W / 2);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(0.14, H, W), wallMat(color, 0.5)), -L / 2, H / 2, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(0.14, H, W), wallMat(color, 0.5)), L / 2, H / 2, 0);
  for (const x of [-L * 0.18, L * 0.18]) {
    addMesh(new THREE.Mesh(new THREE.BoxGeometry(0.12, H * 0.82, W * 0.86), wallMat(color, 0.62)), x, H * 0.41, 0);
  }
  for (const x of [-L * 0.28, L * 0.1]) {
    for (const side of [-1, 1]) {
      addMesh(new THREE.Mesh(new THREE.BoxGeometry(L * 0.16, H * 0.62, W * 0.24), wallMat(color, 0.44)), x, H * 0.31, side * W * 0.47);
    }
  }
  const passLen = Math.max(2, L * 0.28);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(passLen, H * 0.65, W * 0.35), wallMat(color, 0.32)), -L / 2 - passLen / 2, H * 0.32, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, 0.16, W), roofMat(color, 0.34)), 0, H + 0.08, 0);
  addLabel(tomb.墓葬形制 || '多室墓', new THREE.Vector3(0, H + 1.25, 0), color);
  addLabel('墓道', new THREE.Vector3(-L / 2 - passLen / 2, H + 0.65, 0), 0xaaa28f);
}

function buildShaft(tomb) {
  const color = colorFor(tomb);
  const { length, width, depth, scale } = dimsFor(tomb);
  const L = length * scale, W = width * scale, H = depth * scale;
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L * 1.15, H * 1.15, W * 1.22), wallMat(color, 0.25)), 0, H * 0.58, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, H * 0.75, W), wallMat(color, 0.55)), 0, H * 0.38, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L * 0.78, 0.18, W * 0.58), floorMat(0x5a4a3a)), 0, 0.22, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L * 1.04, 0.12, W * 1.04), roofMat(color, 0.45)), 0, H * 0.78, 0);
  addLabel(tomb.墓葬形制 || '竖穴墓', new THREE.Vector3(0, H + 0.9, 0), color);
}

function buildStoneCoffin(tomb) {
  const color = colorFor(tomb);
  const { length, width, depth, scale } = dimsFor(tomb);
  const L = length * scale, W = width * scale, H = depth * scale;
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, H, W), wallMat(color, 0.65)), 0, H / 2, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L * 0.93, H * 0.7, W * 0.78), solidMat(0x242421)), 0, H * 0.52, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L * 1.05, Math.max(0.05, H * 0.12), W * 1.08), roofMat(color, 0.55)), 0, H * 1.06, 0);
  addMesh(new THREE.Mesh(new THREE.SphereGeometry(Math.max(0.05, W * 0.16), 10, 8), solidMat(0xd4c5a9)), L * 0.28, H * 0.48, 0);
  addLabel(tomb.墓葬形制 || '石棺墓', new THREE.Vector3(0, H + 0.7, 0), color);
}

function buildWoodChamber(tomb) {
  const color = colorFor(tomb);
  const { length, width, depth, scale } = dimsFor(tomb);
  const L = length * scale, W = width * scale, H = depth * scale;
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, 0.12, W), floorMat(0x34261b)), 0, 0.06, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, H, 0.14), wallMat(color, 0.32)), 0, H / 2, -W / 2);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(L, H, 0.14), wallMat(color, 0.32)), 0, H / 2, W / 2);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(0.14, H, W), wallMat(color, 0.32)), -L / 2, H / 2, 0);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(0.14, H, W), wallMat(color, 0.32)), L / 2, H / 2, 0);
  const cL = L * 0.72, cW = W * 0.72, cH = H * 0.55;
  for (const z of [-cW / 2, cW / 2]) addMesh(new THREE.Mesh(new THREE.BoxGeometry(cL, cH, 0.1), solidMat(0x8b6914)), 0, cH / 2, z);
  for (const x of [-cL / 2, cL / 2]) addMesh(new THREE.Mesh(new THREE.BoxGeometry(0.1, cH, cW), solidMat(0x8b6914)), x, cH / 2, 0);
  for (let i = 0; i < 7; i++) addMesh(new THREE.Mesh(new THREE.BoxGeometry(cL + 0.08, 0.045, cW + 0.08), solidMat(0x8b6914)), 0, cH + i * 0.07, 0);
  const passLen = Math.max(2.5, L * 0.8);
  addMesh(new THREE.Mesh(new THREE.BoxGeometry(passLen, H * 0.5, W * 0.38), wallMat(color, 0.25)), -L / 2 - passLen / 2, H * 0.25, 0);
  addLabel(tomb.墓葬形制 || '木椁墓', new THREE.Vector3(0, H + 1.0, 0), color);
}

function buildTomb(tomb) {
  const shape = `${tomb.墓葬形制 || tomb.name || ''}${tomb.备注 || ''}`;
  if (/石棺|石板/.test(shape)) buildStoneCoffin(tomb);
  else if (/木椁|木槨/.test(shape)) buildWoodChamber(tomb);
  else if (/多室|前后室|前室|后室|耳室/.test(shape)) buildMultiChamber(tomb);
  else if (/竖穴|土坑|砖圹|壁龛/.test(shape)) buildShaft(tomb);
  else if (/六角|六边/.test(shape)) buildCircular(tomb, 6);
  else if (/八角|八边/.test(shape)) buildCircular(tomb, 8);
  else if (/圆/.test(shape)) buildCircular(tomb, 32);
  else if (/攒尖|方形/.test(shape)) buildPyramidRoof(tomb);
  else buildRectangular(tomb);
}

function applyClipping() {
  renderer.localClippingEnabled = clipActive;
  tombGroup.traverse((obj) => {
    if (!obj.isMesh || !obj.material) return;
    const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
    mats.forEach((mat) => { mat.clippingPlanes = clipActive ? [clipPlane] : []; });
  });
}

function showTomb(index) {
  activeIndex = index;
  const tomb = tombs[index];
  clearTomb();
  buildTomb(tomb);
  tombGroup.traverse((obj) => { if (obj.userData.isLabel) obj.visible = labelsVisible; });
  applyClipping();
  renderList();
  renderInfo(tomb);
  fitCamera(tomb);
}

function fitCamera(tomb) {
  const { length, width, depth, scale } = dimsFor(tomb);
  const maxDim = Math.max(length * scale, width * scale, depth * scale, 3);
  camera.position.set(maxDim * 1.45, maxDim * 0.85, maxDim * 1.45);
  controls.target.set(0, Math.max(0.7, depth * scale * 0.35), 0);
  controls.update();
}

function renderInfo(tomb) {
  const panel = document.getElementById('info-panel');
  const dims = [
    ['墓口长', tomb.墓口长 || tomb.length],
    ['墓口宽', tomb.墓口宽 || tomb.width],
    ['墓深', tomb.墓深 || tomb.depth],
  ].filter(([, value]) => value !== null && value !== undefined && value !== '');
  panel.innerHTML = `
    <div>
      <h2>${escapeHtml(tomb.id)} <span class="muted">${escapeHtml(tomb.年代 || '')}</span></h2>
      <div class="muted">${escapeHtml(tomb.墓葬形制 || tomb.name || '形制未标注')}</div>
      <div class="muted">${escapeHtml(tomb.墓向 || '')}${tomb.墓向 && tomb.发掘位置 ? ' · ' : ''}${escapeHtml(tomb.发掘位置 || '')}</div>
      <div class="dim-grid">
        ${dims.map(([label, value]) => `<div class="dim"><strong>${escapeHtml(value)}m</strong><span>${label}</span></div>`).join('')}
        <div class="dim"><strong>${escapeHtml(tomb.model_tier || 'schematic')}</strong><span>建模层级</span></div>
      </div>
    </div>
    <div>
      <p class="desc">${escapeHtml(tomb.备注 || '暂无结构描述；模型按形制关键词和默认尺寸示意生成。')}</p>
      ${tomb.器物?.length ? `<div class="artifact-line">出土器物：${escapeHtml(tomb.器物.slice(0, 28).join('、'))}${tomb.器物.length > 28 ? ' 等' : ''}</div>` : ''}
    </div>
  `;
}

function filteredIndexes() {
  const query = document.getElementById('search').value.trim().toLowerCase();
  return tombs.map((tomb, index) => ({ tomb, index })).filter(({ tomb }) => {
    const eraMatches = activeEra === '全部' || eraKey(tomb.年代) === activeEra;
    if (!eraMatches) return false;
    if (!query) return true;
    const haystack = [
      tomb.id, tomb.name, tomb.年代, tomb.墓向, tomb.墓葬形制, tomb.发掘位置, tomb.备注,
      ...(tomb.器物 || [])
    ].join(' ').toLowerCase();
    return haystack.includes(query);
  }).map(({ index }) => index);
}

function renderList() {
  const list = document.getElementById('tomb-list');
  visibleIndexes = filteredIndexes();
  document.getElementById('stat-visible').textContent = visibleIndexes.length;
  if (!visibleIndexes.length) {
    list.innerHTML = '<div class="empty">没有匹配的墓葬记录。</div>';
    return;
  }
  list.innerHTML = visibleIndexes.map((index) => {
    const tomb = tombs[index];
    const color = hexColor(colorFor(tomb));
    const dim = tomb.墓口长 || tomb.墓口宽 || tomb.墓深
      ? `${escapeHtml(tomb.墓口长 || '?')}×${escapeHtml(tomb.墓口宽 || '?')}×${escapeHtml(tomb.墓深 || '?')}m`
      : '尺寸待考';
    return `
      <button class="tomb-item ${index === activeIndex ? 'is-active' : ''}" type="button" data-index="${index}">
        <span class="tomb-title">${escapeHtml(tomb.id)}</span>
        <span class="tomb-meta">${escapeHtml(tomb.墓葬形制 || tomb.name || '')}</span>
        <span class="tomb-meta">${dim} · ${escapeHtml(tomb.发掘位置 || tomb.source || '')}</span>
        <span class="badge" style="background:${color}cc">${escapeHtml(tomb.年代 || '未知')}</span>
      </button>
    `;
  }).join('');
  list.querySelectorAll('.tomb-item').forEach((item) => {
    item.addEventListener('click', () => showTomb(Number(item.dataset.index)));
  });
}

function renderEraFilters() {
  const eras = ['全部', ...Array.from(new Set(tombs.map((t) => eraKey(t.年代)))).filter(Boolean).sort()];
  const wrap = document.getElementById('era-filters');
  wrap.innerHTML = eras.map((era) => `<button class="chip ${era === activeEra ? 'is-active' : ''}" type="button" data-era="${escapeHtml(era)}">${escapeHtml(era)}</button>`).join('');
  wrap.querySelectorAll('.chip').forEach((button) => {
    button.addEventListener('click', () => {
      activeEra = button.dataset.era;
      renderEraFilters();
      renderList();
      if (!visibleIndexes.includes(activeIndex) && visibleIndexes.length) showTomb(visibleIndexes[0]);
    });
  });
}

function resize() {
  const rect = container.getBoundingClientRect();
  camera.aspect = Math.max(rect.width, 1) / Math.max(rect.height, 1);
  camera.updateProjectionMatrix();
  renderer.setSize(Math.max(rect.width, 1), Math.max(rect.height, 1));
}

document.getElementById('search').addEventListener('input', () => {
  renderList();
  if (!visibleIndexes.includes(activeIndex) && visibleIndexes.length) showTomb(visibleIndexes[0]);
});
document.getElementById('fit-btn').addEventListener('click', () => showTomb(activeIndex));
document.getElementById('clip-btn').addEventListener('click', (event) => {
  clipActive = !clipActive;
  event.currentTarget.classList.toggle('is-active', clipActive);
  applyClipping();
});
document.getElementById('label-btn').addEventListener('click', (event) => {
  labelsVisible = !labelsVisible;
  event.currentTarget.classList.toggle('is-active', labelsVisible);
  tombGroup.traverse((obj) => { if (obj.userData.isLabel) obj.visible = labelsVisible; });
});

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

document.getElementById('stat-total').textContent = tombs.length;
document.getElementById('stat-shapes').textContent = new Set(tombs.map((t) => t.墓葬形制 || t.name || '')).size;
renderEraFilters();
renderList();
if (tombs.length) showTomb(0);
resize();
window.addEventListener('resize', resize);
animate();
</script>
</body>
</html>
"""
    return (
        template.replace("__TITLE__", escaped_title)
        .replace("__TOMBS_JSON__", tombs_json)
        .replace("__COLORS_JSON__", colors_json)
    )


def generate_tomb_model(
    inputs: list[str | Path],
    *,
    outdir: str | Path | None = None,
    title: str = "墓葬3D建模",
    write_files: bool = True,
    return_html: bool = False,
) -> dict[str, Any]:
    """Main API: accept archaeological CSV files/directories and generate a 3D tomb viewer."""
    csv_files = collect_csv_files(inputs)
    if not csv_files:
        return {"html": None, "stats": {"error": "未找到CSV文件"}}

    tombs = aggregate_tombs(csv_files)
    if not tombs:
        return {"html": None, "stats": {"error": "未提取到墓葬数据"}}

    html_str = render_tomb_model_html(tombs, title=title)
    output_path = None
    if write_files and outdir:
        outdir_path = Path(outdir)
        outdir_path.mkdir(parents=True, exist_ok=True)
        output_path = outdir_path / "tombs-3d-viewer.html"
        output_path.write_text(html_str, encoding="utf-8")

    return {
        "html": html_str if return_html else None,
        "tombs": tombs if return_html else None,
        "stats": {
            "total_csv_files": len(csv_files),
            "total_tombs": len(tombs),
            "shape_count": len({t.get("墓葬形制") or t.get("name") for t in tombs}),
            "artifact_count": sum(len(t.get("artifacts", [])) for t in tombs),
            "output": str(output_path) if output_path else None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="墓葬3D建模生成器 - CSV -> self-contained Three.js HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python modelling.py data/hebei-1.csv --outdir output --title 河北墓葬3D建模\n"
            "  python modelling.py data/ --outdir output\n"
        ),
    )
    parser.add_argument("inputs", nargs="+", help="CSV文件路径,或包含CSV的目录")
    parser.add_argument("--outdir", default="output", help="输出目录 (默认: output)")
    parser.add_argument("--title", default="墓葬3D建模", help="HTML标题")
    parser.add_argument("--discover", action="store_true", help="仅扫描CSV并输出统计,不生成HTML")
    args = parser.parse_args()

    csv_files = collect_csv_files(args.inputs)
    if not csv_files:
        print("未找到CSV文件")
        sys.exit(1)

    tombs = aggregate_tombs(csv_files)
    if args.discover:
        print(f"CSV文件: {len(csv_files)}")
        print(f"墓葬记录: {len(tombs)}")
        print(f"形制数量: {len({t.get('墓葬形制') or t.get('name') for t in tombs})}")
        print(f"器物记录: {sum(len(t.get('artifacts', [])) for t in tombs)}")
        return

    result = generate_tomb_model(
        csv_files,
        outdir=args.outdir,
        title=args.title,
        write_files=True,
        return_html=False,
    )
    stats = result["stats"]
    if "error" in stats:
        print(stats["error"])
        sys.exit(1)

    print(f"完成: {stats['total_tombs']} 座墓, {stats['shape_count']} 类形制")
    print(f"输出: {stats['output']}")


if __name__ == "__main__":
    main()
