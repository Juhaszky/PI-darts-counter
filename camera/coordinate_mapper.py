"""
Coordinate mapper for PI Darts Counter.

Converts pixel (x, y) coordinates from DartDetector to a dartboard
segment and multiplier. Board position is expressed as fractions of
frame dimensions so the mapper works regardless of camera resolution.
"""
import math

from camera.detector import get_segment


class CoordinateMapper:
    """
    Maps pixel coordinates to dartboard segment + multiplier.

    All board-position parameters are fractions of frame dimensions
    (values in [0.0, 1.0]) so the mapper is resolution-independent.

    Parameters
    ----------
    center_x_pct:
        Board centre as a fraction of frame width (default 0.5 = middle).
    center_y_pct:
        Board centre as a fraction of frame height (default 0.5 = middle).
    radius_pct:
        Board radius as a fraction of min(frame_width, frame_height)
        (default 0.4 = 80 % of the shorter dimension).
    """

    def __init__(
        self,
        center_x_pct: float = 0.5,
        center_y_pct: float = 0.5,
        radius_pct: float = 0.4,
    ) -> None:
        self.center_x_pct = center_x_pct
        self.center_y_pct = center_y_pct
        self.radius_pct = radius_pct

    def pixel_to_segment(
        self,
        x: float,
        y: float,
        frame_width: int,
        frame_height: int,
    ) -> tuple[int, int]:
        """
        Convert a pixel position to (segment_value, multiplier).

        Parameters
        ----------
        x, y:
            Pixel coordinates of the dart tip.
        frame_width, frame_height:
            Dimensions of the source frame in pixels.

        Returns
        -------
        (segment_value, multiplier)
            e.g. (20, 3) for T20, (25, 1) for bull, (50, 1) for bullseye.
            Returns (0, 1) when the dart lands outside the board.
        """
        cx = self.center_x_pct * frame_width
        cy = self.center_y_pct * frame_height
        radius_px = self.radius_pct * min(frame_width, frame_height)

        dx = x - cx
        dy = y - cy
        dist = math.sqrt(dx ** 2 + dy ** 2)
        radius_norm = dist / radius_px

        # Angle: 0° = top (−y axis), increasing clockwise.
        # atan2(dx, -dy) gives clockwise angle from the top.
        angle_deg = math.degrees(math.atan2(dx, -dy)) % 360

        return get_segment(angle_deg, radius_norm)

    def update(
        self,
        center_x_pct: float,
        center_y_pct: float,
        radius_pct: float,
    ) -> None:
        """
        Update the board-position calibration at runtime.

        Called by the POST /api/cameras/board-config endpoint so the
        mobile app can adjust the board position without restarting.
        """
        self.center_x_pct = center_x_pct
        self.center_y_pct = center_y_pct
        self.radius_pct = radius_pct
