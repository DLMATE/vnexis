# vnexis

## Core Concept

### Detector

ai 추론기

### Visualizer

추론 결과 시각화

### Publisher

추론 결과 전달기

#### 할일

1. FRAME BUFFER MANAGER N개 세션 프레임 받도록 수정
2. VIDEO REQUESTER는 FRAME BUFFER MANAGER 주입
3. STREAM, BATCH, CALL BY 3개의 형태로 만들기.
4. 외부와의 통신 만들기. GRPC, HTTP, WebSocket 등
