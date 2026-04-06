import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { COLORS, SPACING, TYPOGRAPHY, SHADOWS } from '../constants/theme';
import { useGameStore } from '../store/gameStore';

export default function StatsScreen() {
  const navigation = useNavigation();
  const { gameOverData, gameState } = useGameStore();

  if (!gameOverData || !gameState) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>Nincs elérhető statisztika</Text>
      </View>
    );
  }

  const { winnerName, finalThrow, totalRounds, stats } = gameOverData;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.winnerCard}>
        <Text style={styles.winnerTitle}>🏆 Nyertes</Text>
        <Text style={styles.winnerName}>{winnerName}</Text>
        <Text style={styles.finalThrow}>Kiszálló dobás: {finalThrow}</Text>
        <Text style={styles.rounds}>Körök száma: {totalRounds}</Text>
      </View>

      <Text style={styles.sectionTitle}>Játékos Statisztikák</Text>

      {Object.entries(stats).map(([playerName, playerStats]) => (
        <View key={playerName} style={styles.statCard}>
          <Text style={styles.playerName}>{playerName}</Text>
          <View style={styles.statRow}>
            <Text style={styles.statLabel}>Átlag / nyíl:</Text>
            <Text style={styles.statValue}>{playerStats.avgPerDart.toFixed(1)}</Text>
          </View>
          <View style={styles.statRow}>
            <Text style={styles.statLabel}>Legjobb kör:</Text>
            <Text style={styles.statValue}>{playerStats.highestTurn}</Text>
          </View>
        </View>
      ))}

      <TouchableOpacity
        style={styles.homeButton}
        onPress={() => navigation.navigate('Home' as never)}
      >
        <Text style={styles.homeButtonText}>Vissza a főoldalra</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  content: {
    padding: SPACING.lg,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.background,
  },
  emptyText: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textSecondary,
  },
  winnerCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: SPACING.xl,
    alignItems: 'center',
    marginBottom: SPACING.xl,
    ...SHADOWS.medium,
  },
  winnerTitle: {
    fontSize: TYPOGRAPHY.h3,
    color: COLORS.textSecondary,
    marginBottom: SPACING.sm,
  },
  winnerName: {
    fontSize: TYPOGRAPHY.h1,
    fontWeight: 'bold',
    color: COLORS.primary,
    marginBottom: SPACING.md,
  },
  finalThrow: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.text,
    marginBottom: SPACING.xs,
  },
  rounds: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textSecondary,
  },
  sectionTitle: {
    fontSize: TYPOGRAPHY.h3,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.md,
  },
  statCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: SPACING.lg,
    marginBottom: SPACING.md,
    ...SHADOWS.small,
  },
  playerName: {
    fontSize: TYPOGRAPHY.h3,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.md,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.sm,
  },
  statLabel: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textSecondary,
  },
  statValue: {
    fontSize: TYPOGRAPHY.body,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  homeButton: {
    backgroundColor: COLORS.primary,
    paddingVertical: SPACING.lg,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: SPACING.xl,
  },
  homeButtonText: {
    fontSize: TYPOGRAPHY.body,
    fontWeight: 'bold',
    color: COLORS.text,
  },
});
