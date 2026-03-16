import logging

import uvicorn
from vnexis.common.event import EventBus
from vnexis.core.event import (
    DefectDetected,
    FrameBuffered,
    FrameCaptured,
    FramePendingDone,
    Preprocessed,
    RawDataCollected,
    TargetCreated,
)
from vnexis.core.service.frame_buffer import FrameBufferHandler, FrameBufferManager
from vnexis.core.service.frame_clipper import FrameClipperHandler, FrameClipperManager

from .collector import AvSourceGateway
from .detector import FaultFrameDetector
from .postprocessor import ImageSaver, VideoRequester, VideoSaver
from .preprocessor import KeyFrameDetector
from .target_creator import TriggerTracker
from .web_displayer import WebDisplayer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    max_client = 4
    video_path = "C://workspace//stream_inspection//assets//hm_anvil//video//5s, no 14 pallete.mp4"
    key_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//trigger//trigger_yolonas_s_v1.0.onnx"
    fault_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//defect//YoloNAS_Seg_S_v1.1.onnx"

    event_bus = EventBus()

    # ── 공통 서비스 ──
    frame_buffer_manager = FrameBufferManager()
    frame_buffer_handler = FrameBufferHandler(event_bus, frame_buffer_manager)

    frame_clipper_manager = FrameClipperManager()
    frame_clipper_handler = FrameClipperHandler(event_bus, frame_clipper_manager)

    image_saver = ImageSaver(event_bus)
    video_requester = VideoRequester(event_bus, frame_clipper_manager)
    video_saver = VideoSaver(event_bus)

    # ── WebDisplayer ──
    web_displayer = WebDisplayer(event_bus)

    # ── 공통 구독 ──
    event_bus.subscribe(FrameCaptured, frame_buffer_handler)
    event_bus.subscribe(FrameBuffered, frame_clipper_handler)
    event_bus.subscribe(DefectDetected, image_saver)
    event_bus.subscribe(DefectDetected, video_requester)
    event_bus.subscribe(FramePendingDone, video_saver)
    event_bus.subscribe(Preprocessed, web_displayer)

    # ── 클라이언트별 파이프라인 ──
    collectors = []
    for client_id in range(max_client):
        frame_buffer_manager.add_buffer(client_id)
        frame_clipper_manager.add_frame_clipper(
            client_id, frame_buffer_manager.get_buffer(client_id)
        )

        collector = AvSourceGateway(client_id, video_path, event_bus)
        key_frame_detector = KeyFrameDetector(
            client_id, key_frame_model_path, event_bus
        )
        trigger_tracker = TriggerTracker(client_id, event_bus)
        fault_frame_detector = FaultFrameDetector(
            client_id, fault_frame_model_path, event_bus, default_threshold=0.2
        )

        event_bus.subscribe(RawDataCollected, key_frame_detector)
        event_bus.subscribe(Preprocessed, trigger_tracker)
        event_bus.subscribe(TargetCreated, fault_frame_detector)

        collectors.append(collector)

    # -- print flow --
    print_full_flow(*collectors)

    # ── Collector 시작 ──
    for collector in collectors:
        collector.connect()
        video_saver.set_input_stream(collector.stream)
        collector.start()

    # ── FastAPI 서버 시작 (메인 스레드) ──
    logger.info("[Main] http://localhost:8080 에서 모니터링")
    uvicorn.run(web_displayer.app, host="0.0.0.0", port=8080, log_level="warning")

    # ── 종료 ──
    for collector in collectors:
        collector.disconnect()


if __name__ == "__main__":
    main()
