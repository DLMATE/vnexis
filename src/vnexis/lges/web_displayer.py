import asyncio
import logging
import threading
import time

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

from vnexis.common.event import EventHandler
from vnexis.common.utils import draw_text_using_idx, resize_boxes
from vnexis.core.event import Preprocessed
from vnexis.lges.dto import LgesPreprocessResult

logger = logging.getLogger(__name__)


class WebDisplayer(EventHandler):
    """
    FastAPI + MJPEG 스트리밍 기반 웹 디스플레이어.
    클라이언트별 독립 스트림을 제공합니다.

    - /                    → 전체 클라이언트 모니터링 페이지
    - /stream/{client_id}  → MJPEG 스트림
    - /api/clients         → 등록된 클라이언트 목록
    """

    def __init__(
        self,
        event_bus=None,
        width: int = 800,
        height: int = 600,
    ):
        super().__init__(event_bus)
        self._width = width
        self._height = height

        # client_id → 최신 JPEG 프레임
        self._frames: dict[int, bytes] = {}
        self._metadata: dict[int, dict] = {}
        self._locks: dict[int, threading.Lock] = {}
        self._client_ids: set[int] = set()
        self._last_time: dict[int, float] = {}
        self._fps: dict[int, int] = {}

        self.app = self._create_app()

    def _ensure_client(self, client_id: int):
        if client_id not in self._locks:
            self._locks[client_id] = threading.Lock()
            self._client_ids.add(client_id)

    def handle(self, event: Preprocessed):
        client_id = event.client_id
        self._ensure_client(client_id)

        now = time.perf_counter()
        last = self._last_time.get(client_id)
        if last and (now - last) > 0:
            self._fps[client_id] = int(1 / (now - last))
        self._last_time[client_id] = now

        result: LgesPreprocessResult = event.result
        frame = self._render_frame(client_id, result)

        _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

        with self._locks[client_id]:
            self._frames[client_id] = jpeg.tobytes()
            self._metadata[client_id] = {
                "client_id": client_id,
                "frame_idx": result.frame.idx,
                "cell_id": result.metadata.cell_id,
                "key_frame_detect_time": f"{result.metadata.key_frame_detect_time:.3f}",
            }

    def _render_frame(self, client_id: int, result: LgesPreprocessResult) -> np.ndarray:
        data = cv2.resize(result.frame.data, (self._width, self._height))

        boxes = resize_boxes(
            result.key_frame_detection_result.boxes,
            result.key_frame_detection_result.img_size,
            (result.frame.height, result.frame.width),
            keep_aspect_ratio=True,
            inverse=True,
        )
        boxes = resize_boxes(
            boxes,
            (result.frame.height, result.frame.width),
            (self._height, self._width),
            keep_aspect_ratio=False,
            inverse=False,
        )

        labels = result.key_frame_detection_result.labels
        scores = result.key_frame_detection_result.scores
        for box, label, score in zip(boxes, labels, scores):
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(data, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                data,
                f"{label}: {score:.2f}",
                (x1, y1),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

        data = draw_text_using_idx(data, f"idx: {result.frame.idx}", 0, (0, 255, 0))
        data = draw_text_using_idx(
            data, f"cell_id: {result.metadata.cell_id}", 1, (0, 255, 0)
        )
        data = draw_text_using_idx(
            data, f"fps: {self._fps.get(client_id, 0)}", 2, (0, 255, 0)
        )
        data = draw_text_using_idx(
            data,
            f"detect_time: {result.metadata.key_frame_detect_time:.3f}",
            3,
            (0, 255, 0),
        )
        return data

    # ── FastAPI App ──

    def _create_app(self) -> FastAPI:
        app = FastAPI(title="Vnexis Monitor")

        @app.get("/", response_class=HTMLResponse)
        async def index():
            return INDEX_HTML

        @app.get("/stream/{client_id}")
        async def stream(client_id: int):
            return StreamingResponse(
                self._generate_frames(client_id),
                media_type="multipart/x-mixed-replace; boundary=frame",
            )

        @app.get("/api/clients")
        async def clients():
            result = []
            for cid in sorted(self._client_ids):
                meta = self._metadata.get(cid, {})
                result.append({"client_id": cid, **meta})
            return result

        return app

    async def _generate_frames(self, client_id: int):
        while True:
            jpeg = None
            if client_id in self._locks:
                with self._locks[client_id]:
                    jpeg = self._frames.get(client_id)
            if jpeg:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
            await asyncio.sleep(0.033)


INDEX_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Vnexis Monitor</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1a1a2e; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
  header {
    background: #16213e; padding: 16px 24px; display: flex;
    align-items: center; justify-content: space-between;
    border-bottom: 2px solid #0f3460;
  }
  header h1 { font-size: 20px; color: #e94560; }
  header span { font-size: 13px; color: #888; }
  .grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
    gap: 16px; padding: 20px;
  }
  .card {
    background: #16213e; border-radius: 8px; overflow: hidden;
    border: 1px solid #0f3460;
  }
  .card-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 14px; background: #0f3460;
  }
  .card-header h3 { font-size: 14px; }
  .card-header .status { font-size: 12px; color: #4ecca3; }
  .card img { width: 100%; display: block; background: #000; }
  .card-meta {
    padding: 8px 14px; font-size: 12px; color: #aaa;
    display: flex; gap: 16px;
  }
  .no-clients {
    text-align: center; padding: 60px; color: #555; font-size: 16px;
  }
</style>
</head>
<body>
<header>
  <h1>Vnexis Monitor</h1>
  <span id="client-count">-</span>
</header>
<div class="grid" id="grid"></div>
<div class="no-clients" id="no-clients" style="display:none;">No clients connected</div>

<script>
async function refresh() {
  try {
    const res = await fetch('/api/clients');
    const clients = await res.json();
    const grid = document.getElementById('grid');
    const noClients = document.getElementById('no-clients');
    document.getElementById('client-count').textContent = clients.length + ' client(s)';

    if (clients.length === 0) {
      grid.style.display = 'none';
      noClients.style.display = 'block';
      return;
    }
    grid.style.display = 'grid';
    noClients.style.display = 'none';

    const existing = new Set();
    clients.forEach(c => {
      existing.add('card-' + c.client_id);
      let card = document.getElementById('card-' + c.client_id);
      if (!card) {
        card = document.createElement('div');
        card.className = 'card';
        card.id = 'card-' + c.client_id;
        card.innerHTML = `
          <div class="card-header">
            <h3>Client ${c.client_id}</h3>
            <span class="status">LIVE</span>
          </div>
          <img src="/stream/${c.client_id}" alt="stream">
          <div class="card-meta" id="meta-${c.client_id}"></div>
        `;
        grid.appendChild(card);
      }
      const meta = document.getElementById('meta-' + c.client_id);
      if (meta) {
        meta.innerHTML = `
          <span>Frame: ${c.frame_idx || '-'}</span>
          <span>Cell: ${c.cell_id || '-'}</span>
          <span>Detect: ${c.key_frame_detect_time || '-'}s</span>
        `;
      }
    });

    grid.querySelectorAll('.card').forEach(card => {
      if (!existing.has(card.id)) card.remove();
    });
  } catch(e) {}
}
refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""
