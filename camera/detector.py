"""
Dart detection pipeline for PI Darts Counter.

Implements background subtraction, morphological filtering, contour detection,
dart tip localization, and segment identification per DESIGN.md section 3.2–3.4.
"""
from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional OpenCV / NumPy import guard
# ---------------------------------------------------------------------------
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE: bool = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning(
        "OpenCV (cv2) or NumPy not available. "
        "DartDetector will be non-functional until OpenCV is installed."
    )

# ---------------------------------------------------------------------------
# Dartboard constants — per DESIGN.md section 3.3
# ---------------------------------------------------------------------------

# Clockwise segment order starting from the top (12-o'clock position).
# Index 0 corresponds to angle band centred on 0° (top).
SEGMENTS: list[int] = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5]

# Stability filter settings — per DESIGN.md section 3.4
STABILITY_THRESHOLD_FRAMES: int = 45  # 30 fps × 1.5 s
POSITION_TOLERANCE_PX: int = 5

# Morphological kernel size for noise removal (3×3 is fast and effective)
_MORPH_KERNEL_SIZE: int = 3

# Minimum contour area to consider as a real dart (filters out tiny noise blobs)
_MIN_CONTOUR_AREA: float = 30.0


def get_segment(angle_deg: float, radius: float) -> tuple[int, int]:
    """
    Convert normalised polar coordinates to a dartboard segment.

    Parameters
    ----------
    angle_deg:
        Clockwise angle in degrees from the top (12-o'clock = 0°, range 0–360).
    radius:
        Normalised distance from board centre (0.0 = centre, 1.0 = outer edge
        of the double ring).

    Returns
    -------
    (segment_value, multiplier)
        e.g. (20, 3) for T20, (25, 1) for bull, (50, 1) for bullseye.
        Miss (outside board) returns (0, 1).
    """
    # --- Inner circles ---
    if radius < 0.05:
        return (50, 1)   # Bullseye
    if radius < 0.10:
        return (25, 1)   # Bull (outer bull)

    # Outside the board entirely
    if radius > 1.0:
        return (0, 1)

    # --- Identify the numbered segment ---
    # Each of 20 segments spans 18°. Segment index 0 (value=20) is centred on
    # 0° (top). Adding 9° shifts the boundary so index 0 spans –9° to +9°.
    segment_idx: int = int((angle_deg + 9) % 360 / 18) % 20
    value: int = SEGMENTS[segment_idx]

    # --- Identify the ring multiplier ---
    if 0.62 < radius < 0.68:
        multiplier = 3  # Triple ring
    elif 0.95 < radius <= 1.0:
        multiplier = 2  # Double ring
    else:
        multiplier = 1  # Single

    return (value, multiplier)


class DartDetector:
    """
    Per-camera dart detection pipeline.

    Each camera should have its own DartDetector instance so that background
    models and stability state remain independent.

    The full pipeline per DESIGN.md section 3.2:
      1. Background subtraction (MOG2)
      2. Difference mask + morphological ops (open then dilate)
      3. Contour detection
      4. Dart tip localisation (minimum-y point = tip of dart in frame)
      5. Stability filter (STABILITY_THRESHOLD_FRAMES consecutive frames
         within POSITION_TOLERANCE_PX tolerance)
      6. Return stable pixel position or None
    """

    def __init__(self, stability_threshold: int = STABILITY_THRESHOLD_FRAMES) -> None:
        # Allow callers to override the stability window so that cameras
        # running at a lower FPS (e.g. mobile at 10 fps) can use a smaller
        # frame count while still enforcing the same ~1.5-second hold time.
        self._stability_threshold = stability_threshold

        if CV2_AVAILABLE:
            # MOG2 history=500, varThreshold=16, detectShadows=False
            # Shadow detection is disabled for performance on Raspberry Pi.
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500,
                varThreshold=16,
                detectShadows=False,
            )
            self._morph_kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (_MORPH_KERNEL_SIZE, _MORPH_KERNEL_SIZE),
            )
        else:
            self.background_subtractor = None  # type: ignore[assignment]
            self._morph_kernel = None

        self.stable_position: tuple[float, float] | None = None
        self.stable_frame_count: int = 0
        self.last_detected_position: tuple[float, float] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_frame(self, frame: "np.ndarray") -> tuple[float, float] | None:
        """
        Run the full detection pipeline on a single frame.

        Parameters
        ----------
        frame:
            BGR frame from cv2.VideoCapture.read().

        Returns
        -------
        (x, y) pixel coordinates of the confirmed-stable dart tip, or None if
        no stable dart position has been detected yet.
        """
        if not CV2_AVAILABLE:
            logger.debug("process_frame called but OpenCV is not available.")
            return None

        try:
            return self._run_pipeline(frame)
        except Exception as exc:  # noqa: BLE001
            # A single bad frame must never crash the game loop.
            logger.warning("DartDetector.process_frame error (frame skipped): %s", exc)
            return None

    def reset(self) -> None:
        """
        Reset detection state.

        Call this after the dart has been removed from the board so that the
        stability accumulator is cleared and the background model can rebuild.
        """
        self.stable_position = None
        self.stable_frame_count = 0
        self.last_detected_position = None
        logger.debug("DartDetector state reset.")

    def draw_debug(self, frame: "np.ndarray") -> "np.ndarray":
        """
        Return a copy of frame with debug annotations:
        - Red contours from background subtraction
        - Yellow dot: last detected (unstable) tip
        - Green dot + ring: confirmed stable position
        - Stability counter in top-left
        """
        if not CV2_AVAILABLE:
            return frame

        out = frame.copy()

        try:
            fg = self.background_subtractor.apply(out, learningRate=0)
            fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, self._morph_kernel)
            fg = cv2.dilate(fg, self._morph_kernel, iterations=2)
            contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(out, contours, -1, (0, 0, 255), 1)
        except Exception:
            pass

        if self.last_detected_position is not None:
            x, y = int(self.last_detected_position[0]), int(self.last_detected_position[1])
            cv2.circle(out, (x, y), 6, (0, 255, 255), -1)

        if self.stable_position is not None:
            x, y = int(self.stable_position[0]), int(self.stable_position[1])
            cv2.circle(out, (x, y), 10, (0, 255, 0), -1)
            cv2.circle(out, (x, y), 20, (0, 255, 0), 2)

        cv2.putText(
            out,
            f"Stability: {self.stable_frame_count}/{self._stability_threshold}",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2,
        )
        return out

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _run_pipeline(self, frame: "np.ndarray") -> tuple[float, float] | None:
        """Execute the detection pipeline. Called by process_frame inside try/except."""

        # Step 1 — Background subtraction
        fg_mask: np.ndarray = self.background_subtractor.apply(frame)

        # Step 2 — Morphological ops: erode (noise removal) then dilate (gap fill)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self._morph_kernel)
        fg_mask = cv2.dilate(fg_mask, self._morph_kernel, iterations=2)

        # Step 3 — Contour detection on the cleaned mask
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            self._update_stability(None)
            return None

        # Step 4 — Find the dart tip: the point with the minimum y-value among
        # all contours that are large enough to be a real dart.
        # Minimum y = topmost row in image = tip of dart hanging toward board.
        tip = self._find_dart_tip(contours)

        # Step 5 — Stability check
        return self._update_stability(tip)

    def _find_dart_tip(
        self, contours: list["np.ndarray"]
    ) -> tuple[float, float] | None:
        """
        Return the pixel coordinate of the dart tip from a list of contours.

        The dart tip is defined as the point with the minimum y-value (topmost
        pixel) across all contours that exceed the minimum area threshold.
        Smaller y = higher in the frame = tip of the dart.
        """
        best_point: tuple[float, float] | None = None
        best_y: float = float("inf")

        for contour in contours:
            if cv2.contourArea(contour) < _MIN_CONTOUR_AREA:
                continue

            # topmost point of this contour (min y)
            top_idx = contour[:, 0, 1].argmin()
            cx = float(contour[top_idx, 0, 0])
            cy = float(contour[top_idx, 0, 1])

            if cy < best_y:
                best_y = cy
                best_point = (cx, cy)

        return best_point

    def _update_stability(
        self, position: tuple[float, float] | None
    ) -> tuple[float, float] | None:
        """
        Maintain the stability counter and return the confirmed position.

        A position is "confirmed stable" only after STABILITY_THRESHOLD_FRAMES
        consecutive frames where each detected point is within POSITION_TOLERANCE_PX
        of the previous one.
        """
        if position is None:
            # Nothing detected this frame — reset the accumulator.
            self.stable_frame_count = 0
            self.last_detected_position = None
            return None

        if self.last_detected_position is not None:
            dx = position[0] - self.last_detected_position[0]
            dy = position[1] - self.last_detected_position[1]
            distance = math.sqrt(dx * dx + dy * dy)

            if distance <= POSITION_TOLERANCE_PX:
                self.stable_frame_count += 1
            else:
                # Dart moved — start fresh from this position.
                self.stable_frame_count = 1

        else:
            # First detection after a reset.
            self.stable_frame_count = 1

        self.last_detected_position = position

        if self.stable_frame_count >= self._stability_threshold:
            self.stable_position = position
            return position

        return None
