import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../themes/ThemeContext';
import type { Theme } from '../themes';
import type { ThrowData } from '../types/game.types';

interface ThrowSlotsProps {
  lastThrow: ThrowData | null;
  throwsThisTurn: number;
}

export default function ThrowSlots({ lastThrow, throwsThisTurn }: ThrowSlotsProps) {
  const { colors, spacing, typography, shadows } = useTheme();
  const styles = createStyles(colors, spacing, typography, shadows);

  const renderSlot = (slotNumber: 1 | 2 | 3) => {
    const isActive = lastThrow !== null && lastThrow.throwNumber === slotNumber;
    const isFilled = throwsThisTurn >= slotNumber;

    return (
      <View key={slotNumber} style={[styles.slot, isActive && styles.slotActive]}>
        <Text style={styles.slotLabel}>Dart {slotNumber}</Text>
        {isFilled && lastThrow !== null ? (
          <>
            <Text style={styles.segmentName}>{lastThrow.segmentName}</Text>
            <Text style={styles.score}>{lastThrow.totalScore}</Text>
          </>
        ) : (
          <Text style={styles.emptySlot}>—</Text>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {[1, 2, 3].map((i) => renderSlot(i as 1 | 2 | 3))}
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
      flexDirection: 'row',
      justifyContent: 'space-between',
      marginVertical: spacing.md,
      gap: spacing.sm,
    },
    slot: {
      flex: 1,
      backgroundColor: colors.background,
      borderRadius: 12,
      borderWidth: 1,
      borderColor: colors.border,
      padding: spacing.md,
      alignItems: 'center',
      minHeight: 80,
      justifyContent: 'center',
    },
    slotActive: {
      borderColor: colors.primary,
      borderWidth: 2,
      backgroundColor: colors.primary + '08',
    },
    slotLabel: {
      fontSize: typography.tiny,
      color: colors.placeholder,
      fontWeight: '600',
      textTransform: 'uppercase',
      letterSpacing: 0.5,
      marginBottom: spacing.xs,
    },
    segmentName: {
      fontSize: typography.small,
      fontWeight: '700',
      color: colors.text,
      marginBottom: 2,
    },
    score: {
      fontSize: typography.h2,
      fontWeight: '800',
      color: colors.warning,
    },
    emptySlot: {
      fontSize: typography.h3,
      color: colors.border,
      fontWeight: '300',
    },
  });
}
