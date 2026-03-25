import logging

from lges.event import (
    KeyFrameDetected,
    KeyFrameDetectionDone,
)
from lges.handler import (
    FaultFrameDetector,
    KeyFrameDetector,
    TriggerTracker,
    WebDisplayer,
)
from vnexis.entrypoint import Stream
from vnexis.event import (
    RawDataCollected,
)

logging.basicConfig(level=logging.INFO)


logger = logging.getLogger(__name__)


def main():
    max_sessions = 4
    video_path = "C://workspace//stream_inspection//assets//hm_anvil//video//5s, no 14 pallete.mp4"
    key_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//trigger//trigger_yolonas_s_v1.0.onnx"
    fault_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//defect//YoloNAS_Seg_S_v1.1.onnx"

    vnexis = Stream(
        max_sessions=max_sessions,
        paths=[video_path] * max_sessions,
        save_defect_frame=True,
        save_video=True,
    )

    web_displayer = WebDisplayer(max_workers=max_sessions)
    fault_frame_detector = FaultFrameDetector(
        fault_frame_model_path, default_threshold=0.2
    )

    vnexis.add_handler(KeyFrameDetected, fault_frame_detector)
    for session_id in range(max_sessions):
        key_frame_detector = KeyFrameDetector(session_id, key_frame_model_path)
        trigger_tracker = TriggerTracker(session_id)

        vnexis.add_handler(RawDataCollected, key_frame_detector, session_id)
        vnexis.add_handler(KeyFrameDetectionDone, trigger_tracker, session_id)
        vnexis.add_handler(KeyFrameDetectionDone, web_displayer, session_id)

    vnexis.save_mermaid_flow()
    vnexis.connect()
    vnexis.start()

    # ── FastAPI 서버 시작 (메인 스레드) ──
    logger.info("[Main] http://localhost:8080 에서 모니터링")

    import uvicorn

    uvicorn.run(web_displayer.app, host="0.0.0.0", port=8080, log_level="warning")

    # ── 종료 ──
    vnexis.disconnect()
    vnexis.save_statistics()


if __name__ == "__main__":
    main()
