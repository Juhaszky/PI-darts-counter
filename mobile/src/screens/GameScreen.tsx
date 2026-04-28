import React, { useState } from 'react';
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
import { useTheme } from '../themes/ThemeContext';
import type { Theme } from '../themes';
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
  const { colors, spacing, typography, shadows } = useTheme();

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

  const styles = createStyles(colors, spacing, typography, shadows);

  if (!gameState) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading game...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerMode}>{gameState.mode}</Text>
        <Text style={styles.headerRound}>Round {gameState.round}</Text>
      </View>

      <ScrollView style={styles.content} contentContainerStyle={styles.contentPadding}>
        {/* Players */}
        {gameState.players.map((player) => (
          <PlayerCard key={player.id} player={player} gameMode={gameState.mode} />
        ))}

        {/* Current player throw section */}
        {currentPlayer && (
          <View style={styles.currentPlayerSection}>
            <Text style={styles.currentPlayerLabel}>Current Turn</Text>
            <Text style={styles.currentPlayerName}>{currentPlayer.name}</Text>
            <ThrowSlots
              lastThrow={lastThrow}
              throwsThisTurn={currentPlayer.throwsThisTurn}
            />
            <View style={styles.remainingRow}>
              <Text style={styles.remainingLabel}>Remaining</Text>
              <Text style={styles.remainingScore}>{currentPlayer.score}</Text>
            </View>
          </View>
        )}
      </ScrollView>

      {/* Camera preview — outside ScrollView for Android surface stability */}
      {isStreaming && permission?.granted && (
        <View style={styles.cameraContainer}>
          <CameraView
            ref={cameraRef}
            style={styles.cameraPreview}
            facing="back"
          />
          <Text style={styles.cameraHint}>Camera active — point at the board</Text>
        </View>
      )}

      {/* Action bar */}
      <View style={styles.actionBar}>
        <TouchableOpacity style={styles.actionButton} onPress={handleUndo} activeOpacity={0.8}>
          <Text style={styles.actionButtonText}>Undo</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, styles.actionButtonPrimary]}
          onPress={() => setManualScoreVisible(true)}
          activeOpacity={0.8}
        >
          <Text style={[styles.actionButtonText, styles.actionButtonTextPrimary]}>
            Manual Score
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, isStreaming && styles.actionButtonDanger]}
          onPress={handleCameraToggle}
          activeOpacity={0.8}
        >
          <Text style={styles.actionButtonText}>
            {isStreaming ? 'Camera Off' : 'Camera'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Overlays */}
      <BustOverlay visible={isBust} playerName={bustData?.playerName ?? ''} />

      <ManualScoreModal
        visible={manualScoreVisible}
        onClose={() => setManualScoreVisible(false)}
        onSubmit={handleManualScore}
      />
    </SafeAreaView>
  );
}

function createStyles(
  colors: Theme['colors'],
  spacing: Theme['spacing'],
  typography: Theme['typography'],
  shadows: Theme['shadows'],
) {
  return StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    loadingContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: colors.background,
    },
    loadingText: {
      fontSize: typography.h3,
      color: colors.textSecondary,
    },
    header: {
      backgroundColor: colors.card,
      paddingVertical: spacing.md,
      paddingHorizontal: spacing.lg,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    headerMode: {
      fontSize: typography.h3,
      fontWeight: '800',
      color: colors.text,
    },
    headerRound: {
      fontSize: typography.small,
      fontWeight: '600',
      color: colors.textSecondary,
    },
    content: {
      flex: 1,
    },
    contentPadding: {
      padding: spacing.lg,
    },
    currentPlayerSection: {
      marginTop: spacing.xl,
      backgroundColor: colors.card,
      borderRadius: 16,
      padding: spacing.lg,
      ...shadows.medium,
    },
    currentPlayerLabel: {
      fontSize: typography.tiny,
      fontWeight: '700',
      color: colors.textSecondary,
      textTransform: 'uppercase',
      letterSpacing: 0.8,
    },
    currentPlayerName: {
      fontSize: typography.h2,
      fontWeight: '800',
      color: colors.text,
      marginTop: spacing.xs,
      marginBottom: spacing.sm,
    },
    remainingRow: {
      flexDirection: 'row',
      alignItems: 'baseline',
      justifyContent: 'flex-end',
      marginTop: spacing.sm,
      paddingTop: spacing.sm,
      borderTopWidth: 1,
      borderTopColor: colors.border,
    },
    remainingLabel: {
      fontSize: typography.small,
      color: colors.textSecondary,
      marginRight: spacing.sm,
    },
    remainingScore: {
      fontSize: typography.h1,
      fontWeight: '800',
      color: colors.warning,
    },
    // Action bar
    actionBar: {
      flexDirection: 'row',
      padding: spacing.md,
      backgroundColor: colors.card,
      borderTopWidth: 1,
      borderTopColor: colors.border,
      gap: spacing.sm,
    },
    actionButton: {
      flex: 1,
      backgroundColor: colors.inputBackground,
      borderWidth: 1,
      borderColor: colors.border,
      paddingVertical: spacing.md,
      borderRadius: 10,
      alignItems: 'center',
    },
    actionButtonPrimary: {
      backgroundColor: colors.primary,
      borderColor: colors.primary,
    },
    actionButtonDanger: {
      backgroundColor: colors.error + '15',
      borderColor: colors.error,
    },
    actionButtonText: {
      fontSize: typography.small,
      fontWeight: '700',
      color: colors.text,
    },
    actionButtonTextPrimary: {
      color: colors.textOnPrimary,
    },
    // Camera
    cameraContainer: {
      height: 200,
      marginHorizontal: spacing.lg,
      marginBottom: spacing.md,
      borderRadius: 12,
      overflow: 'hidden',
    },
    cameraPreview: {
      flex: 1,
    },
    cameraHint: {
      position: 'absolute',
      bottom: spacing.sm,
      alignSelf: 'center',
      color: '#FFFFFF',
      fontSize: typography.tiny,
      backgroundColor: 'rgba(0,0,0,0.55)',
      paddingHorizontal: spacing.sm,
      paddingVertical: 4,
      borderRadius: 8,
    },
  });
}
