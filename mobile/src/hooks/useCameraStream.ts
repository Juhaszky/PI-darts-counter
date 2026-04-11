import { useRef, useState, useCallback, useEffect } from 'react';
import type { CameraView } from 'expo-camera';
import { wsService } from '../services/websocketService';

const FRAME_INTERVAL_MS = 100; // ~10 fps

export function useCameraStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cameraRef = useRef<CameraView>(null);

  const startStreaming = useCallback(() => {
    if (isStreaming) return;
    setIsStreaming(true);
  }, [isStreaming]);

  const stopStreaming = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const captureAndSend = useCallback(async () => {
    if (!cameraRef.current || !isStreaming) return;
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.3,
        base64: true,
        skipProcessing: true,
      });
      if (photo?.base64) {
        wsService.send('camera_frame', { frame: photo.base64 });
      }
    } catch {
      // Ignore single-frame capture errors to avoid interrupting the stream
    }
  }, [isStreaming]);

  useEffect(() => {
    if (isStreaming) {
      intervalRef.current = setInterval(captureAndSend, FRAME_INTERVAL_MS);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isStreaming, captureAndSend]);

  return { isStreaming, startStreaming, stopStreaming, cameraRef };
}
