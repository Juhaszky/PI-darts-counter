import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../themes/ThemeContext';
import type { Theme } from '../themes';
import type { Player } from '../types/game.types';

interface PlayerCardProps {
  player: Player;
  gameMode: '301' | '501';
}

export default function PlayerCard({ player, gameMode }: PlayerCardProps) {
  const { colors, spacing, typography, shadows } = useTheme();
  const startScore = gameMode === '301' ? 301 : 501;
  const progressPercent = ((startScore - player.score) / startScore) * 100;

  const styles = createStyles(colors, spacing, typography, shadows);

  return (
    <View style={[styles.container, player.isCurrent && styles.activeContainer]}>
      <View style={styles.topRow}>
        <Text style={styles.name}>{player.name}</Text>
        {player.isCurrent && (
          <View style={styles.activeBadge}>
            <Text style={styles.activeBadgeText}>Your turn</Text>
          </View>
        )}
      </View>

      <Text style={styles.score}>{player.score}</Text>

      <View style={styles.progressBar}>
        <View style={[styles.progressFill, { width: `${progressPercent}%` }]} />
      </View>

      {player.isCurrent && (
        <View style={styles.throwIndicator}>
          {[1, 2, 3].map((i) => (
            <View
              key={i}
              style={[
                styles.throwDot,
                i <= player.throwsThisTurn && styles.throwDotActive,
              ]}
            />
          ))}
        </View>
      )}
    </View>
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
      backgroundColor: colors.card,
      borderRadius: 16,
      padding: spacing.lg,
      marginVertical: spacing.sm,
      borderWidth: 1,
      borderColor: colors.border,
      ...shadows.small,
    },
    activeContainer: {
      borderColor: colors.primary,
      borderWidth: 2,
      ...shadows.medium,
    },
    topRow: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: spacing.xs,
    },
    name: {
      fontSize: typography.body,
      fontWeight: '600',
      color: colors.textSecondary,
    },
    activeBadge: {
      backgroundColor: colors.primary + '18',
      borderRadius: 8,
      paddingVertical: 3,
      paddingHorizontal: spacing.sm,
    },
    activeBadgeText: {
      fontSize: typography.tiny,
      fontWeight: '700',
      color: colors.primary,
    },
    score: {
      fontSize: typography.h1,
      fontWeight: '800',
      color: colors.text,
      marginBottom: spacing.md,
    },
    progressBar: {
      height: 6,
      backgroundColor: colors.border,
      borderRadius: 3,
      overflow: 'hidden',
    },
    progressFill: {
      height: '100%',
      backgroundColor: colors.success,
      borderRadius: 3,
    },
    throwIndicator: {
      flexDirection: 'row',
      justifyContent: 'center',
      marginTop: spacing.md,
      gap: spacing.sm,
    },
    throwDot: {
      width: 10,
      height: 10,
      borderRadius: 5,
      backgroundColor: colors.border,
    },
    throwDotActive: {
      backgroundColor: colors.primary,
    },
  });
}
