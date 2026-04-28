import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
  Modal,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { useTheme } from '../themes/ThemeContext';
import type { Theme } from '../themes';
import { GAME_MODES } from '../constants/config';
import { useConnectionStore } from '../store/connectionStore';
import { useGame } from '../hooks/useGame';
import { wsService } from '../services/websocketService';
import type { RootStackParamList } from '../navigation/types';
import type { GameMode } from '../types/game.types';
import PlayerModal from '../components/PlayersModal';

type SetupScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Setup'>;

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0] ?? '')
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

const AVATAR_COLORS = ['#E8393A', '#2D6A4F', '#F59E0B', '#6366F1', '#EC4899'];

export default function SetupScreen() {
  const navigation = useNavigation<SetupScreenNavigationProp>();
  const { host, port, setGameId } = useConnectionStore();
  const { createGame, startGame } = useGame();
  const { colors, spacing, typography, shadows } = useTheme();

  const [gameMode, setGameMode] = useState<GameMode>('501');
  const [doubleOut, setDoubleOut] = useState(false);
  const [players, setPlayers] = useState<string[]>(['', '']);
  const [newPlayerName, setNewPlayerName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleAddPlayer = () => {
    if (newPlayerName.trim()) {
      setPlayers([...players, newPlayerName.trim()]);
      setNewPlayerName('');
    }
  };

  const handleConfirmPlayers = (newPlayers: string[]) => {
    setPlayers(newPlayers);
    setIsModalOpen(false);
  };

  const handleRemovePlayer = (index: number) => {
    setPlayers(players.filter((_, i) => i !== index));
  };

  const handleStartGame = async () => {
    const validPlayers = players.filter((name) => name.trim());

    if (validPlayers.length < 2) {
      Alert.alert('Not enough players', 'You need at least 2 players to start.');
      return;
    }

    setIsLoading(true);

    try {
      const response = await createGame({
        mode: gameMode,
        doubleOut,
        players: validPlayers.map((name) => ({ name })),
      });

      setGameId(response.gameId);
      wsService.connect(host, port, response.gameId);
      await startGame();
      navigation.navigate('Game', { gameId: response.gameId });
    } catch (error) {
      console.error('Failed to start game:', error);
      Alert.alert('Error', 'Failed to start the game. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const styles = createStyles(colors, spacing, typography, shadows);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* Game mode segmented toggle */}
      <Text style={styles.sectionTitle}>Game Mode</Text>
      <View style={styles.modeSelector}>
        {Object.entries(GAME_MODES).map(([mode, { label }]) => {
          const isActive = gameMode === mode;
          return (
            <TouchableOpacity
              key={mode}
              style={[styles.modePill, isActive && styles.modePillActive]}
              onPress={() => setGameMode(mode as GameMode)}
              activeOpacity={0.8}
            >
              <Text style={[styles.modePillText, isActive && styles.modePillTextActive]}>
                {label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Double out toggle */}
      <Text style={styles.sectionTitle}>Rules</Text>
      <TouchableOpacity
        style={styles.toggleRow}
        onPress={() => setDoubleOut(!doubleOut)}
        activeOpacity={0.8}
      >
        <View style={styles.toggleInfo}>
          <Text style={styles.toggleLabel}>Double Out</Text>
          <Text style={styles.toggleDescription}>Must finish on a double segment</Text>
        </View>
        <View style={[styles.toggleTrack, doubleOut && styles.toggleTrackActive]}>
          <View style={[styles.toggleThumb, doubleOut && styles.toggleThumbActive]} />
        </View>
      </TouchableOpacity>

      {/* Players section */}
      <Text style={styles.sectionTitle}>Players</Text>

      {players.map((player, index) => (
        <View key={index} style={styles.playerCard}>
          <View style={[styles.avatarCircle, { backgroundColor: AVATAR_COLORS[index % AVATAR_COLORS.length] }]}>
            <Text style={styles.avatarText}>
              {player.trim() ? getInitials(player) : String(index + 1)}
            </Text>
          </View>
          <TextInput
            style={styles.playerInput}
            value={player}
            onChangeText={(text) => {
              const updated = [...players];
              updated[index] = text;
              setPlayers(updated);
            }}
            placeholder={`Player ${index + 1}`}
            placeholderTextColor={colors.placeholder}
          />
          {players.length > 2 && (
            <TouchableOpacity
              style={styles.removeButton}
              onPress={() => handleRemovePlayer(index)}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Text style={styles.removeButtonText}>×</Text>
            </TouchableOpacity>
          )}
        </View>
      ))}

      {/* Add player row */}
      <View style={styles.addPlayerRow}>
        <TextInput
          style={[styles.playerInput, styles.addPlayerInput]}
          value={newPlayerName}
          onChangeText={setNewPlayerName}
          placeholder="New player name"
          placeholderTextColor={colors.placeholder}
          onSubmitEditing={handleAddPlayer}
          returnKeyType="done"
        />
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => setIsModalOpen(true)}
        >
          <Text style={styles.addButtonText}>Browse</Text>
        </TouchableOpacity>
      </View>

      {/* Start game CTA */}
      <TouchableOpacity
        style={[styles.startButton, isLoading && styles.startButtonDisabled]}
        onPress={handleStartGame}
        disabled={isLoading}
        activeOpacity={0.85}
      >
        {isLoading ? (
          <ActivityIndicator color={colors.textOnPrimary} />
        ) : (
          <Text style={styles.startButtonText}>Start Game</Text>
        )}
      </TouchableOpacity>

      <Modal
        animationType="slide"
        transparent={false}
        visible={isModalOpen}
        onRequestClose={() => setIsModalOpen(false)}
      >
        <PlayerModal
          onClose={() => setIsModalOpen(false)}
          onConfirm={handleConfirmPlayers}
          onAddInline={handleAddPlayer}
        />
      </Modal>
    </ScrollView>
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
    contentContainer: {
      padding: spacing.lg,
      paddingBottom: spacing.xxl,
    },
    sectionTitle: {
      fontSize: typography.small,
      fontWeight: '700',
      color: colors.textSecondary,
      textTransform: 'uppercase',
      letterSpacing: 0.8,
      marginTop: spacing.xl,
      marginBottom: spacing.md,
    },
    // Segmented mode pill toggle
    modeSelector: {
      flexDirection: 'row',
      backgroundColor: colors.card,
      borderRadius: 12,
      padding: 4,
      ...shadows.small,
    },
    modePill: {
      flex: 1,
      paddingVertical: spacing.md,
      borderRadius: 10,
      alignItems: 'center',
    },
    modePillActive: {
      backgroundColor: colors.secondary,
    },
    modePillText: {
      fontSize: typography.h2,
      fontWeight: '700',
      color: colors.textSecondary,
    },
    modePillTextActive: {
      color: '#FFFFFF',
    },
    // Double-out toggle row
    toggleRow: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      backgroundColor: colors.card,
      borderRadius: 12,
      paddingVertical: spacing.md,
      paddingHorizontal: spacing.lg,
      ...shadows.small,
    },
    toggleInfo: {
      flex: 1,
    },
    toggleLabel: {
      fontSize: typography.body,
      fontWeight: '600',
      color: colors.text,
    },
    toggleDescription: {
      fontSize: typography.tiny,
      color: colors.textSecondary,
      marginTop: 2,
    },
    toggleTrack: {
      width: 48,
      height: 28,
      borderRadius: 14,
      backgroundColor: colors.border,
      justifyContent: 'center',
      padding: 3,
    },
    toggleTrackActive: {
      backgroundColor: colors.success,
    },
    toggleThumb: {
      width: 22,
      height: 22,
      borderRadius: 11,
      backgroundColor: '#FFFFFF',
      ...shadows.small,
    },
    toggleThumbActive: {
      alignSelf: 'flex-end',
    },
    // Player card rows
    playerCard: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: colors.card,
      borderRadius: 12,
      padding: spacing.md,
      marginBottom: spacing.sm,
      ...shadows.small,
    },
    avatarCircle: {
      width: 40,
      height: 40,
      borderRadius: 20,
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: spacing.md,
    },
    avatarText: {
      fontSize: typography.small,
      fontWeight: '700',
      color: '#FFFFFF',
    },
    playerInput: {
      flex: 1,
      fontSize: typography.body,
      color: colors.text,
      paddingVertical: 0,
    },
    removeButton: {
      width: 32,
      height: 32,
      borderRadius: 16,
      backgroundColor: colors.error + '15',
      justifyContent: 'center',
      alignItems: 'center',
      marginLeft: spacing.sm,
    },
    removeButtonText: {
      fontSize: 20,
      color: colors.error,
      fontWeight: '700',
      lineHeight: 22,
    },
    addPlayerRow: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: spacing.xl,
      gap: spacing.sm,
    },
    addPlayerInput: {
      flex: 1,
      backgroundColor: colors.card,
      borderRadius: 12,
      paddingHorizontal: spacing.md,
      paddingVertical: spacing.md,
      ...shadows.small,
    },
    addButton: {
      backgroundColor: colors.secondary,
      paddingVertical: spacing.md,
      paddingHorizontal: spacing.lg,
      borderRadius: 12,
    },
    addButtonText: {
      fontSize: typography.body,
      fontWeight: '700',
      color: '#FFFFFF',
    },
    // CTA
    startButton: {
      backgroundColor: colors.primary,
      paddingVertical: spacing.lg,
      borderRadius: 12,
      alignItems: 'center',
      ...shadows.medium,
    },
    startButtonDisabled: {
      opacity: 0.5,
    },
    startButtonText: {
      fontSize: typography.h3,
      fontWeight: '700',
      color: colors.textOnPrimary,
    },
  });
}
