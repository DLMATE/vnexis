import logging
import pickle
import threading
import uuid
from collections import defaultdict
from dataclasses import fields, is_dataclass
from multiprocessing import shared_memory

import av
import numpy as np
import zmq

from vnexis.common.event import Event, EventHandler

logger = logging.getLogger(__name__)


class ShmBlock:
    """공유 메모리에 저장된 ndarray 참조"""

    def __init__(self, name: str, shape: tuple, dtype: str):
        self.name = name
        self.shape = shape
        self.dtype = dtype


def _extract_ndarrays(obj, shm_blocks: list[shared_memory.SharedMemory]) -> object:
    """dataclass/ndarray/av.Packet을 재귀 탐색하여 직렬화 가능 형태로 치환"""
    if isinstance(obj, av.Packet):
        return None

    if isinstance(obj, np.ndarray):
        if obj.nbytes == 0:
            return ShmBlock(name="", shape=obj.shape, dtype=str(obj.dtype))
        shm = shared_memory.SharedMemory(create=True, size=obj.nbytes)
        buf = np.ndarray(obj.shape, dtype=obj.dtype, buffer=shm.buf)
        buf[:] = obj  # 최초 1회 복사 (발행 측)
        shm_blocks.append(shm)
        return ShmBlock(name=shm.name, shape=obj.shape, dtype=str(obj.dtype))

    if isinstance(obj, (list, tuple)):
        converted = [_extract_ndarrays(item, shm_blocks) for item in obj]
        return type(obj)(converted)

    if is_dataclass(obj) and not isinstance(obj, type):
        new_fields = {}
        for f in fields(obj):
            val = getattr(obj, f.name)
            new_fields[f.name] = _extract_ndarrays(val, shm_blocks)
        # frozen dataclass는 __init__으로 재생성
        try:
            return type(obj)(**new_fields)
        except TypeError:
            return obj

    return obj


def _restore_ndarrays(obj, shm_refs: list[shared_memory.SharedMemory]) -> object:
    """ShmBlock → ndarray, AvPacketBytes → av.Packet 복원"""
    if isinstance(obj, ShmBlock):
        if obj.name == "":
            return np.empty(obj.shape, dtype=np.dtype(obj.dtype))
        shm = shared_memory.SharedMemory(name=obj.name, create=False)
        shm_refs.append(shm)
        # buffer를 직접 참조 — 복사 없음 (zero-copy)
        arr = np.ndarray(obj.shape, dtype=np.dtype(obj.dtype), buffer=shm.buf)
        return arr

    if isinstance(obj, (list, tuple)):
        restored = [_restore_ndarrays(item, shm_refs) for item in obj]
        return type(obj)(restored)

    if is_dataclass(obj) and not isinstance(obj, type):
        new_fields = {}
        for f in fields(obj):
            val = getattr(obj, f.name)
            new_fields[f.name] = _restore_ndarrays(val, shm_refs)
        try:
            return type(obj)(**new_fields)
        except TypeError:
            return obj

    return obj


class ZmqEventBus:
    """
    ZeroMQ PUB/SUB + SharedMemory 기반 EventBus.

    - ndarray 데이터: SharedMemory로 zero-copy 전달
    - 이벤트 메타데이터: ZeroMQ PUB/SUB로 전달
    - EventBus와 동일한 인터페이스 (subscribe/publish)

    사용법:
        # 발행 프로세스
        bus = ZmqEventBus(pub_addr="tcp://*:5555")
        bus.publish(event)

        # 구독 프로세스
        bus = ZmqEventBus(sub_addr="tcp://localhost:5555")
        bus.subscribe(SomeEvent, handler)
        bus.start()  # 수신 루프 시작
    """

    def __init__(
        self,
        pub_addr: str | None = None,
        sub_addr: str | None = None,
    ):
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._ctx = zmq.Context()
        self._shm_blocks: list[shared_memory.SharedMemory] = []  # 발행 측 shm 추적
        self._shm_refs: list[shared_memory.SharedMemory] = []  # 구독 측 shm 추적
        self._listening = False

        # PUB 소켓 (발행용)
        self._pub = None
        if pub_addr:
            self._pub = self._ctx.socket(zmq.PUB)
            self._pub.bind(pub_addr)

        # SUB 소켓 (구독용)
        self._sub = None
        self._sub_addr = sub_addr
        if sub_addr:
            self._sub = self._ctx.socket(zmq.SUB)
            self._sub.connect(sub_addr)

    def subscribe(self, event: type[Event], event_handler: EventHandler):
        topic = event.__name__
        self._subscribers[topic].append(event_handler)
        if self._sub:
            self._sub.setsockopt_string(zmq.SUBSCRIBE, topic)

    def publish(self, event: Event):
        topic = event.__class__.__name__

        # 로컬 핸들러 실행
        for handler in self._subscribers[topic]:
            handler.handle(event)

        # ZMQ 발행
        if self._pub:
            shm_blocks: list[shared_memory.SharedMemory] = []
            extracted = _extract_ndarrays(event, shm_blocks)
            payload = pickle.dumps(extracted)

            self._pub.send_string(topic, zmq.SNDMORE)
            self._pub.send(payload, copy=False)  # zero-copy 송신

            self._shm_blocks.extend(shm_blocks)

    def start(self):
        """구독 수신 루프를 백그라운드 스레드로 시작"""
        if not self._sub:
            return
        self._listening = True
        self._listener = threading.Thread(target=self._listen, daemon=True)
        self._listener.start()

    def _listen(self):
        while self._listening:
            try:
                topic = self._sub.recv_string()
                payload = self._sub.recv(copy=False)  # zero-copy 수신

                extracted = pickle.loads(payload.bytes)
                shm_refs: list[shared_memory.SharedMemory] = []
                event = _restore_ndarrays(extracted, shm_refs)
                self._shm_refs.extend(shm_refs)

                for handler in self._subscribers.get(topic, []):
                    handler.handle(event)
            except zmq.ZMQError:
                break
            except Exception as e:
                logger.error(f"[ZmqEventBus] Error: {e}", exc_info=True)

    def stop(self):
        self._listening = False

    def cleanup(self):
        """공유 메모리 정리"""
        for shm in self._shm_blocks:
            try:
                shm.close()
                shm.unlink()
            except Exception:
                pass
        for shm in self._shm_refs:
            try:
                shm.close()
            except Exception:
                pass
        self._shm_blocks.clear()
        self._shm_refs.clear()

    def close(self):
        self.stop()
        self.cleanup()
        if self._pub:
            self._pub.close()
        if self._sub:
            self._sub.close()
        self._ctx.term()
