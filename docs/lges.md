# LGES 프로젝트

Vnexis Core를 활용한 LGES 제조 라인 결함 검출 시스템.

## 개요

LGES 프로젝트는 제조 라인의 영상을 실시간으로 분석하여 트리거(키프레임) 검출 및 결함 검출을 수행합니다. Core의 추상 클래스를 구현하여 ONNX 모델 기반 추론 파이프라인을 구성합니다.

## Core 확장 구조

```
Core 추상 클래스                    LGES 구현체
─────────────────                  ─────────────────
SourceGateway           ──→        AvSourceGateway (PyAV 영상 수집)
Preprocessor            ──→        KeyFrameDetector (ONNX 트리거 검출)
TargetCreator           ──→        TriggerTracker (상태 머신)
Detector                ──→        FaultFrameDetector (ONNX 결함 검출)
RawData                 ──→        LgesRawData (Frame 포함)
Metadata                ──→        LgesMetadata (cell_id, detect_time)
PreprocessResult        ──→        LgesPreprocessResult (검출 결과 DTO)
DetectResult            ──→        LgesDetectResult (결함 검출 결과 DTO)
```

## 디렉토리 구조

```
src/vnexis/lges/
├── dto.py              # LGES 데이터 모델 (Core DTO 확장)
├── collector.py        # AvSourceGateway (PyAV 기반 영상 수집)
├── preprocessor.py     # KeyFrameDetector (트리거 ONNX 추론)
├── target_creator.py   # TriggerTracker (트리거 상태 머신)
├── detector.py         # FaultFrameDetector (결함 ONNX 추론)
├── displayer.py        # Displayer (OpenCV GUI)
├── web_displayer.py    # WebDisplayer (FastAPI MJPEG 스트리밍)
├── postprocessor.py    # ImageSaver, VideoRequester, VideoSaver
├── main.py             # 단일 프로세스 실행
├── main2.py            # 멀티 프로세스 실행
├── main3.py            # ZMQ 분산 실행
└── main4.py            # FastAPI 웹 모니터링 실행
```

## 데이터 모델 (`dto.py`)

Core의 빈 dataclass를 LGES 도메인에 맞게 확장합니다.

```python
class LgesRawData(RawData):
    frame: Frame                          # 수집된 프레임

class LgesMetadata(Metadata):
    cell_id: str                          # 셀 ID (UUID)
    key_frame_detect_time: float          # 키프레임 검출 소요 시간

class DetectionResultDto:
    boxes: np.ndarray                     # 바운딩 박스 [N, 4]
    labels: np.ndarray                    # 클래스 라벨 [N]
    scores: np.ndarray                    # 신뢰도 점수 [N]
    masks: np.ndarray                     # 세그멘테이션 마스크
    img_size: tuple[int, int]             # 모델 입력 크기

class LgesPreprocessResult(PreprocessResult):
    frame: Frame
    metadata: LgesMetadata
    key_frame_detection_result: DetectionResultDto

class LgesDetectResult(DetectResult):
    fault_frame_detection_result: DetectionResultDto
    time: float
```

## 파이프라인 구현체

### 1. AvSourceGateway (`collector.py`)

Core의 `SourceGateway`를 구현. PyAV 라이브러리로 영상 파일을 읽어 프레임을 수집합니다.

- `connect()`: `av.open()`으로 영상 파일 열기
- `collect()`: 패킷 단위 디먹싱 → 디코딩 → `LgesRawData` yield
- `FrameCaptured` 이벤트도 직접 발행 (프레임 버퍼용)

### 2. KeyFrameDetector (`preprocessor.py`)

Core의 `Preprocessor`를 구현. ONNX 모델(YoloNAS)로 트리거(키프레임)를 검출합니다.

```
입력: LgesRawData (프레임)
처리: 리사이즈 → ONNX 추론 → 임계값 필터링
출력: LgesPreprocessResult (프레임 + 메타데이터 + 검출 결과)
```

- `CUDAExecutionProvider`로 GPU 추론
- 클래스별 신뢰도 임계값 적용
- 추론 시간을 메타데이터에 기록

### 3. TriggerTracker (`target_creator.py`)

Core의 `TargetCreator`를 구현. 트리거의 움직임을 상태 머신으로 추적합니다.

```
상태 전이:
  UNKNOWN → UP → UPSTABLE → DOWN → DOWNSTABLE
                                      ↓
                               Target 생성 (검출 대상으로 판정)
```

- 트리거 바운딩 박스의 y좌표 변화를 모니터링
- 슬라이딩 윈도우(num_watch=10)로 이동 방향 판단
- `DOWNSTABLE` 전이 시 `Target`을 반환하여 검출 단계로 전달

### 4. FaultFrameDetector (`detector.py`)

Core의 `Detector`를 구현. ONNX 모델(YoloNAS-Seg)로 결함을 검출합니다.

```
입력: Target (프레임 + 메타데이터)
처리: 리사이즈 → ONNX 추론 → 임계값 필터링
출력: (is_defect, LgesDetectResult)
```

- 세그멘테이션 마스크 포함
- 검출 결과가 있으면 `is_defect=True` → `DefectDetected` 이벤트 발행

### 5. 후처리 (`postprocessor.py`)

결함 검출 후의 처리를 담당합니다.

| 클래스 | 구독 이벤트 | 동작 |
|---|---|---|
| `ImageSaver` | `DefectDetected` | 결함 이미지를 PNG로 저장 |
| `VideoRequester` | `DefectDetected` | FrameClipper에 클립 요청 |
| `VideoSaver` | `FramePendingDone` | 수집된 프레임을 MP4로 저장 |

- `ImageSaver`: `output/{client_id}/{frame_idx}.png`
- `VideoSaver`: PyAV로 원본 패킷을 재먹싱 (재인코딩 없음)

### 6. Displayer (`displayer.py`)

OpenCV 기반 실시간 시각화. 메인 스레드에서 실행됩니다.

- 검출 바운딩 박스, 라벨, 신뢰도 표시
- 프레임 인덱스, 셀 ID, FPS, 검출 시간 오버레이
- ESC 키로 종료

### 7. WebDisplayer (`web_displayer.py`)

FastAPI + MJPEG 스트리밍 기반 웹 디스플레이어. 데몬 스레드에서 실행됩니다.

- `GET /` → 전체 클라이언트 모니터링 대시보드
- `GET /stream/{client_id}` → 클라이언트별 MJPEG 스트림
- `GET /api/clients` → 클라이언트 목록 및 메타데이터
- 클라이언트별 FPS 측정 및 표시
- 반응형 그리드 레이아웃 (자동 카드 추가/제거)

## 실행 방식

### main.py — 단일 프로세스

```bash
python -m vnexis.lges.main
```

- 4개 클라이언트를 하나의 프로세스에서 실행
- 글로벌 EventBus 공유
- OpenCV GUI로 client 0만 표시
- **가장 빠름** (IPC 오버헤드 없음, ONNX/OpenCV는 GIL 릴리스)

### main2.py — 멀티 프로세스

```bash
python -m vnexis.lges.main2
```

- 클라이언트당 독립 프로세스
- 프로세스별 독립 EventBus
- 장애 격리 가능
- GPU 메모리 x N 사용

### main3.py — ZMQ 분산

```bash
python -m vnexis.lges.main3
```

- KeyFrameDetector, FaultFrameDetector를 별도 프로세스로 분리
- ZmqEventBus + SharedMemory로 zero-copy 통신
- 포트: 5555/5556 (KeyFrameDetector), 5557/5558 (FaultFrameDetector)
- `_ZmqForwarder`, `_LocalForwarder`로 이벤트 브릿지

### main4.py — 웹 모니터링

```bash
pip install fastapi uvicorn
python -m vnexis.lges.main4
```

- 단일 프로세스 + FastAPI 웹 서버
- `http://localhost:8080`에서 전체 클라이언트 모니터링
- uvicorn이 메인 스레드 점유 (논블로킹)

## 실행 방식 비교

| | main | main2 | main3 | main4 |
|---|---|---|---|---|
| 프로세스 | 1개 | N개 | 3개 | 1개 |
| EventBus | 글로벌 1개 | 프로세스별 | ZMQ 브릿지 | 로컬 1개 |
| 디스플레이 | OpenCV | OpenCV (0번만) | OpenCV | 웹 (MJPEG) |
| IPC 오버헤드 | 없음 | 없음 | ZMQ + SHM | 없음 |
| 장애 격리 | 없음 | 클라이언트별 | 모델별 | 없음 |
| 추천 상황 | 기본 | 독립 운영 | GPU 분리 | 원격 모니터링 |

## 의존성

```
onnxruntime-gpu    # ONNX 추론
opencv-python      # 영상 처리 / GUI
av                 # PyAV 영상 디코딩
numpy              # 수치 연산
pyzmq              # ZeroMQ (main3)
fastapi            # 웹 서버 (main4)
uvicorn            # ASGI 서버 (main4)
```
