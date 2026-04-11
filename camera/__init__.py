"""
Camera module for PI Darts Counter.

Exports the three public components used by the rest of the application:
  - CameraManager  : camera lifecycle, frame capture, dart position reporting
  - DartDetector   : per-frame background subtraction + stability pipeline
  - get_segment    : polar → dartboard segment mapping
  - CameraCalibration : checkerboard calibration + undistortion
"""
from camera.camera_manager import CameraManager
from camera.detector import DartDetector, get_segment
from camera.calibration import CameraCalibration

__all__ = ["CameraManager", "DartDetector", "get_segment", "CameraCalibration"]
