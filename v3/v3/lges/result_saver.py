from common.event import EventBus, EventHandler
from lges.event import PendingDone
from core.event import DefectDetected
from concurrent.futures import ThreadPoolExecutor
import cv2
import os
from common.utils import draw_text
import logging
import time
import av


logger = logging.getLogger(__name__)


class ImageSaver(EventHandler):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="ImageSaver"
        )

    def handle(self, event: DefectDetected):
        self._executor.submit(self._process, event)

    def _process(self, event: DefectDetected):
        os.makedirs("output", exist_ok=True)
        cv2.imwrite(
            f"output/{event.frame.idx}.jpg",
            draw_text(event.frame.data, f"idx: {event.frame.idx}"),
        )
        logger.info(f"[ImageSaver] image saved: {event.frame.idx}")


class VideoSaver(EventHandler):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="VideoSaver"
        )

    def handle(self, event: DefectDetected):
        logger.info(f"[VideoSaver] video save requested: {event.key_idx}")
        self._executor.submit(self._process, event)

    def _process(self, event: PendingDone):
        try:
            os.makedirs("output", exist_ok=True)
            h, w = event.frames[0].data.shape[:2]
            writer = cv2.VideoWriter(
                f"output/{event.key_idx}.mp4",
                cv2.VideoWriter_fourcc(*"avc1"),
                30,
                (w, h),
            )
            logger.info(f"[VideoSaver] video save started: {event.key_idx}")
            start = time.perf_counter()
            for frame in event.frames:
                writer.write(frame.data)
            end = time.perf_counter()
            logger.info(
                f"[VideoSaver] video saved: {event.key_idx} ({end - start:.2f}s)"
            )
        except Exception as e:
            logger.error(e)
        finally:
            writer.release()


class AvVideoSaver(EventHandler):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="VideoSaver"
        )
        self._input_stream = None

    def set_input_stream(self, stream: av.VideoStream):
        self._input_stream = stream

    def handle(self, event: DefectDetected):
        logger.info(f"[AvVideoSaver] video save requested: {event.key_idx}")
        self._executor.submit(self._process, event)

    def _process(self, event: PendingDone):
        try:
            os.makedirs("output", exist_ok=True)
            output_container = av.open(f"output/{event.key_idx}.mp4", mode="w")
            output_stream = output_container.add_stream_from_template(
                self._input_stream
            )
            # output_stream.codec_tag = "hvc1"
            output_stream.codec_tag = self._input_stream.codec_tag
            logger.info(
                f"{event.key_idx}'s input stream.\ntimebase: {self._input_stream.time_base}\nstarttime: {self._input_stream.start_time}\nduration: {self._input_stream.duration}, "
            )
            logger.info(
                f"{event.key_idx}'s output stream.\ntimebase: {output_stream.time_base}\nstarttime: {output_stream.start_time}\nduration: {output_stream.duration}, "
            )

            logger.info(
                f"[AvVideoSaver] video save started: {event.key_idx}. len: {len(event.frames)}"
            )
            output_stream.time_base = self._input_stream.time_base
            # output_stream.duration = event.frames[0].data.duration * len(event.frames)
            # output_stream.start_time = event.frames[0].data.dts

            start = time.perf_counter()
            dts_offset = event.frames[0].data.dts
            for frame in event.frames:
                src = frame.data
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
                f"[AvVideoSaver] video saved: {event.key_idx} ({end - start:.2f}s)"
            )
        except Exception as e:
            logger.exception(e)
        finally:
            output_container.close()
