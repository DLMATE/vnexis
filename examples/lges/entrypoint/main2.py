import logging
import multiprocessing
import threading
import time

from lges.event import KeyFrameDetected, KeyFrameDetectionDone
from lges.handler import (
    FaultFrameDetector,
    KeyFrameDetector,
    TriggerTracker,
    WebDisplayer,
)
from vnexis.entrypoint import Stream
from vnexis.event import RawDataCollected

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VIDEO_PATH = (
    "C://workspace//stream_inspection//assets//hm_anvil//video//5s, no 14 pallete.mp4"
)
KEY_FRAME_MODEL_PATH = "C://workspace//stream_inspection//assets//hm_anvil//trigger//trigger_yolonas_s_v1.0.onnx"
FAULT_FRAME_MODEL_PATH = "C://workspace//stream_inspection//assets//hm_anvil//defect//YoloNAS_Seg_S_v1.1.onnx"


def run_stream(process_id: int, enable_web: bool = False, web_port: int = 8080):
    logger.info(f"[Process {process_id}] 시작")

    vnexis = Stream(
        max_sessions=1,
        paths=[VIDEO_PATH],
        save_defect_frame=True,
        save_video=True,
    )

    session_id = 0
    fault_frame_detector = FaultFrameDetector(
        FAULT_FRAME_MODEL_PATH, default_threshold=0.2
    )
    key_frame_detector = KeyFrameDetector(session_id, KEY_FRAME_MODEL_PATH)
    trigger_tracker = TriggerTracker(session_id)

    vnexis.add_handler(KeyFrameDetected, fault_frame_detector)
    vnexis.add_handler(RawDataCollected, key_frame_detector, session_id)
    vnexis.add_handler(KeyFrameDetectionDone, trigger_tracker, session_id)

    if enable_web:
        web_displayer = WebDisplayer(max_workers=1)
        vnexis.add_handler(KeyFrameDetectionDone, web_displayer, session_id)

    vnexis.connect()
    vnexis.start()

    logger.info(f"[Process {process_id}] 실행 중...")

    if enable_web:
        import uvicorn

        logger.info(f"[Process {process_id}] http://localhost:{web_port} 에서 모니터링")
        server = threading.Thread(
            target=uvicorn.run,
            args=(web_displayer.app,),
            kwargs={"host": "0.0.0.0", "port": web_port, "log_level": "warning"},
            daemon=True,
        )
        server.start()

    try:
        while vnexis._video_readers[0].is_running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    vnexis.disconnect()
    vnexis.save_statistics()
    logger.info(f"[Process {process_id}] 종료")


def main():
    num_processes = 4
    processes = []

    for i in range(num_processes):
        p = multiprocessing.Process(target=run_stream, args=(i, True, 8080 + i))
        processes.append(p)
        p.start()

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        logger.info("[Main] 종료 신호 수신, 프로세스 종료 중...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()


if __name__ == "__main__":
    main()
