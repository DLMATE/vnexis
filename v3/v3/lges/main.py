from .video_capture import VideoCapture, AvVideoCapture
from .key_frame_detector import KeyFrameDetector
from .defect_detector import DefectDetector
from .displayer import Displayer, EventFrameStreamTrack, WebrtcStreamPublisher
from .frame_buffer import (
    FrameBuffer,
    FrameClipper,
    FrameBufferHandler,
    FrameClipperHandler,
)
from contextlib import asynccontextmanager
from .result_saver import ImageSaver, VideoSaver, AvVideoSaver
from common.event import EventBus
from core.dto import Source
from .event import (
    FrameCaptured,
    KeyFrameDetectionDone,
    KeyFrameDetected,
    FrameBuffered,
    PendingDone,
)
from core.event import DefectDetected
import time
import cv2
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OfferRequest(BaseModel):
    sdp: str
    type: str


class OfferResponse(BaseModel):
    sdp: str
    type: str


event_bus = EventBus()
source = Source(path="/Users/gwonil/RTM/data/LGES/hm_anvil/video/5s, no 14 pallete.mp4")
# source = Source(path="/Users/gwonil/RTM/project/sq_vd3/v3/output/17.mp4")

frame_buffer = FrameBuffer()
frame_clipper = FrameClipper(frame_buffer)
event_frame_stream_track = EventFrameStreamTrack(event_bus)

# video_capture = VideoCapture(source, event_bus)
video_capture = AvVideoCapture(source, event_bus)
key_frame_detector = KeyFrameDetector(event_bus)
displayer = Displayer(event_bus)
stream_publisher = WebrtcStreamPublisher(event_frame_stream_track)

defect_detector = DefectDetector(event_bus, frame_clipper)
image_saver = ImageSaver(event_bus)
# video_saver = VideoSaver(event_bus)
video_saver = AvVideoSaver(event_bus)

frame_buffer_handler = FrameBufferHandler(event_bus, frame_buffer)
frame_clipper_handler = FrameClipperHandler(event_bus, frame_clipper)

event_bus.subscribe(FrameCaptured, key_frame_detector)
event_bus.subscribe(KeyFrameDetectionDone, displayer)
event_bus.subscribe(KeyFrameDetectionDone, event_frame_stream_track)
event_bus.subscribe(KeyFrameDetected, defect_detector)
event_bus.subscribe(FrameCaptured, frame_buffer_handler)
event_bus.subscribe(FrameBuffered, frame_clipper_handler)
event_bus.subscribe(DefectDetected, image_saver)
event_bus.subscribe(PendingDone, video_saver)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup")
    video_capture.connect()
    video_saver.set_input_stream(video_capture.stream)
    video_capture.start()
    yield
    # shutdown
    video_capture.disconnect()
    logger.info("All connections closed")


app = FastAPI(lifespan=lifespan)


@app.post("/offer")
async def offer(
    request: OfferRequest,
) -> OfferResponse:
    output = await stream_publisher.publish(
        connection_info={"sdp": request.sdp, "type": request.type}
    )
    return OfferResponse.model_validate(output)


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "client.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text("utf-8"), status_code=200)
    else:
        return HTMLResponse(
            content="<h1>client.html not found.</h1>",
            status_code=404,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup")
    video_capture.connect()
    video_capture.start()
    yield
    # shutdown
    video_capture.disconnect()
    logger.info("All connections closed")


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


# def main():
#     try:
#         video_capture.connect()
#         video_saver.set_input_stream(video_capture.stream)
#         video_capture.start()
#         displayer.show()

#         while displayer.is_running:
#             time.sleep(0.1)
#     except Exception as e:
#         logger.error(e)
#     finally:
#         video_capture.stop()
#         video_capture.disconnect()
#         cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
