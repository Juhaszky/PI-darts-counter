import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useGame } from '../hooks/useGame';
import { useTheme } from '../themes/ThemeContext';
import type { Theme } from '../themes';

interface PlayersModalProps {
  onClose: () => void;
  onConfirm: (selectedNames: string[]) => void;
  onAddInline: (name: string) => void;
}

const AVATAR_COLORS = ['#E8393A', '#2D6A4F', '#F59E0B', '#6366F1', '#EC4899'];

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length] ?? AVATAR_COLORS[0];
}

export default function PlayersModal({ onClose, onConfirm, onAddInline }: PlayersModalProps) {
  const { fetchAllPlayers } = useGame();
  const { colors, spacing, typography, shadows } = useTheme();

  const [availablePlayers, setAvailablePlayers] = useState<string[]>([]);
  const [selectedNames, setSelectedNames] = useState<Set<string>>(new Set());
  const [newPlayerName, setNewPlayerName] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const names = await fetchAllPlayers();
        if (!cancelled) {
          setAvailablePlayers(names);
        }
      } catch {
        if (!cancelled) {
          setError('Failed to load players. Check your connection and try again.');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [fetchAllPlayers]);

  const toggleSelection = useCallback((name: string) => {
    setSelectedNames((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  }, []);

  const handleAddInline = useCallback(() => {
    const trimmed = newPlayerName.trim();
    if (!trimmed) return;
    onAddInline(trimmed);
    setNewPlayerName('');
    setAvailablePlayers((prev) =>
      prev.includes(trimmed) ? prev : [...prev, trimmed].sort((a, b) => a.localeCompare(b)),
    );
    setSelectedNames((prev) => new Set(prev).add(trimmed));
  }, [newPlayerName, onAddInline]);

  const handleConfirm = useCallback(() => {
    onConfirm(Array.from(selectedNames));
  }, [onConfirm, selectedNames]);

  const styles = createStyles(colors, spacing, typography, shadows);

  const renderItem = useCallback(
    ({ item }: { item: string }) => {
      const isSelected = selectedNames.has(item);
      const avatarColor = getAvatarColor(item);
      return (
        <Pressable
          style={[styles.playerRow, isSelected && styles.playerRowSelected]}
          onPress={() => toggleSelection(item)}
          accessibilityRole="checkbox"
          accessibilityState={{ checked: isSelected }}
        >
          <View style={[styles.avatar, { backgroundColor: avatarColor + (isSelected ? 'FF' : '33') }]}>
            <Text style={[styles.avatarText, { color: isSelected ? '#FFFFFF' : avatarColor }]}>
              {item[0]?.toUpperCase() ?? '?'}
            </Text>
          </View>
          <Text style={[styles.playerName, isSelected && styles.playerNameSelected]}>
            {item}
          </Text>
          {isSelected && (
            <View style={styles.checkmark}>
              <Text style={styles.checkmarkText}>✓</Text>
            </View>
          )}
        </Pressable>
      );
    },
    [selectedNames, toggleSelection, styles],
  );

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Select Players</Text>
          <Text style={styles.subtitle}>
            {selectedNames.size > 0
              ? `${selectedNames.size} selected`
              : 'Tap to select'}
          </Text>
        </View>

        {/* Player list */}
        {isLoading ? (
          <View style={styles.centeredState}>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={styles.stateText}>Loading players...</Text>
          </View>
        ) : error !== null ? (
          <View style={styles.centeredState}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : (
          <FlatList
            data={availablePlayers}
            keyExtractor={(item) => item}
            renderItem={renderItem}
            style={styles.list}
            contentContainerStyle={styles.listContent}
            ListEmptyComponent={
              <Text style={styles.emptyText}>No existing players found.</Text>
            }
          />
        )}

        {/* Add new player inline */}
        <View style={styles.inlineAdd}>
          <TextInput
            style={styles.textInput}
            placeholder="New player name..."
            placeholderTextColor={colors.placeholder}
            value={newPlayerName}
            onChangeText={setNewPlayerName}
            onSubmitEditing={handleAddInline}
            returnKeyType="done"
            autoCapitalize="words"
          />
          <Pressable
            style={[styles.addButton, !newPlayerName.trim() && styles.addButtonDisabled]}
            onPress={handleAddInline}
            disabled={!newPlayerName.trim()}
          >
            <Text style={styles.addButtonText}>Add</Text>
          </Pressable>
        </View>

        {/* Actions */}
        <View style={styles.actions}>
          <Pressable style={styles.cancelButton} onPress={onClose}>
            <Text style={styles.cancelButtonText}>Cancel</Text>
          </Pressable>
          <Pressable
            style={[styles.confirmButton, selectedNames.size === 0 && styles.confirmButtonDisabled]}
            onPress={handleConfirm}
            disabled={selectedNames.size === 0}
          >
            <Text style={styles.confirmButtonText}>
              Confirm ({selectedNames.size})
            </Text>
          </Pressable>
        </View>
      </View>
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
    safeArea: {
      flex: 1,
      backgroundColor: colors.background,
    },
    container: {
      flex: 1,
      padding: spacing.lg,
    },
    header: {
      marginBottom: spacing.lg,
    },
    title: {
      fontSize: typography.h2,
      fontWeight: '800',
      color: colors.text,
    },
    subtitle: {
      fontSize: typography.small,
      color: colors.textSecondary,
      marginTop: spacing.xs,
    },
    list: {
      flex: 1,
    },
    listContent: {
      paddingBottom: spacing.md,
    },
    playerRow: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingVertical: spacing.md,
      paddingHorizontal: spacing.md,
      backgroundColor: colors.card,
      borderRadius: 12,
      marginBottom: spacing.sm,
      borderWidth: 1,
      borderColor: colors.border,
      ...shadows.small,
    },
    playerRowSelected: {
      borderColor: colors.primary,
      borderWidth: 2,
    },
    avatar: {
      width: 40,
      height: 40,
      borderRadius: 20,
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: spacing.md,
    },
    avatarText: {
      fontSize: typography.body,
      fontWeight: '700',
    },
    playerName: {
      flex: 1,
      fontSize: typography.body,
      color: colors.text,
      fontWeight: '500',
    },
    playerNameSelected: {
      fontWeight: '700',
      color: colors.primary,
    },
    checkmark: {
      width: 24,
      height: 24,
      borderRadius: 12,
      backgroundColor: colors.primary,
      justifyContent: 'center',
      alignItems: 'center',
    },
    checkmarkText: {
      fontSize: typography.tiny,
      color: '#FFFFFF',
      fontWeight: '800',
    },
    centeredState: {
      flex: 1,
      alignItems: 'center',
      justifyContent: 'center',
      gap: spacing.sm,
    },
    stateText: {
      fontSize: typography.small,
      color: colors.textSecondary,
      marginTop: spacing.sm,
    },
    errorText: {
      fontSize: typography.small,
      color: colors.error,
      textAlign: 'center',
      paddingHorizontal: spacing.md,
    },
    emptyText: {
      fontSize: typography.body,
      color: colors.textSecondary,
      textAlign: 'center',
      marginTop: spacing.lg,
    },
    inlineAdd: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: spacing.sm,
      marginBottom: spacing.md,
    },
    textInput: {
      flex: 1,
      height: 48,
      borderRadius: 12,
      borderWidth: 1,
      borderColor: colors.border,
      paddingHorizontal: spacing.md,
      color: colors.text,
      fontSize: typography.body,
      backgroundColor: colors.card,
    },
    addButton: {
      height: 48,
      paddingHorizontal: spacing.lg,
      borderRadius: 12,
      backgroundColor: colors.secondary,
      alignItems: 'center',
      justifyContent: 'center',
    },
    addButtonDisabled: {
      backgroundColor: colors.border,
    },
    addButtonText: {
      fontSize: typography.body,
      color: '#FFFFFF',
      fontWeight: '700',
    },
    actions: {
      flexDirection: 'row',
      gap: spacing.sm,
    },
    cancelButton: {
      flex: 1,
      height: 52,
      borderRadius: 12,
      borderWidth: 1,
      borderColor: colors.border,
      alignItems: 'center',
      justifyContent: 'center',
    },
    cancelButtonText: {
      fontSize: typography.body,
      color: colors.textSecondary,
      fontWeight: '700',
    },
    confirmButton: {
      flex: 1,
      height: 52,
      borderRadius: 12,
      backgroundColor: colors.primary,
      alignItems: 'center',
      justifyContent: 'center',
    },
    confirmButtonDisabled: {
      backgroundColor: colors.border,
    },
    confirmButtonText: {
      fontSize: typography.body,
      color: '#FFFFFF',
      fontWeight: '700',
    },
  });
}
