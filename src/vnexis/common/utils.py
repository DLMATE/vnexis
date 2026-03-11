from typing import Literal

import cv2
import numpy as np

__all__ = [
    "resize_image",
    "inverse_resize_image_keep_aspect_ratio",
    "resize_boxes",
    "inverse_resize_boxes_keep_aspect_ratio",
    "make_color_mask",
    "draw_text_using_idx",
]


def resize_image(
    image: np.ndarray,
    size: tuple[int, int],
    mode: Literal["nearest", "linear", "cubic"] = "linear",
    keep_aspect_ratio: bool = False,
    pad_value: int = 114,
    inverse: bool = False,
) -> np.ndarray:
    """
    Args:
        image (np.ndarray): Image to be resized.
        size (tuple): Desired output size. (H, W)
        mode (str): Algorithm used for upsampling: 'nearest' | 'linear' | 'cubic' | Default: 'linear'
    Returns:
        np.ndarray: Resized image.
    """  # noqa: E501
    interpolations = {
        "nearest": cv2.INTER_NEAREST,
        "linear": cv2.INTER_LINEAR,
        "cubic": cv2.INTER_CUBIC,
    }
    interpolation = interpolations[mode]

    if keep_aspect_ratio:
        if inverse:
            image = inverse_resize_image_keep_aspect_ratio(image, size, interpolation)
        else:
            scale = min(size[0] / image.shape[0], size[1] / image.shape[1])
            new_size = (
                int(image.shape[0] * scale),
                int(image.shape[1] * scale),
            )
            image = cv2.resize(image, new_size[::-1], interpolation=interpolation)

            if new_size[0] != size[0]:
                top_pad = (size[0] - new_size[0]) // 2
                bottom_pad = size[0] - new_size[0] - top_pad
                image = np.pad(
                    image,
                    ((top_pad, bottom_pad), (0, 0), (0, 0)),
                    mode="constant",
                    constant_values=pad_value,
                )
            if new_size[1] != size[1]:
                left_pad = (size[1] - new_size[1]) // 2
                right_pad = size[1] - new_size[1] - left_pad
                image = np.pad(
                    image,
                    ((0, 0), (left_pad, right_pad), (0, 0)),
                    mode="constant",
                    constant_values=pad_value,
                )
    else:
        image = cv2.resize(image, size[::-1], interpolation=interpolation)

    return image


def inverse_resize_image_keep_aspect_ratio(
    image: np.ndarray,
    size: tuple[int, int],
    mode: int = cv2.INTER_LINEAR,
) -> np.ndarray:
    """
    Args:
        image (np.ndarray): Image to be resized.
        size (tuple): Desired output size. (H, W)
        mode (str): Algorithm used for upsampling: 'nearest' | 'linear' | 'cubic' | Default: 'linear'
    Returns:
        np.ndarray: Resized image.
    """  # noqa: E501

    scale = min(image.shape[0] / size[0], image.shape[1] / size[1])
    new_size = (int(size[0] * scale), int(size[1] * scale))
    top_pad, bottom_pad, left_pad, right_pad = 0, 0, 0, 0
    if new_size[0] != image.shape[0]:
        top_pad = (image.shape[0] - new_size[0]) // 2
        bottom_pad = image.shape[0] - new_size[0] - top_pad
    else:
        left_pad = (image.shape[1] - new_size[1]) // 2
        right_pad = image.shape[1] - new_size[1] - left_pad

    image = cv2.resize(
        image[
            top_pad : image.shape[0] - bottom_pad,
            left_pad : image.shape[1] - right_pad,
        ],
        size[::-1],
        interpolation=mode,
    )

    return image


def resize_boxes(
    boxes: np.ndarray,
    in_size: tuple[int, int],
    out_size: tuple[int, int],
    keep_aspect_ratio: bool = False,
    inverse: bool = False,
) -> np.ndarray:
    """
    Args:
        boxes (np.ndarray): Bounding boxes to be resized. (N, 4)
        in_size (tuple): Original image size. (H, W)
        out_size (tuple): Desired output size. (H, W)
    Returns:
        np.ndarray: Resized bounding boxes. (N, 4)
    """

    output_boxes = boxes.copy()
    if keep_aspect_ratio:
        if inverse:
            output_boxes = inverse_resize_boxes_keep_aspect_ratio(
                output_boxes, in_size, out_size
            )
        else:
            scale = min(out_size[0] / in_size[0], out_size[1] / in_size[1])
            new_size = (int(in_size[0] * scale), int(in_size[1] * scale))
            output_boxes = output_boxes * scale
            top_pad, left_pad = 0, 0
            if new_size[0] != out_size[0]:
                top_pad = (out_size[0] - new_size[0]) // 2
            else:
                left_pad = (out_size[1] - new_size[1]) // 2
            output_boxes[:, [0, 2]] += left_pad
            output_boxes[:, [1, 3]] += top_pad
    else:
        output_boxes[:, [0, 2]] = output_boxes[:, [0, 2]] * (out_size[1] / in_size[1])
        output_boxes[:, [1, 3]] = output_boxes[:, [1, 3]] * (out_size[0] / in_size[0])

    output_boxes[:, 0::2] = np.clip(output_boxes[:, 0::2], 0, out_size[1] - 1)
    output_boxes[:, 1::2] = np.clip(output_boxes[:, 1::2], 0, out_size[0] - 1)
    return output_boxes


def inverse_resize_boxes_keep_aspect_ratio(
    boxes: np.ndarray,
    in_size: tuple[int, int],
    out_size: tuple[int, int],
) -> np.ndarray:
    """
    Args:
        boxes (np.ndarray): Bounding boxes to be resized. (N, 4)
        in_size (tuple): Original image size. (H, W)
        out_size (tuple): Desired output size. (H, W)
    Returns:
        np.ndarray: Resized bounding boxes. (N, 4)
    """

    output_boxes = boxes.copy()
    scale = min(in_size[0] / out_size[0], in_size[1] / out_size[1])
    new_size = (int(out_size[0] * scale), int(out_size[1] * scale))
    top_pad, left_pad = 0, 0
    if new_size[0] != in_size[0]:
        top_pad = (in_size[0] - new_size[0]) // 2
    else:
        left_pad = (in_size[1] - new_size[1]) // 2
    output_boxes[:, [0, 2]] = output_boxes[:, [0, 2]] - left_pad
    output_boxes[:, [1, 3]] = output_boxes[:, [1, 3]] - top_pad
    output_boxes = output_boxes / scale
    return output_boxes


def make_color_mask(
    mask: np.ndarray,
    color: tuple[int, int, int],
    index: int = 1,
    color_mask: np.ndarray = None,
) -> np.ndarray:
    """
    Args:
        mask (np.ndarray): Mask to be colored. (H, W)
        color (tuple): Color to be used for the mask. (R, G, B)
    Returns:
        np.ndarray: Colored mask. (H, W, 3)
    """
    if color_mask is None:
        color_mask = np.zeros((*mask.shape, 3), dtype=np.uint8)
    color_mask[mask == index] = color
    return color_mask


def draw_text_using_idx(
    image: np.ndarray,
    text: str,
    idx: int,
    color: tuple[int, int, int],
    font: int = cv2.FONT_HERSHEY_SIMPLEX,
    font_scale: float = 1.0,
    thickness: int = 2,
) -> np.ndarray:
    # 텍스트 크기 계산
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
    text_x = 10
    text_y = 10 + text_height * 2 * (idx + 1)

    # 반투명한 검은색 배경 그리기
    overlay = image.copy()
    cv2.rectangle(
        overlay,
        (text_x, text_y - text_height - 5),
        (text_x + text_width, text_y + 5),
        (75, 75, 75),
        -1,
    )
    image = cv2.addWeighted(overlay, 0.5, image, 0.5, 0)

    # 텍스트 그리기
    cv2.putText(
        image,
        text,
        (text_x, text_y),
        font,
        font_scale,
        color,
        thickness,
    )
    return image
