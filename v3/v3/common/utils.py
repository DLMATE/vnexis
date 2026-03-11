import cv2
import numpy as np


def draw_boxes(
    image: np.ndarray,
    boxes: np.ndarray,
    labels: list[str] | np.ndarray | None = None,
    scores: np.ndarray | None = None,
    color: tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
    font_scale: float = 0.5,
) -> np.ndarray:
    """바운딩 박스 그리기.

    Args:
        image: BGR 이미지 (복사본 반환, 원본 변형 없음).
        boxes: (N, 4) [x1, y1, x2, y2] 배열.
        labels: 클래스명 리스트 또는 int 배열.
        scores: 신뢰도 배열.
        color: BGR 색상.
        thickness: 선 두께.
        font_scale: 글자 크기.

    Returns:
        박스가 그려진 새 이미지.
    """
    result = image.copy()
    if len(boxes) == 0:
        return result

    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(result, (x1, y1), (x2, y2), color, thickness)

        text_parts = []
        if labels is not None:
            label = labels[i] if isinstance(labels, list) else str(int(labels[i]))
            text_parts.append(label)
        if scores is not None:
            text_parts.append(f"{scores[i]:.2f}")

        if text_parts:
            text = ": ".join(text_parts)
            (tw, th), _ = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
            )
            cv2.rectangle(result, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
            cv2.putText(
                result,
                text,
                (x1, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (255, 255, 255),
                thickness,
            )

    return result


def draw_masks(
    image: np.ndarray,
    masks: np.ndarray,
    colors: list[tuple[int, int, int]] | None = None,
    alpha: float = 0.4,
) -> np.ndarray:
    """세그멘테이션 마스크 오버레이.

    Args:
        image: BGR 이미지 (복사본 반환).
        masks: (N, H, W) 바이너리 마스크.
        colors: 마스크별 BGR 색상. None이면 자동 생성.
        alpha: 투명도.

    Returns:
        마스크가 오버레이된 새 이미지.
    """
    result = image.copy()
    if len(masks) == 0:
        return result

    default_colors = [
        (0, 255, 0),
        (255, 0, 0),
        (0, 0, 255),
        (255, 255, 0),
        (0, 255, 255),
        (255, 0, 255),
    ]

    overlay = result.copy()
    for i, mask in enumerate(masks):
        if colors is not None:
            c = colors[i]
        else:
            c = default_colors[i % len(default_colors)]
        overlay[mask > 0] = c

    return cv2.addWeighted(overlay, alpha, result, 1 - alpha, 0)


def draw_text(
    image: np.ndarray,
    text: str,
    position: tuple[int, int] = (10, 30),
    color: tuple[int, int, int] = (0, 255, 0),
    font_scale: float = 1.0,
    thickness: int = 2,
    background: bool = True,
    bg_alpha: float = 0.5,
) -> np.ndarray:
    """텍스트 그리기 (선택적 반투명 배경).

    Args:
        image: BGR 이미지 (복사본 반환).
        text: 텍스트 문자열.
        position: (x, y) 텍스트 위치.
        color: BGR 색상.
        font_scale: 글자 크기.
        thickness: 선 두께.
        background: True면 반투명 배경 그리기.
        bg_alpha: 배경 투명도.

    Returns:
        텍스트가 그려진 새 이미지.
    """
    result = image.copy()
    x, y = position

    if background:
        (tw, th), _ = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
        )
        overlay = result.copy()
        cv2.rectangle(
            overlay,
            (x, y - th - 5),
            (x + tw, y + 5),
            (75, 75, 75),
            -1,
        )
        result = cv2.addWeighted(overlay, bg_alpha, result, 1 - bg_alpha, 0)

    cv2.putText(
        result,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        color,
        thickness,
    )
    return result


def draw_info_lines(
    image: np.ndarray,
    lines: list[str],
    color: tuple[int, int, int] = (0, 255, 0),
    font_scale: float = 0.6,
    thickness: int = 2,
) -> np.ndarray:
    """여러 줄의 텍스트를 좌상단에 그리기.

    프레임 인덱스, FPS 등 정보 오버레이에 적합.

    Args:
        image: BGR 이미지 (복사본 반환).
        lines: 텍스트 리스트 (위에서 아래로).
        color: BGR 색상.
        font_scale: 글자 크기.
        thickness: 선 두께.

    Returns:
        텍스트가 그려진 새 이미지.
    """
    result = image.copy()
    for idx, text in enumerate(lines):
        (tw, th), _ = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
        )
        text_x = 10
        text_y = 10 + th * 2 * (idx + 1)

        overlay = result.copy()
        cv2.rectangle(
            overlay,
            (text_x, text_y - th - 5),
            (text_x + tw, text_y + 5),
            (75, 75, 75),
            -1,
        )
        result = cv2.addWeighted(overlay, 0.5, result, 0.5, 0)

        cv2.putText(
            result,
            text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            thickness,
        )
    return result
