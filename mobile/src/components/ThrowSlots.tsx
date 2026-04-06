import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, SPACING, TYPOGRAPHY, SHADOWS } from '../constants/theme';
import type { ThrowData } from '../types/game.types';

interface ThrowSlotsProps {
  lastThrow: ThrowData | null;
  throwsThisTurn: number;
}

export default function ThrowSlots({ lastThrow, throwsThisTurn }: ThrowSlotsProps) {
  const renderSlot = (slotNumber: 1 | 2 | 3) => {
    const isActive = lastThrow && lastThrow.throwNumber === slotNumber;
    const isFilled = throwsThisTurn >= slotNumber;

    return (
      <View key={slotNumber} style={[styles.slot, isActive && styles.slotActive]}>
        <Text style={styles.slotLabel}>{slotNumber}. nyíl</Text>
        {isFilled && lastThrow ? (
          <>
            <Text style={styles.segmentName}>{lastThrow.segmentName}</Text>
            <Text style={styles.score}>{lastThrow.totalScore}</Text>
          </>
        ) : (
          <Text style={styles.emptySlot}>-</Text>
        )}
      </View>
    );
  };

  return <View style={styles.container}>{[1, 2, 3].map((i) => renderSlot(i as 1 | 2 | 3))}</View>;
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginVertical: SPACING.lg,
  },
  slot: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: SPACING.md,
    minWidth: 90,
    alignItems: 'center',
    ...SHADOWS.small,
  },
  slotActive: {
    borderWidth: 2,
    borderColor: COLORS.primary,
  },
  slotLabel: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textSecondary,
    marginBottom: SPACING.xs,
  },
  segmentName: {
    fontSize: TYPOGRAPHY.h3,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.xs,
  },
  score: {
    fontSize: TYPOGRAPHY.h2,
    fontWeight: 'bold',
    color: COLORS.success,
  },
  emptySlot: {
    fontSize: TYPOGRAPHY.h1,
    color: COLORS.textSecondary,
  },
});
