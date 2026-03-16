import logging

from lges.event import (
    KeyFrameDetected,
    KeyFrameDetectionDone,
)
from lges.handler import (
    FaultFrameDetector,
    FaultFrameSaver,
    KeyFrameDetector,
    TriggerTracker,
    VideoReader,
    VideoRequester,
    VideoSaver,
    WebDisplayer,
)
from vnexis.event import (
    DefectDetected,
    FrameBuffered,
    FrameCaptured,
    FramePendingDone,
    RawDataCollected,
    get_glboal_event_bus,
)
from vnexis.handler import (
    FrameBuffering,
    FrameBufferManager,
    FrameClipperManager,
    FrameClipping,
)

logging.basicConfig(level=logging.INFO)


logger = logging.getLogger(__name__)


def main():
    client_id = 0
    max_client = 4
    video_path = "C://workspace//stream_inspection//assets//hm_anvil//video//5s, no 14 pallete.mp4"
    key_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//trigger//trigger_yolonas_s_v1.0.onnx"
    fault_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//defect//YoloNAS_Seg_S_v1.1.onnx"
    global_event_bus = get_glboal_event_bus()

    frame_buffer_manager = FrameBufferManager()
    frame_clipper_manager = FrameClipperManager()

    frame_buffering = FrameBuffering(
        event_bus=global_event_bus, frame_buffer_manager=frame_buffer_manager
    )
    frame_clipping = FrameClipping(
        event_bus=global_event_bus, frame_clipper_manager=frame_clipper_manager
    )

    image_saver = FaultFrameSaver()
    video_requester = VideoRequester(frame_clipper_manager)
    video_saver = VideoSaver()
    web_displayer = WebDisplayer(max_workers=max_client)
    fault_frame_detector = FaultFrameDetector(
        None, fault_frame_model_path, global_event_bus, default_threshold=0.2
    )

    global_event_bus.subscribe(FrameCaptured, frame_buffering)
    global_event_bus.subscribe(FrameBuffered, frame_clipping)
    global_event_bus.subscribe(DefectDetected, image_saver)
    global_event_bus.subscribe(DefectDetected, video_requester)
    global_event_bus.subscribe(FramePendingDone, video_saver)
    global_event_bus.subscribe(KeyFrameDetected, fault_frame_detector)
    # global_event_bus.subscribe(KeyFrameDetectionDone, web_displayer)

    collectors = []
    for client_id in range(max_client):
        frame_buffer_manager.add_buffer(client_id)
        frame_clipper_manager.add_frame_clipper(
            client_id, frame_buffer_manager.get_buffer(client_id)
        )

        collector = VideoReader(client_id, global_event_bus, video_path)
        key_frame_detector = KeyFrameDetector(
            client_id,
            key_frame_model_path,
            global_event_bus,
        )
        trigger_tracker = TriggerTracker(client_id, global_event_bus)
        # fault_frame_detector = FaultFrameDetector(
        #     client_id, fault_frame_model_path, global_event_bus, default_threshold=0.2
        # )

        global_event_bus.subscribe(RawDataCollected, key_frame_detector, client_id)
        # collector.event_bus.subscribe(FrameCaptured, frame_buffering)
        global_event_bus.subscribe(KeyFrameDetectionDone, trigger_tracker, client_id)
        global_event_bus.subscribe(KeyFrameDetectionDone, web_displayer, client_id)

        collectors.append(collector)

    # ── 흐름도 출력 ──
    from vnexis.event import print_full_flow, save_mermaid_flow

    print_full_flow(*collectors)
    save_mermaid_flow(*collectors, path="docs/flow.md")

    # # ── Collector 시작 ──
    # for collector in collectors:
    #     collector.connect()
    #     video_saver.set_input_stream(collector.stream)
    #     collector.start()

    # # ── FastAPI 서버 시작 (메인 스레드) ──
    # logger.info("[Main] http://localhost:8080 에서 모니터링")

    # import uvicorn

    # uvicorn.run(web_displayer.app, host="0.0.0.0", port=8080, log_level="warning")

    # ── 종료 ──
    for collector in collectors:
        collector.disconnect()


if __name__ == "__main__":
    main()
