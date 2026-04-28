import React, { useState } from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { useTheme } from '../themes/ThemeContext';
import type { Theme } from '../themes';

interface ManualScoreModalProps {
  visible: boolean;
  onClose: () => void;
  onSubmit: (segment: number, multiplier: number) => void;
}

const SEGMENTS = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5];
const MULTIPLIERS = [1, 2, 3];
const SPECIAL = [25, 50];

const MULTIPLIER_LABELS: Record<number, string> = {
  1: 'Single',
  2: 'Double',
  3: 'Triple',
};

export default function ManualScoreModal({ visible, onClose, onSubmit }: ManualScoreModalProps) {
  const { colors, spacing, typography, shadows } = useTheme();
  const [selectedSegment, setSelectedSegment] = useState<number | null>(null);
  const [selectedMultiplier, setSelectedMultiplier] = useState<number>(1);

  const handleSubmit = () => {
    if (selectedSegment !== null) {
      onSubmit(selectedSegment, selectedMultiplier);
      setSelectedSegment(null);
      setSelectedMultiplier(1);
      onClose();
    }
  };

  const styles = createStyles(colors, spacing, typography, shadows);

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.container}>
          <View style={styles.titleRow}>
            <Text style={styles.title}>Manual Score</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <Text style={styles.closeButtonText}>×</Text>
            </TouchableOpacity>
          </View>

          {/* Multiplier pills */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Multiplier</Text>
            <View style={styles.multiplierRow}>
              {MULTIPLIERS.map((mult) => {
                const isActive = selectedMultiplier === mult;
                return (
                  <TouchableOpacity
                    key={mult}
                    style={[styles.multiplierPill, isActive && styles.multiplierPillActive]}
                    onPress={() => setSelectedMultiplier(mult)}
                    activeOpacity={0.8}
                  >
                    <Text style={[styles.multiplierText, isActive && styles.multiplierTextActive]}>
                      {MULTIPLIER_LABELS[mult]}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          {/* Special segments */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Special</Text>
            <View style={styles.segmentGrid}>
              {SPECIAL.map((seg) => {
                const isActive = selectedSegment === seg;
                return (
                  <TouchableOpacity
                    key={seg}
                    style={[styles.segmentButton, styles.specialButton, isActive && styles.segmentButtonActive]}
                    onPress={() => setSelectedSegment(seg)}
                    activeOpacity={0.8}
                  >
                    <Text style={[styles.segmentText, isActive && styles.segmentTextActive]}>
                      {seg === 25 ? 'Bull' : 'Bullseye'}
                    </Text>
                    <Text style={[styles.segmentScore, isActive && styles.segmentTextActive]}>
                      {seg}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          {/* Number segments */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Segments</Text>
            <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
              <View style={styles.segmentGrid}>
                {SEGMENTS.map((seg) => {
                  const isActive = selectedSegment === seg;
                  return (
                    <TouchableOpacity
                      key={seg}
                      style={[styles.segmentButton, isActive && styles.segmentButtonActive]}
                      onPress={() => setSelectedSegment(seg)}
                      activeOpacity={0.8}
                    >
                      <Text style={[styles.segmentText, isActive && styles.segmentTextActive]}>
                        {seg}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </ScrollView>
          </View>

          {/* Selected preview + actions */}
          {selectedSegment !== null && (
            <View style={styles.previewRow}>
              <Text style={styles.previewText}>
                {selectedMultiplier > 1 ? `${MULTIPLIER_LABELS[selectedMultiplier]} ` : ''}
                {selectedSegment === 25 ? 'Bull' : selectedSegment === 50 ? 'Bullseye' : selectedSegment}
              </Text>
              <Text style={styles.previewScore}>
                = {selectedSegment * selectedMultiplier} pts
              </Text>
            </View>
          )}

          <View style={styles.actionRow}>
            <TouchableOpacity style={styles.cancelButton} onPress={onClose} activeOpacity={0.8}>
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.submitButton, selectedSegment === null && styles.submitButtonDisabled]}
              onPress={handleSubmit}
              disabled={selectedSegment === null}
              activeOpacity={0.85}
            >
              <Text style={styles.submitButtonText}>Confirm</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

function createStyles(
  colors: Theme['colors'],
  spacing: Theme['spacing'],
  typography: Theme['typography'],
  shadows: Theme['shadows'],
) {
  return StyleSheet.create({
    overlay: {
      flex: 1,
      backgroundColor: colors.overlay,
      justifyContent: 'flex-end',
    },
    container: {
      backgroundColor: colors.card,
      borderTopLeftRadius: 24,
      borderTopRightRadius: 24,
      padding: spacing.lg,
      paddingBottom: spacing.xxl,
      ...shadows.large,
    },
    titleRow: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: spacing.lg,
    },
    title: {
      fontSize: typography.h2,
      fontWeight: '800',
      color: colors.text,
    },
    closeButton: {
      width: 32,
      height: 32,
      borderRadius: 16,
      backgroundColor: colors.background,
      justifyContent: 'center',
      alignItems: 'center',
    },
    closeButtonText: {
      fontSize: 22,
      color: colors.textSecondary,
      lineHeight: 26,
    },
    section: {
      marginBottom: spacing.lg,
    },
    sectionTitle: {
      fontSize: typography.tiny,
      fontWeight: '700',
      color: colors.textSecondary,
      textTransform: 'uppercase',
      letterSpacing: 0.8,
      marginBottom: spacing.sm,
    },
    multiplierRow: {
      flexDirection: 'row',
      backgroundColor: colors.background,
      borderRadius: 12,
      padding: 4,
      gap: 4,
    },
    multiplierPill: {
      flex: 1,
      paddingVertical: spacing.md,
      borderRadius: 10,
      alignItems: 'center',
    },
    multiplierPillActive: {
      backgroundColor: colors.secondary,
    },
    multiplierText: {
      color: colors.textSecondary,
      fontSize: typography.small,
      fontWeight: '600',
    },
    multiplierTextActive: {
      color: '#FFFFFF',
      fontWeight: '700',
    },
    scrollView: {
      maxHeight: 180,
    },
    segmentGrid: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      gap: spacing.sm,
    },
    segmentButton: {
      width: '22%',
      aspectRatio: 1,
      backgroundColor: colors.background,
      borderRadius: 10,
      borderWidth: 1,
      borderColor: colors.border,
      justifyContent: 'center',
      alignItems: 'center',
    },
    specialButton: {
      width: '47%',
      aspectRatio: 2.5,
    },
    segmentButtonActive: {
      backgroundColor: colors.primary,
      borderColor: colors.primary,
    },
    segmentText: {
      color: colors.text,
      fontSize: typography.body,
      fontWeight: '700',
    },
    segmentScore: {
      color: colors.textSecondary,
      fontSize: typography.tiny,
      marginTop: 2,
    },
    segmentTextActive: {
      color: '#FFFFFF',
    },
    previewRow: {
      flexDirection: 'row',
      alignItems: 'baseline',
      justifyContent: 'center',
      backgroundColor: colors.background,
      borderRadius: 12,
      paddingVertical: spacing.md,
      marginBottom: spacing.md,
      gap: spacing.sm,
    },
    previewText: {
      fontSize: typography.h3,
      fontWeight: '700',
      color: colors.text,
    },
    previewScore: {
      fontSize: typography.h3,
      fontWeight: '800',
      color: colors.warning,
    },
    actionRow: {
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
    submitButton: {
      flex: 2,
      height: 52,
      borderRadius: 12,
      backgroundColor: colors.primary,
      alignItems: 'center',
      justifyContent: 'center',
    },
    submitButtonDisabled: {
      opacity: 0.4,
    },
    submitButtonText: {
      fontSize: typography.body,
      color: '#FFFFFF',
      fontWeight: '700',
    },
  });
}
