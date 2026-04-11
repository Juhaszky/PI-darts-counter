"""
Camera management for PI Darts Counter.

CameraManager owns and lifecycle-manages up to 3 cv2.VideoCapture instances,
one DartDetector per camera, and one CameraCalibration per camera.

Frame capture is CPU-bound (OpenCV C++ under the hood) and is offloaded to a
thread pool executor so it never blocks the asyncio event loop.
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from camera.calibration import CameraCalibration
from camera.detector import DartDetector

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
        "CameraManager will operate in stub mode (no real capture)."
    )

# ---------------------------------------------------------------------------
# Camera metadata
# ---------------------------------------------------------------------------

# Human-readable labels per DESIGN.md section 6.2 (camera_status message).
# Hungarian: Bal=Left, Jobb=Right, Felső=Top.
_CAMERA_LABELS: dict[int, str] = {0: "Bal", 1: "Jobb", 2: "Felső"}

# Thread pool for blocking OpenCV calls.  One thread per camera is enough
# because captures are sequential (one frame per camera per iteration).
_CAPTURE_THREAD_POOL = ThreadPoolExecutor(max_workers=3, thread_name_prefix="cam_capture")


class CameraManager:
    """
    Manages camera initialisation, frame capture, and dart position reporting.

    Parameters
    ----------
    camera_ids:
        Ordered list of camera sources.  Each entry is either a numeric string
        device index (e.g. "0", "1") or an HTTP MJPEG URL
        (e.g. "http://192.168.1.100:8080/video") for IP cameras such as the
        Android "IP Webcam" app.
    fps:
        Target capture frame-rate. Used to set the V4L2 FPS property on each
        camera on Linux; on Windows this is a hint only.
    """

    def __init__(self, camera_ids: list[str], fps: int = 30) -> None:
        self.camera_ids: list[str] = camera_ids
        self.fps: int = fps

        # Populated by start(); index matches camera_ids.
        self.cameras: list["cv2.VideoCapture | None"] = []
        self.detectors: list[DartDetector] = []
        self.calibrations: list[CameraCalibration] = []

        # Populated in _read_frame when a frame is successfully read.
        # Keyed by camera index (position in self.cameras); value is (width, height).
        self.frame_sizes: dict[int, tuple[int, int]] = {}

        self.running: bool = False
        self.last_frames: dict[int, "np.ndarray"] = {}  # latest raw frame per camera index

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """
        Open all cameras, load calibration data, and mark the manager as running.

        Cameras that fail to open are recorded as None so that the rest of the
        pipeline can continue with degraded (fewer-camera) operation.
        """
        if self.running:
            logger.info("CameraManager.start() called but already running — no-op.")
            return

        logger.info("CameraManager starting with camera sources: %s", self.camera_ids)

        self.cameras = []
        self.detectors = []
        self.calibrations = []
        self.frame_sizes = {}

        for cam_source in self.camera_ids:
            cap = await self._open_camera(cam_source)
            self.cameras.append(cap)

            detector = DartDetector()
            self.detectors.append(detector)

            # CameraCalibration is keyed by index, not source string.
            cam_idx = len(self.calibrations)
            calibration = CameraCalibration(cam_idx)
            loaded = calibration.load_calibration()
            if not loaded:
                logger.warning(
                    "Camera %s: no calibration data found — undistortion disabled.",
                    cam_source,
                )
            self.calibrations.append(calibration)

        active_count = sum(1 for c in self.cameras if c is not None)
        logger.info(
            "CameraManager started: %d / %d cameras active.",
            active_count,
            len(self.camera_ids),
        )
        self.running = True

    async def stop(self) -> None:
        """Release all open cameras and reset running state."""
        if not self.running:
            return

        self.running = False

        for idx, cap in enumerate(self.cameras):
            if cap is not None and CV2_AVAILABLE:
                # Release is synchronous but fast; no executor needed here.
                cap.release()
                logger.info("Camera %s released.", self.camera_ids[idx])

        self.cameras = []
        self.detectors = []
        self.calibrations = []
        self.frame_sizes = {}
        logger.info("CameraManager stopped.")

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------

    async def capture_frames(self) -> list["np.ndarray | None"]:
        """
        Capture one frame from each camera concurrently.

        Uses run_in_executor so that blocking VideoCapture.read() calls do not
        stall the asyncio event loop.

        Returns
        -------
        List of BGR frames (numpy arrays), one per camera.  A None entry means
        that camera failed to provide a frame this cycle.
        """
        if not self.running or not CV2_AVAILABLE:
            return [None] * len(self.camera_ids)

        loop = asyncio.get_event_loop()

        tasks = [
            loop.run_in_executor(_CAPTURE_THREAD_POOL, self._read_frame, i)
            for i in range(len(self.cameras))
        ]

        frames: list["np.ndarray | None"] = list(await asyncio.gather(*tasks))
        return frames

    # ------------------------------------------------------------------
    # Dart position
    # ------------------------------------------------------------------

    def get_dart_position(self) -> tuple[float, float, int, int] | None:
        """
        Return the first confirmed-stable dart position across all active cameras,
        together with the frame dimensions needed to compute board-relative coordinates.

        This is a single-camera fallback that returns the first detector that has a
        stable position.  Full multi-camera triangulation will replace this in a
        future phase.

        Returns
        -------
        (x, y, frame_width, frame_height) if a stable position is available, else None.
        """
        for i, detector in enumerate(self.detectors):
            if detector.stable_position is not None and i in self.frame_sizes:
                x, y = detector.stable_position
                w, h = self.frame_sizes[i]
                return (x, y, w, h)
        return None

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_camera_status(self) -> list[dict]:
        """
        Return the active/inactive status for every configured camera.

        This matches the `camera_status` WebSocket message format defined in
        DESIGN.md section 6.2.

        Returns
        -------
        List of dicts: [{"id": 0, "label": "Bal", "active": True}, ...]
        """
        status: list[dict] = []
        for i, cam_source in enumerate(self.camera_ids):
            if i < len(self.cameras):
                cap = self.cameras[i]
                active = (
                    CV2_AVAILABLE
                    and cap is not None
                    and cap.isOpened()
                )
            else:
                active = False

            status.append({
                "id": i,
                "source": cam_source,
                "label": _CAMERA_LABELS.get(i, f"Kamera {i}"),
                "active": active,
            })

        return status

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _open_camera(self, cam_source: str) -> "cv2.VideoCapture | None":
        """
        Open a single camera device or MJPEG URL in a thread executor.

        Returns the VideoCapture object if successful, or None on failure.
        """
        if not CV2_AVAILABLE:
            logger.warning("Cannot open camera %s: OpenCV not available.", cam_source)
            return None

        loop = asyncio.get_event_loop()
        cap: cv2.VideoCapture = await loop.run_in_executor(
            _CAPTURE_THREAD_POOL, self._open_sync, cam_source
        )

        if cap is None or not cap.isOpened():
            logger.warning("Camera %s could not be opened.", cam_source)
            return None

        logger.info("Camera %s opened successfully.", cam_source)
        return cap

    def _open_sync(self, cam_source: str) -> "cv2.VideoCapture | None":
        """
        Synchronous camera open — runs in executor thread.

        Accepts either a numeric string device index ("0", "1", "2") or an
        HTTP MJPEG URL (e.g. "http://192.168.1.100:8080/video").
        Numeric strings are converted to int so that cv2.VideoCapture receives
        the expected device-index type on all platforms.
        """
        try:
            # Convert to int for local device indices; leave as str for URLs.
            source: int | str = int(cam_source) if cam_source.isdigit() else cam_source
            cap = cv2.VideoCapture(source)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FPS, self.fps)
            return cap
        except Exception as exc:  # noqa: BLE001
            logger.error("Exception opening camera %s: %s", cam_source, exc)
            return None

    def _read_frame(self, camera_index: int) -> "np.ndarray | None":
        """
        Read one frame from the camera at position camera_index in self.cameras.

        Runs in a thread executor — must not call any async code.
        Also feeds the frame through the matching DartDetector.
        """
        cap = self.cameras[camera_index]
        if cap is None or not cap.isOpened():
            return None

        try:
            ok, frame = cap.read()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Camera %s read error: %s",
                self.camera_ids[camera_index],
                exc,
            )
            return None

        if not ok or frame is None:
            logger.debug("Camera %s returned empty frame.", self.camera_ids[camera_index])
            return None

        # Cache frame dimensions for coordinate mapping (written once, then stable).
        h, w = frame.shape[:2]
        self.frame_sizes[camera_index] = (w, h)

        # Apply undistortion if calibrated (fast no-op if not).
        calib = self.calibrations[camera_index]
        frame = calib.undistort(frame)

        # Cache latest frame for debug snapshot endpoint.
        self.last_frames[camera_index] = frame.copy()

        # Feed to detector so stability state is updated on every read.
        self.detectors[camera_index].process_frame(frame)

        return frame
