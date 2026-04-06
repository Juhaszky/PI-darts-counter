import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, SPACING, TYPOGRAPHY, SHADOWS } from '../constants/theme';
import type { Player } from '../types/game.types';

interface PlayerCardProps {
  player: Player;
  gameMode: '301' | '501';
}

export default function PlayerCard({ player, gameMode }: PlayerCardProps) {
  const startScore = gameMode === '301' ? 301 : 501;
  const progressPercent = ((startScore - player.score) / startScore) * 100;

  return (
    <View style={[styles.container, player.isCurrent && styles.activeContainer]}>
      <Text style={styles.name}>{player.name}</Text>
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

const styles = StyleSheet.create({
  container: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: SPACING.md,
    marginVertical: SPACING.sm,
    ...SHADOWS.medium,
  },
  activeContainer: {
    borderWidth: 2,
    borderColor: COLORS.primary,
  },
  name: {
    fontSize: TYPOGRAPHY.h3,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.xs,
  },
  score: {
    fontSize: TYPOGRAPHY.h1,
    fontWeight: 'bold',
    color: COLORS.primary,
    marginBottom: SPACING.sm,
  },
  progressBar: {
    height: 8,
    backgroundColor: COLORS.background,
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: COLORS.success,
  },
  throwIndicator: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: SPACING.sm,
  },
  throwDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: COLORS.background,
    marginHorizontal: SPACING.xs,
  },
  throwDotActive: {
    backgroundColor: COLORS.primary,
  },
});
