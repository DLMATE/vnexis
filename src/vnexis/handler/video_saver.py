import logging
import os
import time
from pathlib import Path
from typing import Literal

import av

from vnexis.event import EventBus, FramePendingDone
from vnexis.handler.handler import FramePendingDoneHandler

logger = logging.getLogger(__name__)


class VideoSaver(FramePendingDoneHandler):
    def __init__(
        self,
        save_dir: Path,
        event_bus: EventBus | None = None,
        session_id: int | None = None,
        max_workers: int = 1,
        type: Literal["thread", "process"] = "thread",
    ):
        super().__init__(event_bus, session_id, max_workers, type)
        self._save_dir = save_dir

    def process(self, event: FramePendingDone):
        try:
            path = self._save_dir / str(event.session_id) / f"{event.key_frame_idx}.mp4"
            os.makedirs(path.parent, exist_ok=True)

            output_container = av.open(path, mode="w")
            output_stream = output_container.add_stream_from_template(
                event.av_input_stream
            )
            # output_stream.codec_tag = "hvc1"
            output_stream.codec_tag = event.av_input_stream.codec_tag
            logger.info(
                f"{event.key_frame_idx}'s input stream.\ntimebase: {event.av_input_stream.time_base}\nstarttime: {event.av_input_stream.start_time}\nduration: {event.av_input_stream.duration}, "
            )
            logger.info(
                f"{event.key_frame_idx}'s output stream.\ntimebase: {output_stream.time_base}\nstarttime: {output_stream.start_time}\nduration: {output_stream.duration}, "
            )

            logger.info(
                f"[AvVideoSaver] video save started: {event.key_frame_idx}. len: {len(event.frames)}"
            )
            output_stream.time_base = event.av_input_stream.time_base
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
