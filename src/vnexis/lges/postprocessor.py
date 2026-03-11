import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import av
import cv2
import numpy as np

from vnexis.common.event import EventHandler
from vnexis.core.event import DefectDetected, FramePendingDone
from vnexis.core.service.frame_clipper import FrameClipperManager

logger = logging.getLogger(__name__)


class VideoRequester(EventHandler):
    def __init__(self, event_bus, frame_clipper_manager: FrameClipperManager):
        self._event_bus = event_bus
        self._frame_clipper_manager = frame_clipper_manager

    def handle(self, event: DefectDetected):
        self._frame_clipper_manager.request_clip(
            event.client_id, event.session_id, event.target.frame.idx
        )


class ImageSaver(EventHandler):
    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="ImageSaver"
        )

    def handle(self, event: DefectDetected):
        self._executor.submit(
            self.save_image,
            event.client_id,
            event.target.frame.idx,
            event.target.frame.data,
        )

    def save_image(self, client_id: int, frame_idx: int, img: np.ndarray):
        path = Path("output") / str(client_id) / f"{frame_idx}.png"
        os.makedirs(path.parent, exist_ok=True)
        cv2.imwrite(path, img)


class VideoSaver(EventHandler):
    def __init__(self, event_bus):
        super().__init__(event_bus)
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="VideoSaver"
        )
        self._input_stream = None

    def set_input_stream(self, stream: av.VideoStream):
        self._input_stream = stream

    def handle(self, event: FramePendingDone):
        logger.info(
            f"[AvVideoSaver] video save requested. client_id: {event.client_id}, key frame idx: {event.key_frame_idx}"
        )
        self._executor.submit(self._process, event)

    def _process(self, event: FramePendingDone):
        try:
            path = Path("output") / str(event.client_id) / f"{event.key_frame_idx}.mp4"
            os.makedirs(path.parent, exist_ok=True)

            output_container = av.open(path, mode="w")
            output_stream = output_container.add_stream_from_template(
                self._input_stream
            )
            # output_stream.codec_tag = "hvc1"
            output_stream.codec_tag = self._input_stream.codec_tag
            logger.info(
                f"{event.key_frame_idx}'s input stream.\ntimebase: {self._input_stream.time_base}\nstarttime: {self._input_stream.start_time}\nduration: {self._input_stream.duration}, "
            )
            logger.info(
                f"{event.key_frame_idx}'s output stream.\ntimebase: {output_stream.time_base}\nstarttime: {output_stream.start_time}\nduration: {output_stream.duration}, "
            )

            logger.info(
                f"[AvVideoSaver] video save started: {event.key_frame_idx}. len: {len(event.frames)}"
            )
            output_stream.time_base = self._input_stream.time_base
            # output_stream.duration = event.frames[0].data.duration * len(event.frames)
            # output_stream.start_time = event.frames[0].data.dts

            start = time.perf_counter()
            dts_offset = event.frames[0].raw.dts
            for frame in event.frames:
                src = frame.raw
                packet = av.Packet(bytes(src))
                # logger.info(
                #     f"src.is_keyframe={src.is_keyframe}, src.time_base={src.time_base}, src.duration={src.duration}"
                # )
                packet.time_base = src.time_base
                packet.is_keyframe = src.is_keyframe
                packet.duration = src.duration
                packet.pts = src.pts - dts_offset
                packet.dts = src.dts - dts_offset
                packet.stream = output_stream
                output_container.mux(packet)
            end = time.perf_counter()
            logger.info(
                f"[AvVideoSaver] video saved: {event.key_frame_idx} ({end - start:.2f}s)"
            )
        except Exception as e:
            logger.exception(e)
        finally:
            output_container.close()
