import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useTheme } from '../themes/ThemeContext';
import type { Theme } from '../themes';
import { useGameStore } from '../store/gameStore';

export default function StatsScreen() {
  const navigation = useNavigation();
  const { gameOverData, gameState } = useGameStore();
  const { colors, spacing, typography, shadows } = useTheme();

  const styles = createStyles(colors, spacing, typography, shadows);

  if (!gameOverData || !gameState) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>No stats available</Text>
      </View>
    );
  }

  const { winnerName, finalThrow, totalRounds, stats } = gameOverData;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Winner card — dark green background */}
      <View style={styles.winnerCard}>
        <Text style={styles.winnerTrophy}>🏆</Text>
        <Text style={styles.winnerLabel}>You won</Text>
        <Text style={styles.winnerName}>{winnerName}</Text>
        <View style={styles.winnerStats}>
          <View style={styles.winnerStatItem}>
            <Text style={styles.winnerStatValue}>{finalThrow}</Text>
            <Text style={styles.winnerStatLabel}>Checkout</Text>
          </View>
          <View style={styles.winnerStatDivider} />
          <View style={styles.winnerStatItem}>
            <Text style={styles.winnerStatValue}>{totalRounds}</Text>
            <Text style={styles.winnerStatLabel}>Rounds</Text>
          </View>
        </View>
      </View>

      {/* Player stat cards */}
      <Text style={styles.sectionTitle}>Player Statistics</Text>

      {Object.entries(stats).map(([playerName, playerStats]) => (
        <View key={playerName} style={styles.statCard}>
          <View style={styles.statCardHeader}>
            <View style={styles.statAvatar}>
              <Text style={styles.statAvatarText}>
                {playerName[0]?.toUpperCase() ?? '?'}
              </Text>
            </View>
            <Text style={styles.statPlayerName}>{playerName}</Text>
            {playerName === winnerName && (
              <View style={styles.winnerBadge}>
                <Text style={styles.winnerBadgeText}>Winner</Text>
              </View>
            )}
          </View>

          <View style={styles.statGrid}>
            <View style={styles.statGridItem}>
              <Text style={[styles.statGridValue, styles.statHighlight]}>
                {playerStats.avgPerDart.toFixed(1)}
              </Text>
              <Text style={styles.statGridLabel}>Avg / dart</Text>
            </View>
            <View style={styles.statGridDivider} />
            <View style={styles.statGridItem}>
              <Text style={[styles.statGridValue, styles.statHighlight]}>
                {playerStats.highestTurn}
              </Text>
              <Text style={styles.statGridLabel}>Best turn</Text>
            </View>
          </View>
        </View>
      ))}

      <TouchableOpacity
        style={styles.homeButton}
        onPress={() => navigation.navigate('Home' as never)}
        activeOpacity={0.85}
      >
        <Text style={styles.homeButtonText}>Back to Home</Text>
      </TouchableOpacity>
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
    content: {
      padding: spacing.lg,
      paddingBottom: spacing.xxl,
    },
    emptyContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: colors.background,
    },
    emptyText: {
      fontSize: typography.body,
      color: colors.textSecondary,
    },
    // Winner card
    winnerCard: {
      backgroundColor: colors.success,
      borderRadius: 16,
      padding: spacing.xl,
      alignItems: 'center',
      marginBottom: spacing.xl,
      ...shadows.large,
    },
    winnerTrophy: {
      fontSize: 48,
      marginBottom: spacing.sm,
    },
    winnerLabel: {
      fontSize: typography.small,
      fontWeight: '700',
      color: 'rgba(255,255,255,0.75)',
      textTransform: 'uppercase',
      letterSpacing: 1,
      marginBottom: spacing.xs,
    },
    winnerName: {
      fontSize: typography.h1,
      fontWeight: '800',
      color: '#FFFFFF',
      marginBottom: spacing.xl,
    },
    winnerStats: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: 'rgba(255,255,255,0.15)',
      borderRadius: 12,
      paddingVertical: spacing.md,
      paddingHorizontal: spacing.xl,
      gap: spacing.xl,
    },
    winnerStatItem: {
      alignItems: 'center',
    },
    winnerStatValue: {
      fontSize: typography.h2,
      fontWeight: '800',
      color: '#FFFFFF',
    },
    winnerStatLabel: {
      fontSize: typography.tiny,
      color: 'rgba(255,255,255,0.7)',
      marginTop: 2,
    },
    winnerStatDivider: {
      width: 1,
      height: 32,
      backgroundColor: 'rgba(255,255,255,0.3)',
    },
    // Section
    sectionTitle: {
      fontSize: typography.small,
      fontWeight: '700',
      color: colors.textSecondary,
      textTransform: 'uppercase',
      letterSpacing: 0.8,
      marginBottom: spacing.md,
    },
    // Stat cards
    statCard: {
      backgroundColor: colors.card,
      borderRadius: 16,
      padding: spacing.lg,
      marginBottom: spacing.md,
      ...shadows.medium,
    },
    statCardHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: spacing.lg,
    },
    statAvatar: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: colors.primary + '20',
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: spacing.md,
    },
    statAvatarText: {
      fontSize: typography.body,
      fontWeight: '700',
      color: colors.primary,
    },
    statPlayerName: {
      flex: 1,
      fontSize: typography.h3,
      fontWeight: '700',
      color: colors.text,
    },
    winnerBadge: {
      backgroundColor: colors.success + '20',
      borderRadius: 8,
      paddingVertical: 4,
      paddingHorizontal: spacing.sm,
    },
    winnerBadgeText: {
      fontSize: typography.tiny,
      fontWeight: '700',
      color: colors.success,
    },
    statGrid: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: colors.background,
      borderRadius: 12,
      paddingVertical: spacing.md,
    },
    statGridItem: {
      flex: 1,
      alignItems: 'center',
    },
    statGridDivider: {
      width: 1,
      height: 36,
      backgroundColor: colors.border,
    },
    statGridValue: {
      fontSize: typography.h2,
      fontWeight: '800',
      color: colors.text,
    },
    statHighlight: {
      color: colors.warning,
    },
    statGridLabel: {
      fontSize: typography.tiny,
      color: colors.textSecondary,
      marginTop: 2,
    },
    // CTA
    homeButton: {
      backgroundColor: colors.secondary,
      paddingVertical: spacing.lg,
      borderRadius: 12,
      alignItems: 'center',
      marginTop: spacing.xl,
    },
    homeButtonText: {
      fontSize: typography.body,
      fontWeight: '700',
      color: '#FFFFFF',
    },
  });
}
