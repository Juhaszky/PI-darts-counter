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
import { COLORS, SPACING, TYPOGRAPHY, SHADOWS } from '../constants/theme';
import { GAME_MODES } from '../constants/config';
import { useConnectionStore } from '../store/connectionStore';
import { useGame } from '../hooks/useGame';
import { wsService } from '../services/websocketService';
import type { RootStackParamList } from '../navigation/types';
import type { GameMode } from '../types/game.types';
import PlayerModal from '../components/PlayersModal';

type SetupScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Setup'>;

export default function SetupScreen() {
  const navigation = useNavigation<SetupScreenNavigationProp>();
  const { host, port, setGameId } = useConnectionStore();
  const { createGame, startGame } = useGame();

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
      Alert.alert('Hiba', 'Legalább 2 játékos szükséges!');
      return;
    }

    setIsLoading(true);

    try {
      // Create game
      const response = await createGame({
        mode: gameMode,
        doubleOut,
        players: validPlayers.map((name) => ({ name })),
      });

      // Store game ID
      setGameId(response.gameId);

      // Connect WebSocket
      wsService.connect(host, port, response.gameId);

      // Start game
      await startGame();

      // Navigate to game screen
      navigation.navigate('Game', { gameId: response.gameId });
    } catch (error) {
      console.error('Failed to start game:', error);
      Alert.alert('Hiba', 'Nem sikerült elindítani a játékot!');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.sectionTitle}>Játékmód</Text>
      <View style={styles.modeSelector}>
        {Object.entries(GAME_MODES).map(([mode, { label }]) => (
          <TouchableOpacity
            key={mode}
            style={[
              styles.modeButton,
              gameMode === mode && styles.modeButtonActive,
            ]}
            onPress={() => setGameMode(mode as GameMode)}
          >
            <Text style={styles.modeButtonText}>{label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.sectionTitle}>Double Out</Text>
      <TouchableOpacity
        style={styles.toggleButton}
        onPress={() => setDoubleOut(!doubleOut)}
      >
        <View style={[styles.checkbox, doubleOut && styles.checkboxActive]} />
        <Text style={styles.toggleText}>
          {doubleOut ? 'Bekapcsolva' : 'Kikapcsolva'}
        </Text>
      </TouchableOpacity>

      <Text style={styles.sectionTitle}>Játékosok</Text>
      {/* {players.map((player, index) => (
        <View key={index} style={styles.playerRow}>
          <TextInput
            style={styles.playerInput}
            value={player}
            onChangeText={(text) => {
              const updated = [...players];
              updated[index] = text;
              setPlayers(updated);
            }}
            placeholder={`Játékos ${index + 1}`}
            placeholderTextColor={COLORS.textSecondary}
          />
          {players.length > 2 && (
            <TouchableOpacity
              style={styles.removeButton}
              onPress={() => handleRemovePlayer(index)}
            >
              <Text style={styles.removeButtonText}>×</Text>
            </TouchableOpacity>
          )}
        </View>
      ))} */}

      <View style={styles.addPlayerRow}>
        <TextInput
          style={[styles.playerInput, { flex: 1 }]}
          value={newPlayerName}
          onChangeText={setNewPlayerName}
          placeholder="Új játékos neve"
          placeholderTextColor={COLORS.textSecondary}
          onSubmitEditing={handleAddPlayer}
        />
        <TouchableOpacity style={styles.addButton} onPress={() => {
          setIsModalOpen(true);
        }}>
          <Text style={styles.addButtonText}>+ Hozzáad</Text>
        </TouchableOpacity>
      </View>

      <TouchableOpacity
        style={[styles.startButton, isLoading && styles.startButtonDisabled]}
        onPress={handleStartGame}
        disabled={isLoading}
      >
        {isLoading ? (
          <ActivityIndicator color={COLORS.text} />
        ) : (
          <Text style={styles.startButtonText}>Játék indítása</Text>
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

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  contentContainer: {
    padding: SPACING.lg,
  },
  sectionTitle: {
    fontSize: TYPOGRAPHY.h3,
    fontWeight: 'bold',
    color: COLORS.text,
    marginTop: SPACING.lg,
    marginBottom: SPACING.md,
  },
  modeSelector: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: SPACING.lg,
  },
  modeButton: {
    flex: 1,
    backgroundColor: COLORS.card,
    paddingVertical: SPACING.lg,
    borderRadius: 12,
    alignItems: 'center',
    marginHorizontal: SPACING.sm,
    ...SHADOWS.small,
  },
  modeButtonActive: {
    backgroundColor: COLORS.primary,
  },
  modeButtonText: {
    fontSize: TYPOGRAPHY.h2,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  toggleButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.card,
    paddingVertical: SPACING.md,
    paddingHorizontal: SPACING.md,
    borderRadius: 12,
    marginBottom: SPACING.lg,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: COLORS.textSecondary,
    marginRight: SPACING.md,
  },
  checkboxActive: {
    backgroundColor: COLORS.success,
    borderColor: COLORS.success,
  },
  toggleText: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.text,
  },
  playerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.sm,
  },
  playerInput: {
    flex: 1,
    backgroundColor: COLORS.card,
    borderRadius: 8,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.md,
    fontSize: TYPOGRAPHY.body,
    color: COLORS.text,
  },
  removeButton: {
    width: 40,
    height: 40,
    backgroundColor: COLORS.error,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: SPACING.sm,
  },
  removeButtonText: {
    fontSize: 24,
    color: COLORS.text,
    fontWeight: 'bold',
  },
  addPlayerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.xl,
  },
  addButton: {
    backgroundColor: COLORS.success,
    paddingVertical: SPACING.md,
    paddingHorizontal: SPACING.lg,
    borderRadius: 8,
    marginLeft: SPACING.sm,
  },
  addButtonText: {
    fontSize: TYPOGRAPHY.body,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  startButton: {
    backgroundColor: COLORS.primary,
    paddingVertical: SPACING.lg,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: SPACING.lg,
    ...SHADOWS.medium,
  },
  startButtonDisabled: {
    opacity: 0.5,
  },
  startButtonText: {
    fontSize: TYPOGRAPHY.h3,
    fontWeight: 'bold',
    color: COLORS.text,
  },
});
