"""
Camera calibration for PI Darts Counter.

Uses OpenCV's standard checkerboard calibration workflow:
  1. Detect inner corners on a set of checkerboard images.
  2. Run cv2.calibrateCamera to compute the camera matrix and distortion coefficients.
  3. Persist results to / reload from a JSON file in calibration_data/.

All numpy arrays are serialised as nested Python lists so that the JSON is
human-readable and does not require numpy on the reading side.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
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
        "CameraCalibration will be non-functional until OpenCV is installed."
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CALIBRATION_DATA_DIR: Path = Path(__file__).parent / "calibration_data"

# Standard 9×6 inner-corner checkerboard (10×7 squares).
_CHESSBOARD_COLS: int = 9
_CHESSBOARD_ROWS: int = 6

# Termination criteria for corner sub-pixel refinement.
# Max 30 iterations, accuracy 0.001 pixels.
_SUBPIX_CRITERIA = (
    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    if CV2_AVAILABLE
    else None
)


class CameraCalibration:
    """
    Holds intrinsic calibration parameters for a single camera.

    Attributes
    ----------
    camera_id:
        Integer camera index (0, 1, or 2).
    camera_matrix:
        3×3 numpy array — intrinsic matrix [[fx,0,cx],[0,fy,cy],[0,0,1]].
    dist_coeffs:
        1-D numpy array of distortion coefficients [k1, k2, p1, p2, k3].
    is_calibrated:
        True once valid calibration data has been loaded or computed.
    """

    def __init__(self, camera_id: int) -> None:
        self.camera_id: int = camera_id
        self.camera_matrix: "np.ndarray | None" = None
        self.dist_coeffs: "np.ndarray | None" = None
        self.is_calibrated: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calibrate(self, images: list["np.ndarray"]) -> bool:
        """
        Calibrate the camera from a list of checkerboard images.

        Each image should be a BGR or grayscale frame captured at different
        angles / positions of the same printed checkerboard pattern.

        Parameters
        ----------
        images:
            List of numpy BGR frames containing the calibration target.

        Returns
        -------
        True if calibration succeeded and was saved; False otherwise.
        """
        if not CV2_AVAILABLE:
            logger.error("calibrate() called but OpenCV is not available.")
            return False

        if not images:
            logger.error("calibrate() received an empty image list.")
            return False

        board_shape = (_CHESSBOARD_COLS, _CHESSBOARD_ROWS)

        # Prepare the known 3-D object points for one checkerboard view.
        # Corners lie on a Z=0 plane; spacing is 1 unit (real size does not
        # matter for undistortion — only the shape matters).
        objp: np.ndarray = np.zeros(
            (_CHESSBOARD_COLS * _CHESSBOARD_ROWS, 3), dtype=np.float32
        )
        objp[:, :2] = np.mgrid[0:_CHESSBOARD_COLS, 0:_CHESSBOARD_ROWS].T.reshape(-1, 2)

        obj_points: list[np.ndarray] = []  # 3-D points in real-world space
        img_points: list[np.ndarray] = []  # 2-D points in image space
        image_size: tuple[int, int] | None = None

        for idx, frame in enumerate(images):
            gray = (
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if len(frame.shape) == 3
                else frame
            )

            if image_size is None:
                image_size = (gray.shape[1], gray.shape[0])  # (width, height)

            found, corners = cv2.findChessboardCorners(gray, board_shape, None)

            if not found:
                logger.debug("Checkerboard not found in calibration image %d — skipping.", idx)
                continue

            # Refine to sub-pixel accuracy.
            corners_refined = cv2.cornerSubPix(
                gray, corners, (11, 11), (-1, -1), _SUBPIX_CRITERIA
            )

            obj_points.append(objp)
            img_points.append(corners_refined)
            logger.debug("Calibration image %d: corners found and refined.", idx)

        if len(obj_points) < 3:
            logger.error(
                "Calibration failed: found checkerboard in only %d / %d images "
                "(minimum 3 required).",
                len(obj_points),
                len(images),
            )
            return False

        logger.info(
            "Camera %d: calibrating from %d / %d images.",
            self.camera_id,
            len(obj_points),
            len(images),
        )

        ret, camera_matrix, dist_coeffs, _rvecs, _tvecs = cv2.calibrateCamera(
            obj_points, img_points, image_size, None, None
        )

        if not ret:
            logger.error("cv2.calibrateCamera returned failure for camera %d.", self.camera_id)
            return False

        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        self.is_calibrated = True

        logger.info("Camera %d calibrated successfully (RMS reprojection error: %.4f).", self.camera_id, ret)

        self.save_calibration()
        return True

    def load_calibration(self) -> bool:
        """
        Load calibration parameters from the JSON file for this camera.

        Returns
        -------
        True if the file exists and was loaded successfully; False otherwise.
        """
        if not CV2_AVAILABLE:
            logger.error("load_calibration() called but OpenCV/NumPy is not available.")
            return False

        calib_path = self._calibration_path()

        if not calib_path.exists():
            logger.info(
                "No calibration file found for camera %d at %s.",
                self.camera_id,
                calib_path,
            )
            return False

        try:
            with calib_path.open("r", encoding="utf-8") as fh:
                data: dict = json.load(fh)

            self.camera_matrix = np.array(data["camera_matrix"], dtype=np.float64)
            self.dist_coeffs = np.array(data["dist_coeffs"], dtype=np.float64)
            self.is_calibrated = True

            logger.info("Camera %d: calibration loaded from %s.", self.camera_id, calib_path)
            return True

        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            logger.error(
                "Failed to parse calibration file for camera %d: %s", self.camera_id, exc
            )
            return False

    def save_calibration(self) -> None:
        """
        Persist calibration parameters to a JSON file.

        The calibration_data/ directory is created automatically if it does
        not exist. numpy arrays are stored as nested lists for portability.
        """
        if not self.is_calibrated or self.camera_matrix is None or self.dist_coeffs is None:
            logger.warning(
                "save_calibration() called for camera %d but no calibration data is available.",
                self.camera_id,
            )
            return

        CALIBRATION_DATA_DIR.mkdir(parents=True, exist_ok=True)
        calib_path = self._calibration_path()

        data = {
            "camera_id": self.camera_id,
            "camera_matrix": self.camera_matrix.tolist(),
            "dist_coeffs": self.dist_coeffs.tolist(),
        }

        with calib_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

        logger.info("Camera %d: calibration saved to %s.", self.camera_id, calib_path)

    def undistort(self, frame: "np.ndarray") -> "np.ndarray":
        """
        Apply lens-distortion correction to a frame.

        If the camera is not yet calibrated, the original frame is returned
        unchanged so that the pipeline can continue without crashing.

        Parameters
        ----------
        frame:
            BGR numpy array from cv2.VideoCapture.read().

        Returns
        -------
        Undistorted BGR frame, or the original frame if not calibrated.
        """
        if not CV2_AVAILABLE:
            return frame

        if not self.is_calibrated or self.camera_matrix is None or self.dist_coeffs is None:
            logger.debug(
                "undistort() called for camera %d but calibration not available — "
                "returning original frame.",
                self.camera_id,
            )
            return frame

        return cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calibration_path(self) -> Path:
        """Return the path to the JSON calibration file for this camera."""
        return CALIBRATION_DATA_DIR / f"camera_{self.camera_id}.json"
