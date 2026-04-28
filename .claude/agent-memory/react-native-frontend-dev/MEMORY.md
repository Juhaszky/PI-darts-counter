# React Native Frontend Dev - Agent Memory

## Project Structure
- Mobile app root: `C:\Develop\PI-darts-counter\mobile\`
- Expo SDK 54, React Native 0.81.5, React 19.1.0
- TypeScript strict mode, Zustand 5.x state management

## Theme System (light theme, post-redesign)
- Theme files live in `mobile/src/themes/` — colors.ts, spacing.ts, typography.ts, shadows.ts, index.ts, ThemeContext.tsx
- `constants/theme.ts` is now a pure backward-compat re-export shim from `../themes`
- All screens/components use `useTheme()` hook from `../themes/ThemeContext`; no direct `constants/theme` imports remain
- `createStyles(colors, spacing, typography, shadows)` factory pattern — called inside component, typed with `Theme['colors']` etc.
- Key colors: `primary=#E8393A` (red CTA), `secondary=#1A1A1A` (charcoal pills), `background=#F5F5F0`, `card=#FFFFFF`, `success=#2D6A4F` (dark green), `warning=#F59E0B` (amber stat highlights), `text=#1A1A1A`, `textSecondary=#6B6B6B`, `border=#E5E5E5`, `textOnPrimary=#FFFFFF`
- TYPOGRAPHY: tiny=12, small=14, body=16, h3=20, h2=24, h1=32
- SPACING: xs=4, sm=8, md=16, lg=24, xl=32, xxl=48

## WebSocket Patterns
- `wsService.send(type: string, data?: object)` accepts any string type — outgoing messages do not need to be in `WsEventType`
- `WsEventType` is for INBOUND server events only (discriminated union used in useWebSocket switch)
- Outgoing types live in `WsOutgoingEventType` in websocket.types.ts (added in camera streaming feature)
- `WsCameraFramePayload { frame: string }` — base64 JPEG for camera_frame messages

## Camera Streaming Pattern (useCameraStream hook)
- File: `mobile/src/hooks/useCameraStream.ts`
- Uses `import type { CameraView } from 'expo-camera'` for typed ref — never use `any` for camera ref
- `useRef<CameraView>(null)` — ref typed against the CameraView class
- Interval-based capture at 100ms (10 fps) via `setInterval`
- `captureAndSend` depends on `isStreaming` state — must be in useCallback deps
- Cleanup: interval cleared in both the else branch AND the effect cleanup function (belt-and-suspenders)
- `takePictureAsync({ quality: 0.3, base64: true, skipProcessing: true })` — low quality for bandwidth

## Camera Preview Layout Decision
- Camera preview (`CameraView`) must be placed OUTSIDE `ScrollView`, between ScrollView and actionBar
- Reason: Android camera surface is a native view — embedding inside ScrollView causes surface instability/black frames
- Pattern: `{isStreaming && permission?.granted && <View style={cameraContainer}>...}` guards render

## expo-camera Package
- Version: `^16.0.18` for Expo SDK 54
- Import: `import { CameraView, useCameraPermissions } from 'expo-camera'`
- Permission flow: `useCameraPermissions()` hook, call `requestPermission()` before startStreaming
- `facing="back"` prop on CameraView for rear camera

## Patterns - See detailed notes
- Details: `patterns.md` (to be created as needed)
