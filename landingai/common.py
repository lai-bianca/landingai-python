import math
import re
from functools import cached_property
from typing import Dict, List, Tuple

import cv2
import numpy as np
from pydantic import BaseModel, BaseSettings


class APICredential(BaseSettings):
    """The API credentials of an organization in LandingLens.
    It supports loading from environment variables or .env files.

    The supported name of the environment variables are (case-insensitive):
    - LANDINGAI_API_KEY
    - LANDINGAI_API_SECRET

    Environment variables will always take priority over values loaded from a dotenv file.
    """

    api_key: str
    api_secret: str

    class Config:
        env_file = ".env"
        env_prefix = "landingai_"
        case_sensitive = False


class Prediction(BaseModel):
    """The base/parent prediction class that stores the common shared properties of a prediction."""

    score: float
    """The confidence score of this prediction."""

    @property
    def num_predicted_pixels(self) -> int:
        """Return the number of pixels within the prediction"""
        raise NotImplementedError()


class ClassificationPrediction(Prediction):
    """A single classification prediction for an image."""

    label_name: str
    """The predicted label name."""

    label_index: int
    """The predicted label index.
    A label index is an unique integer that identifies a label in your label book.
    For more information, see https://support.landing.ai/docs/manage-label-book.
    """


class OcrPrediction(Prediction):
    """A single OCR prediction for an image."""

    text: str
    """The predicted text."""

    location: List[Tuple[int, int]]
    """A quadrilateral polygon that represents the location of the text. It is a list of four (x, y) coordinates."""


class ObjectDetectionPrediction(ClassificationPrediction):
    """A single bounding box prediction for an image.
    It includes a predicted bounding box (xmin, ymin, xmax, ymax), confidence score, and the predicted label.
    """

    id: str
    """A unique string identifier (UUID) for the prediction."""

    bboxes: Tuple[int, int, int, int]
    """A tuple of (xmin, ymin, xmax, ymax) of the predicted bounding box."""

    @cached_property
    def num_predicted_pixels(self) -> int:
        """The number of pixels within the predicted bounding box."""
        return (self.bboxes[2] - self.bboxes[0]) * (self.bboxes[3] - self.bboxes[1])

    class Config:
        keep_untouched = (cached_property,)


class SegmentationPrediction(ClassificationPrediction):
    """A single segmentation mask prediction for an image.
    It includes a predicted segmentation mask, confidence score, and the predicted label.
    """

    id: str
    """A unique string identifier (UUID) for this prediction."""

    encoded_mask: str
    """A run-length encoded bitmap string."""

    encoding_map: Dict[str, int]
    """A map that is used to generate the encoded_mask. For example: {'Z':0, 'N':1}.
    The key is the character in the encoded_mask, the value is the bit value.
    """

    mask_shape: Tuple[int, int]
    """The shape of the decoded two-dimensional segmentation mask. For example: (1024, 1024)."""

    @cached_property
    def decoded_boolean_mask(self) -> np.ndarray:
        """Decoded boolean segmentation mask.
        It is a two-dimensional NumPy array with 0s and 1s.
        1 means the pixel is the predicted class, 0 means the pixel is not.
        """
        flattened_bitmap = decode_bitmap_rle(self.encoded_mask, self.encoding_map)
        seg_mask_channel = np.array(flattened_bitmap, dtype=np.uint8).reshape(
            self.mask_shape
        )
        return seg_mask_channel

    @cached_property
    def decoded_index_mask(self) -> np.ndarray:
        """Decoded index segmentation mask.
        It is a two-dimensional numpy array with 0s and the number of the predicted class index.
        This is useful if you want to overlay multiple segmentation masks into one.
        """
        return self.decoded_boolean_mask * self.label_index

    @cached_property
    def decoded_colored_mask(self) -> np.ndarray:
        """Decoded colored segmentation mask.
        It is a three-dimensional numpy array (HWC) where the predicted pixels are colored.
        The color is randomly assigned for each mask.
        """
        mask_3d = np.expand_dims(self.decoded_boolean_mask, -1)
        mask_3d = cv2.cvtColor(mask_3d, cv2.COLOR_GRAY2RGB)
        random_color = np.random.randint(0, 255, size=3, dtype=np.uint8)  # type: ignore
        return mask_3d * random_color  # type: ignore

    @cached_property
    def num_predicted_pixels(self) -> int:
        """The number of pixels that are predicted as the class."""
        return np.count_nonzero(self.decoded_boolean_mask)

    @cached_property
    def percentage_predicted_pixels(self) -> float:
        """The percentage of pixels that are predicted as the class."""
        return np.count_nonzero(self.decoded_boolean_mask) / math.prod(self.mask_shape)

    class Config:
        keep_untouched = (cached_property,)


def decode_bitmap_rle(bitmap: str, encoding_map: Dict[str, int]) -> List[int]:
    """
    Decode bitmap string to NumPy array.

    Parameters
    ----------
    bitmap:
        Single run-length encoded bitmap string. For example: "5Z3N2Z".
    encoding_map:
        Dictionary with the enconding used to generate the bitmap. For example: {'Z':0, 'N':1}.

    Return
    -----
    A flattened segmentation mask (with 0s and 1s) for a single class.
    """
    flat_mask = []
    bitmap_list = re.split("(Z|N)", bitmap)
    for num, map_letter in zip(*[iter(bitmap_list)] * 2):
        map_number = encoding_map[map_letter]
        flat_mask.extend([int(map_number)] * int(num))
    return flat_mask
