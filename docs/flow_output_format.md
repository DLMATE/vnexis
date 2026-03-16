# 흐름도 출력 형식 목표

## Client 0

```
── VideoReader[0] (local) ──────────────────────────────────
    ├──→ [RawDataCollected] (local)
    │     └──→ KeyFrameDetector[0]
    │           └──→ [KeyFrameDetectionDone] (local)
    │                 ├──→ WebDisplayer
    │                 └──→ TriggerTracker[0]
    │                       └──→ [KeyFrameDetected] (global)
    │                             └──→ FaultFrameDetector
    │                                   └──→ [FaultFrameDetected] (global)
    │                                         └──↳ (extends DefectDetected)
    │                                               ├──→ FaultFrameSaver
    │                                               └──→ VideoRequester
    └──→ [FrameCaptured] (global)
          └──→ FrameBuffering
                └──→ [FrameBuffered] (global)
                      └──→ FrameClipping
                            └──→ [FramePendingDone] (global)
                                  └──→ VideoSaver

```

## Client 1, 2, 3 — 동일 구조

## 표시 규칙

### EventBus 구분

- `══` 굵은 선: Global EventBus
- `──` 일반 선: Local EventBus (handler 소유)

### 이벤트 표기

- `[EventName]`: 이벤트 타입
- `→`: 구독 관계 (이벤트 → 핸들러)
- `→ (global)` / `→ (bus_name)`: 다른 EventBus로 publish됨

### MRO 상속 표시

- `↳ (extends 부모이벤트명) → 구독자들`
- publish된 이벤트가 부모 이벤트를 상속하고, 부모 이벤트에 구독자가 있을 때 표시
- 예: `FaultFrameDetected`는 `DefectDetected`를 상속 → `DefectDetected` 구독자도 호출됨

### 핸들러 이름 규칙

- session_id가 있는 핸들러: `ClassName[session_id]` (예: `KeyFrameDetector[0]`)
- session_id가 없는 핸들러: `ClassName` (예: `FrameBuffering`)
