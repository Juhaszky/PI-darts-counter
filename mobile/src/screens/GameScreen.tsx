import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ScrollView,
} from 'react-native';
import { useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { COLORS, SPACING, TYPOGRAPHY } from '../constants/theme';
import { useWebSocket } from '../hooks/useWebSocket';
import { useGame } from '../hooks/useGame';
import { useGameStore } from '../store/gameStore';
import { useCameraStream } from '../hooks/useCameraStream';
import PlayerCard from '../components/PlayerCard';
import ThrowSlots from '../components/ThrowSlots';
import BustOverlay from '../components/BustOverlay';
import ManualScoreModal from '../components/ManualScoreModal';
import type { RootStackParamList } from '../navigation/types';

type GameScreenRouteProp = RouteProp<RootStackParamList, 'Game'>;

export default function GameScreen() {
  const route = useRoute<GameScreenRouteProp>();
  const { gameId } = route.params;

  useWebSocket(); // Initialize WebSocket listener

  const { gameState, lastThrow, isBust, bustData } = useGameStore();
  const { undoLastThrow, getCurrentPlayer, submitManualScore } = useGame();
  const [manualScoreVisible, setManualScoreVisible] = useState(false);

  const [permission, requestPermission] = useCameraPermissions();
  const { isStreaming, startStreaming, stopStreaming, cameraRef } = useCameraStream();

  const handleCameraToggle = async () => {
    if (isStreaming) {
      stopStreaming();
      return;
    }
    if (!permission?.granted) {
      const result = await requestPermission();
      if (!result.granted) return;
    }
    startStreaming();
  };

  const currentPlayer = getCurrentPlayer();

  const handleUndo = async () => {
    try {
      await undoLastThrow();
    } catch (error) {
      console.error('Undo failed:', error);
    }
  };

  const handleManualScore = async (segment: number, multiplier: number) => {
    try {
      await submitManualScore({ segment, multiplier });
    } catch (error) {
      console.error('Manual score failed:', error);
    }
  };

  if (!gameState) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Játék betöltése...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>
          🎯 {gameState.mode} – {gameState.round}. kör
        </Text>
      </View>

      <ScrollView style={styles.content}>
        {/* Players */}
        {gameState.players.map((player) => (
          <PlayerCard key={player.id} player={player} gameMode={gameState.mode} />
        ))}

        {/* Current player section */}
        {currentPlayer && (
          <View style={styles.currentPlayerSection}>
            <Text style={styles.currentPlayerTitle}>{currentPlayer.name} köre</Text>
            <ThrowSlots
              lastThrow={lastThrow}
              throwsThisTurn={currentPlayer.throwsThisTurn}
            />
            <Text style={styles.remainingScore}>
              Maradék: {currentPlayer.score} pt
            </Text>
          </View>
        )}
      </ScrollView>

      {/* Camera preview — rendered outside ScrollView for Android surface stability */}
      {isStreaming && permission?.granted && (
        <View style={styles.cameraContainer}>
          <CameraView
            ref={cameraRef}
            style={styles.cameraPreview}
            facing="back"
          />
          <Text style={styles.cameraHint}>Kamera aktív – tartsd a táblára</Text>
        </View>
      )}

      {/* Action buttons */}
      <View style={styles.actionBar}>
        <TouchableOpacity style={styles.actionButton} onPress={handleUndo}>
          <Text style={styles.actionButtonText}>Visszavon</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, styles.actionButtonPrimary]}
          onPress={() => setManualScoreVisible(true)}
        >
          <Text style={styles.actionButtonText}>Kézi pont</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, isStreaming && styles.actionButtonActive]}
          onPress={handleCameraToggle}
        >
          <Text style={styles.actionButtonText}>{isStreaming ? 'Kamera ki' : 'Kamera'}</Text>
        </TouchableOpacity>
      </View>

      {/* Bust overlay */}
      <BustOverlay visible={isBust} playerName={bustData?.playerName || ''} />

      {/* Manual score modal */}
      <ManualScoreModal
        visible={manualScoreVisible}
        onClose={() => setManualScoreVisible(false)}
        onSubmit={handleManualScore}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.background,
  },
  loadingText: {
    fontSize: TYPOGRAPHY.h3,
    color: COLORS.text,
  },
  header: {
    backgroundColor: COLORS.card,
    paddingVertical: SPACING.md,
    paddingHorizontal: SPACING.lg,
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: TYPOGRAPHY.h3,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  content: {
    flex: 1,
    padding: SPACING.lg,
  },
  currentPlayerSection: {
    marginTop: SPACING.xl,
    alignItems: 'center',
  },
  currentPlayerTitle: {
    fontSize: TYPOGRAPHY.h2,
    fontWeight: 'bold',
    color: COLORS.primary,
    marginBottom: SPACING.md,
  },
  remainingScore: {
    fontSize: TYPOGRAPHY.h3,
    color: COLORS.text,
    marginTop: SPACING.md,
  },
  actionBar: {
    flexDirection: 'row',
    padding: SPACING.lg,
    backgroundColor: COLORS.card,
  },
  actionButton: {
    flex: 1,
    backgroundColor: COLORS.background,
    paddingVertical: SPACING.md,
    borderRadius: 8,
    alignItems: 'center',
    marginHorizontal: SPACING.xs,
  },
  actionButtonPrimary: {
    backgroundColor: COLORS.primary,
  },
  actionButtonActive: {
    backgroundColor: COLORS.error,
  },
  actionButtonText: {
    fontSize: TYPOGRAPHY.body,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  cameraContainer: {
    height: 200,
    marginHorizontal: SPACING.lg,
    marginBottom: SPACING.md,
    borderRadius: 12,
    overflow: 'hidden',
    position: 'relative',
  },
  cameraPreview: {
    flex: 1,
  },
  cameraHint: {
    position: 'absolute',
    bottom: SPACING.sm,
    alignSelf: 'center',
    color: COLORS.text,
    fontSize: TYPOGRAPHY.small,
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingHorizontal: SPACING.sm,
    paddingVertical: 4,
    borderRadius: 8,
  },
});
