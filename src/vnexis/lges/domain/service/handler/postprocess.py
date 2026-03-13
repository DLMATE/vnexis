import logging
import os
import time
from pathlib import Path

import av
import cv2

from vnexis.core.common.event import AsyncEventHandler, EventHandler
from vnexis.core.domain.event import DefectDetected, FramePendingDone
from vnexis.core.domain.service.frame_clipper import FrameClipperManager

logger = logging.getLogger(__name__)


class VideoRequester(EventHandler[DefectDetected]):
    def __init__(self, frame_clipper_manager: FrameClipperManager):
        self._frame_clipper_manager = frame_clipper_manager

    def process(self, event: DefectDetected):
        self._frame_clipper_manager.request_clip(event.session_id, event.frame.idx)


class ImageSaver(AsyncEventHandler[DefectDetected]):
    def process(self, event: DefectDetected):
        path = Path("output") / str(event.session_id) / f"{event.frame.idx}.png"
        os.makedirs(path.parent, exist_ok=True)
        cv2.imwrite(path, event.frame.data)


class VideoSaver(AsyncEventHandler[FramePendingDone]):
    def __init__(self, max_workers: int = 1):
        super().__init__(max_workers)
        self._input_stream = None

    def set_input_stream(self, stream: av.VideoStream):
        self._input_stream = stream

    def process(self, event: FramePendingDone):
        try:
            path = Path("output") / str(event.session_id) / f"{event.key_frame_idx}.mp4"
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
