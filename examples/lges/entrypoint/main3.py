"""
프로세스 구조:

  [메인 프로세스]
    Collector → RawDataCollected ──ZMQ──→ [KeyFrameDetector 프로세스]
    TriggerTracker ← Preprocessed ←─ZMQ──┘
         ↓
    TargetCreated ──ZMQ──→ [FaultFrameDetector 프로세스]
    ImageSaver 등 ← DetectionDone/DefectDetected ←─ZMQ──┘

  포트 할당:
    5555: 메인 → KeyFrameDetector (RawDataCollected)
    5556: KeyFrameDetector → 메인 (Preprocessed)
    5557: 메인 → FaultFrameDetector (TargetCreated)
    5558: FaultFrameDetector → 메인 (DetectionDone, DefectDetected)
"""

import logging
import multiprocessing
import time

from vnexis.common.event import EventBus
from vnexis.common.zmq_event_bus import ZmqEventBus
from vnexis.core.event import (
    DefectDetected,
    DetectionDone,
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


# ── KeyFrameDetector 프로세스 ──
def run_key_frame_detector(
    client_id: int,
    model_path: str,
):
    logger.info(f"[KeyFrameDetector] 프로세스 시작 (PID: {multiprocessing.current_process().pid})")

    # 수신: RawDataCollected (포트 5555)
    # 발행: Preprocessed (포트 5556)
    zmq_bus = ZmqEventBus(
        sub_addr="tcp://localhost:5555",
        pub_addr="tcp://*:5556",
    )

    detector = KeyFrameDetector(client_id, model_path, zmq_bus)
    zmq_bus.subscribe(RawDataCollected, detector)

    time.sleep(0.5)  # SUB 소켓 연결 대기 (slow joiner 문제)
    zmq_bus.start()

    logger.info("[KeyFrameDetector] 수신 대기 중...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        zmq_bus.close()
        logger.info("[KeyFrameDetector] 프로세스 종료")


# ── FaultFrameDetector 프로세스 ──
def run_fault_frame_detector(
    client_id: int,
    model_path: str,
):
    logger.info(f"[FaultFrameDetector] 프로세스 시작 (PID: {multiprocessing.current_process().pid})")

    # 수신: TargetCreated (포트 5557)
    # 발행: DetectionDone, DefectDetected (포트 5558)
    zmq_bus = ZmqEventBus(
        sub_addr="tcp://localhost:5557",
        pub_addr="tcp://*:5558",
    )

    detector = FaultFrameDetector(client_id, model_path, zmq_bus, default_threshold=0.2)
    zmq_bus.subscribe(TargetCreated, detector)

    time.sleep(0.5)
    zmq_bus.start()

    logger.info("[FaultFrameDetector] 수신 대기 중...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        zmq_bus.close()
        logger.info("[FaultFrameDetector] 프로세스 종료")


# ── 메인 프로세스 ──
def main():
    client_id = 0
    video_path = "C://workspace//stream_inspection//assets//hm_anvil//video//5s, no 14 pallete.mp4"
    key_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//trigger//trigger_yolonas_s_v1.0.onnx"
    fault_frame_model_path = "C://workspace//stream_inspection//assets//hm_anvil//defect//YoloNAS_Seg_S_v1.1.onnx"

    # ── 모델 프로세스 시작 ──
    procs = [
        multiprocessing.Process(
            target=run_key_frame_detector,
            args=(client_id, key_frame_model_path),
            name="KeyFrameDetector",
        ),
        multiprocessing.Process(
            target=run_fault_frame_detector,
            args=(client_id, fault_frame_model_path),
            name="FaultFrameDetector",
        ),
    ]
    for p in procs:
        p.start()
        logger.info(f"{p.name} started (PID: {p.pid})")

    time.sleep(1)  # 모델 프로세스 SUB 소켓 준비 대기

    # ── 메인 프로세스 EventBus ──
    local_bus = EventBus()

    # ZMQ 발행용 (메인 → 모델 프로세스)
    zmq_to_kfd = ZmqEventBus(pub_addr="tcp://*:5555")   # → KeyFrameDetector
    zmq_to_ffd = ZmqEventBus(pub_addr="tcp://*:5557")   # → FaultFrameDetector

    # ZMQ 수신용 (모델 프로세스 → 메인)
    zmq_from_kfd = ZmqEventBus(sub_addr="tcp://localhost:5556")  # ← KeyFrameDetector
    zmq_from_ffd = ZmqEventBus(sub_addr="tcp://localhost:5558")  # ← FaultFrameDetector

    # ── 로컬 서비스 ──
    frame_buffer_manager = FrameBufferManager()
    frame_buffer_manager.add_buffer(client_id)
    frame_buffer_handler = FrameBufferHandler(local_bus, frame_buffer_manager)

    frame_clipper_manager = FrameClipperManager()
    frame_clipper_manager.add_frame_clipper(
        client_id, frame_buffer_manager.get_buffer(client_id)
    )
    frame_clipper_handler = FrameClipperHandler(local_bus, frame_clipper_manager)

    trigger_tracker = TriggerTracker(client_id, local_bus)
    image_saver = ImageSaver(local_bus)
    video_requester = VideoRequester(local_bus, frame_clipper_manager)
    video_saver = VideoSaver(local_bus)
    displayer = Displayer(client_id, local_bus)

    # ── 로컬 구독 ──
    local_bus.subscribe(FrameCaptured, frame_buffer_handler)
    local_bus.subscribe(FrameBuffered, frame_clipper_handler)
    local_bus.subscribe(Preprocessed, trigger_tracker)
    local_bus.subscribe(Preprocessed, displayer)
    local_bus.subscribe(DefectDetected, image_saver)
    local_bus.subscribe(DefectDetected, video_requester)
    local_bus.subscribe(FramePendingDone, video_saver)

    # ── ZMQ 브릿지: 로컬 이벤트 → 모델 프로세스 ──
    # RawDataCollected → KeyFrameDetector 프로세스로 전달
    local_bus.subscribe(RawDataCollected, _ZmqForwarder(zmq_to_kfd))
    # TargetCreated → FaultFrameDetector 프로세스로 전달
    local_bus.subscribe(TargetCreated, _ZmqForwarder(zmq_to_ffd))

    # ── ZMQ 브릿지: 모델 프로세스 → 로컬 이벤트 ──
    # KeyFrameDetector → Preprocessed를 로컬 버스로 전달
    zmq_from_kfd.subscribe(Preprocessed, _LocalForwarder(local_bus))
    # FaultFrameDetector → DetectionDone/DefectDetected를 로컬 버스로 전달
    zmq_from_ffd.subscribe(DetectionDone, _LocalForwarder(local_bus))
    zmq_from_ffd.subscribe(DefectDetected, _LocalForwarder(local_bus))

    zmq_from_kfd.start()
    zmq_from_ffd.start()

    # ── Collector 시작 ──
    collector = AvSourceGateway(client_id, video_path, local_bus)
    collector.connect()
    video_saver.set_input_stream(collector.stream)
    collector.start()

    logger.info("[Main] 파이프라인 실행 중...")
    displayer.show()

    # ── 종료 ──
    collector.disconnect()
    zmq_to_kfd.close()
    zmq_to_ffd.close()
    zmq_from_kfd.close()
    zmq_from_ffd.close()

    for p in procs:
        p.terminate()
    for p in procs:
        p.join(timeout=5)

    logger.info("[Main] 모든 프로세스 종료 완료")


class _ZmqForwarder:
    """로컬 이벤트를 ZMQ로 포워딩하는 어댑터"""

    def __init__(self, zmq_bus: ZmqEventBus):
        self._zmq_bus = zmq_bus

    def handle(self, event):
        self._zmq_bus.publish(event)


class _LocalForwarder:
    """ZMQ에서 수신한 이벤트를 로컬 EventBus로 포워딩하는 어댑터"""

    def __init__(self, local_bus: EventBus):
        self._local_bus = local_bus

    def handle(self, event):
        self._local_bus.publish(event)


if __name__ == "__main__":
    main()
