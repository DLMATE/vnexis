# Vnexis Core

영상 기반 검사 시스템을 위한 이벤트 드리븐 파이프라인 프레임워크.

## 개요

Vnexis Core는 영상 수집 → 전처리 → 검출 → 후처리로 이어지는 파이프라인을 이벤트 기반으로 구성할 수 있는 프레임워크입니다. 각 단계는 추상 클래스로 정의되어 있으며, 프로젝트별로 구현체를 작성하여 사용합니다.

## 아키텍처

```
SourceGateway.collect()
  │ RawDataCollected
  ├──→ FrameBufferHandler (프레임 링 버퍼 저장)
  └──→ Preprocessor.preprocess()
         │ Preprocessed
         └──→ TargetCreator.create_target()
                │ TargetCreated (조건 만족 시)
                └──→ Detector.detect()
                       │ DetectionDone
                       └──→ DefectDetected (결함 발견 시)
```

## 디렉토리 구조

```
src/vnexis/
├── common/
│   ├── event.py           # Event, EventBus, EventHandler
│   ├── task.py            # Task 추상 클래스
│   ├── utils.py           # 이미지/박스 유틸리티
│   └── zmq_event_bus.py   # ZeroMQ + SharedMemory 기반 EventBus
│
├── core/
│   ├── dto.py             # RawData, Frame, Target, Result 데이터 클래스
│   ├── event.py           # 파이프라인 이벤트 정의
│   └── service/
│       ├── source_gateway.py   # 영상 수집
│       ├── preprocessor.py     # 전처리 + 타겟 생성
│       ├── detector.py         # 검출
│       ├── frame_buffer.py     # 프레임 링 버퍼
│       └── frame_clipper.py    # 프레임 클리핑
│
└── infra/
    └── source_gateway/
        └── av_source_gateway.py  # PyAV 기반 구현
```

## 핵심 컴포넌트

### 1. EventBus (`common/event.py`)

모든 컴포넌트 간 통신의 핵심. Pub/Sub 패턴으로 느슨한 결합을 유지합니다.

```python
event_bus = EventBus()
event_bus.subscribe(RawDataCollected, handler)
event_bus.publish(RawDataCollected(...))
```

- `Event`: 불변(frozen) dataclass. `timestamp` 자동 생성.
- `EventHandler`: 추상 클래스. `handle(event)` 구현 필요.
- `EventBus`: 이벤트 클래스 이름으로 핸들러를 매핑.

### 2. SourceGateway (`core/service/source_gateway.py`)

영상/데이터 소스를 추상화합니다. 데몬 스레드에서 데이터를 수집하고 `RawDataCollected` 이벤트를 발행합니다.

```python
class SourceGateway(ABC):
    def connect(self): ...
    def disconnect(self): ...
    def collect(self) -> Iterator[RawData | None]: ...
```

- `source_type`: `rtsp`, `file`, `nas`, `camera`, `db`
- 데몬 스레드에서 `collect()` 반복 호출 → `RawDataCollected` 발행

### 3. Preprocessor (`core/service/preprocessor.py`)

원시 데이터를 전처리합니다. `ThreadPoolExecutor`로 비동기 실행됩니다.

```python
class Preprocessor(EventHandler, ABC):
    def preprocess(self, raw_data: RawData) -> PreprocessResult: ...
```

- `RawDataCollected` 수신 → `preprocess()` 실행 → `Preprocessed` 발행

### 4. TargetCreator (`core/service/preprocessor.py`)

전처리 결과를 기반으로 검출 대상 여부를 판단합니다.

```python
class TargetCreator(EventHandler, ABC):
    def create_target(self, raw_data, preprocess_result) -> Target | None: ...
```

- `Preprocessed` 수신 → `create_target()` 실행 → 조건 만족 시 `TargetCreated` 발행
- `None` 반환 시 이벤트 미발행 (필터링)

### 5. Detector (`core/service/detector.py`)

검출 대상에 대해 추론을 수행합니다.

```python
class Detector(EventHandler, ABC):
    def detect(self, target: Target) -> tuple[bool, DetectResult]: ...
```

- `TargetCreated` 수신 → `detect()` 실행 → `DetectionDone` 항상 발행
- `is_defect=True`이면 `DefectDetected` 추가 발행

### 6. FrameBuffer (`core/service/frame_buffer.py`)

프레임을 링 버퍼에 저장합니다. 클라이언트별 독립 관리.

- `FrameBuffer`: `deque` 기반 링 버퍼 (기본 300프레임 = 30fps x 10초)
- `FrameBufferManager`: 클라이언트별 버퍼 관리
- `FrameBufferHandler`: `FrameCaptured` → 버퍼 저장 → `FrameBuffered` 발행

### 7. FrameClipper (`core/service/frame_clipper.py`)

키프레임 전후 N초 분량의 프레임을 수집합니다.

- `PendingClip`: 수집 상태 추적 (대기 중인 클립)
- `FrameClipper`: 클립 요청/완료 관리
- `FrameClipperHandler`: `FrameBuffered` 수신 → 완료 시 `FramePendingDone` 발행

## 이벤트 흐름

| 이벤트 | 발행 주체 | 주요 필드 |
|---|---|---|
| `RawDataCollected` | SourceGateway | `client_id`, `session_id`, `raw_data` |
| `FrameCaptured` | SourceGateway | `client_id`, `session_id`, `frame` |
| `FrameBuffered` | FrameBufferHandler | `client_id`, `session_id`, `frame` |
| `Preprocessed` | Preprocessor | `client_id`, `session_id`, `raw_data`, `result` |
| `TargetCreated` | TargetCreator | `client_id`, `session_id`, `raw_data`, `preprocess_result`, `target` |
| `DetectionDone` | Detector | 위 + `detect_result` |
| `DefectDetected` | Detector | DetectionDone 상속 |
| `FramePendingDone` | FrameClipperHandler | `client_id`, `session_id`, `key_frame_idx`, `frames` |

## 데이터 모델 (`core/dto.py`)

```python
@dataclass
class RawData: ...              # 원시 데이터 (프로젝트별 확장)

@dataclass
class Frame:                    # 프레임
    idx: int                    # 프레임 인덱스
    raw: str | bytes | ...      # 원본 데이터
    data: bytes | np.ndarray    # 디코딩된 이미지

@dataclass
class Metadata: ...             # 메타데이터 (프로젝트별 확장)

@dataclass
class Target:                   # 검출 대상
    frame: Frame
    metadata: Metadata

@dataclass
class PreprocessResult: ...     # 전처리 결과 (프로젝트별 확장)
class DetectResult: ...         # 검출 결과 (프로젝트별 확장)
class PostprocessResult: ...    # 후처리 결과 (프로젝트별 확장)
```

## 설계 원칙

1. **이벤트 드리븐**: 모든 컴포넌트는 EventBus로 통신. 직접 참조 없음.
2. **Template Method**: Core가 알고리즘 골격 정의, 프로젝트별 구현체가 세부 로직 구현.
3. **비동기 처리**: 블로킹 작업(추론 등)은 `ThreadPoolExecutor`로 비동기 실행.
4. **멀티 클라이언트**: `client_id`로 여러 영상 소스를 동시 처리.
5. **확장 가능**: `RawData`, `Metadata`, `Result` 등은 빈 dataclass로 정의 → 프로젝트별 필드 추가.

## 실행 모드

| 모드 | 설명 | EventBus |
|---|---|---|
| 단일 프로세스 | 모든 컴포넌트가 하나의 프로세스 | 인메모리 EventBus |
| 멀티 프로세스 | 클라이언트별 독립 프로세스 | 프로세스별 독립 EventBus |
| 분산 (ZMQ) | 모델 추론을 별도 프로세스로 분리 | ZmqEventBus + SharedMemory |

## ZmqEventBus (`common/zmq_event_bus.py`)

프로세스 간 이벤트 통신을 위한 ZeroMQ 기반 EventBus.

- `ndarray` → SharedMemory (zero-copy)
- 메타데이터 → ZeroMQ PUB/SUB (pickle 직렬화)
- `av.Packet` → `None`으로 치환 (pickle 불가)
- 빈 ndarray (`nbytes == 0`) → SharedMemory 없이 직접 전달

```python
# 발행 프로세스
bus = ZmqEventBus(pub_addr="tcp://*:5555")
bus.publish(event)

# 구독 프로세스
bus = ZmqEventBus(sub_addr="tcp://localhost:5555")
bus.subscribe(SomeEvent, handler)
bus.start()
```
