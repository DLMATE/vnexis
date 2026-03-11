import logging
import multiprocessing
import time

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
from .displayer import Displayer
from .postprocessor import ImageSaver, VideoRequester, VideoSaver
from .preprocessor import KeyFrameDetector
from .target_creator import TriggerTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_client(
    client_id: int,
    video_path: str,
    key_frame_model_path: str,
    fault_frame_model_path: str,
):
    """각 프로세스에서 독립적으로 실행되는 클라이언트"""
    logger.info(
        f"[Client {client_id}] 프로세스 시작 (PID: {multiprocessing.current_process().pid})"
    )

    # 프로세스별 독립 EventBus
    event_bus = EventBus()

    # frame buffer
    frame_buffer_manager = FrameBufferManager()
    frame_buffer_manager.add_buffer(client_id)
    frame_buffer_handler = FrameBufferHandler(event_bus, frame_buffer_manager)

    # frame clipper
    frame_clipper_manager = FrameClipperManager()
    frame_clipper_manager.add_frame_clipper(
        client_id, frame_buffer_manager.get_buffer(client_id)
    )
    frame_clipper_handler = FrameClipperHandler(event_bus, frame_clipper_manager)

    # postprocessor
    image_saver = ImageSaver(event_bus)
    video_requester = VideoRequester(event_bus, frame_clipper_manager)
    video_saver = VideoSaver(event_bus)

    # collector & pipeline
    collector = AvSourceGateway(client_id, video_path, event_bus)
    key_frame_detector = KeyFrameDetector(client_id, key_frame_model_path, event_bus)
    trigger_tracker = TriggerTracker(client_id, event_bus)
    fault_frame_detector = FaultFrameDetector(
        client_id, fault_frame_model_path, event_bus, default_threshold=0.2
    )

    # subscribe
    event_bus.subscribe(FrameCaptured, frame_buffer_handler)
    event_bus.subscribe(FrameBuffered, frame_clipper_handler)
    event_bus.subscribe(RawDataCollected, key_frame_detector)
    event_bus.subscribe(Preprocessed, trigger_tracker)
    event_bus.subscribe(TargetCreated, fault_frame_detector)
    event_bus.subscribe(DefectDetected, image_saver)
    event_bus.subscribe(DefectDetected, video_requester)
    event_bus.subscribe(FramePendingDone, video_saver)

    # displayer (client_id == 0 만)
    displayer = None
    if client_id == 0:
        displayer = Displayer(client_id, event_bus)
        event_bus.subscribe(Preprocessed, displayer)

    # run
    collector.connect()
    video_saver.set_input_stream(collector.stream)
    collector.start()

    logger.info(f"[Client {client_id}] 파이프라인 실행 중...")

    if displayer:
        displayer.show()
        collector.disconnect()
    else:
        try:
            while collector.is_running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info(f"[Client {client_id}] 종료 요청")
        finally:
            collector.disconnect()

    logger.info(f"[Client {client_id}] 프로세스 종료")


def main():
    max_client = 4
    video_path = "C://workspace//stream_inspection//assets//hm_anvil//video//5s, no 14 pallete.mp4"
    key_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//trigger//trigger_yolonas_s_v1.0.onnx"
    fault_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//defect//YoloNAS_Seg_S_v1.1.onnx"

    processes = []
    for client_id in range(max_client):
        p = multiprocessing.Process(
            target=run_client,
            args=(client_id, video_path, key_frame_model_path, fault_frame_model_path),
            name=f"Client-{client_id}",
        )
        processes.append(p)

    for p in processes:
        p.start()
        logger.info(f"{p.name} started (PID: {p.pid})")

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        logger.info("전체 종료 요청")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join(timeout=5)

    logger.info("모든 프로세스 종료 완료")


if __name__ == "__main__":
    main()
