import React, { useState } from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { COLORS, SPACING, TYPOGRAPHY, SHADOWS } from '../constants/theme';

interface ManualScoreModalProps {
  visible: boolean;
  onClose: () => void;
  onSubmit: (segment: number, multiplier: number) => void;
}

const SEGMENTS = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5];
const MULTIPLIERS = [1, 2, 3];
const SPECIAL = [25, 50]; // Bull, Bullseye

export default function ManualScoreModal({ visible, onClose, onSubmit }: ManualScoreModalProps) {
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

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.container}>
          <Text style={styles.title}>Kézi pontbevitel</Text>

          {/* Multipliers */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Szorzó</Text>
            <View style={styles.multiplierRow}>
              {MULTIPLIERS.map((mult) => (
                <TouchableOpacity
                  key={mult}
                  style={[
                    styles.multiplierButton,
                    selectedMultiplier === mult && styles.multiplierButtonActive,
                  ]}
                  onPress={() => setSelectedMultiplier(mult)}
                >
                  <Text style={styles.multiplierText}>
                    {mult === 1 ? 'Single' : mult === 2 ? 'Double' : 'Triple'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Special segments */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Speciális</Text>
            <View style={styles.segmentGrid}>
              {SPECIAL.map((seg) => (
                <TouchableOpacity
                  key={seg}
                  style={[
                    styles.segmentButton,
                    styles.specialButton,
                    selectedSegment === seg && styles.segmentButtonActive,
                  ]}
                  onPress={() => setSelectedSegment(seg)}
                >
                  <Text style={styles.segmentText}>{seg === 25 ? 'Bull' : 'Bullseye'}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Segments */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Szegmensek</Text>
            <ScrollView style={styles.scrollView}>
              <View style={styles.segmentGrid}>
                {SEGMENTS.map((seg) => (
                  <TouchableOpacity
                    key={seg}
                    style={[
                      styles.segmentButton,
                      selectedSegment === seg && styles.segmentButtonActive,
                    ]}
                    onPress={() => setSelectedSegment(seg)}
                  >
                    <Text style={styles.segmentText}>{seg}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>
          </View>

          {/* Action buttons */}
          <View style={styles.actionRow}>
            <TouchableOpacity style={[styles.button, styles.cancelButton]} onPress={onClose}>
              <Text style={styles.buttonText}>Mégse</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.button, styles.submitButton]}
              onPress={handleSubmit}
              disabled={selectedSegment === null}
            >
              <Text style={styles.buttonText}>Rögzít</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  container: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: SPACING.lg,
    width: '90%',
    maxHeight: '80%',
    ...SHADOWS.medium,
  },
  title: {
    fontSize: TYPOGRAPHY.h2,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.lg,
    textAlign: 'center',
  },
  section: {
    marginBottom: SPACING.lg,
  },
  sectionTitle: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textSecondary,
    marginBottom: SPACING.sm,
  },
  multiplierRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  multiplierButton: {
    flex: 1,
    backgroundColor: COLORS.background,
    paddingVertical: SPACING.md,
    borderRadius: 8,
    marginHorizontal: SPACING.xs,
    alignItems: 'center',
  },
  multiplierButtonActive: {
    backgroundColor: COLORS.primary,
  },
  multiplierText: {
    color: COLORS.text,
    fontSize: TYPOGRAPHY.body,
    fontWeight: 'bold',
  },
  scrollView: {
    maxHeight: 200,
  },
  segmentGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  segmentButton: {
    width: '22%',
    aspectRatio: 1,
    backgroundColor: COLORS.background,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.sm,
  },
  specialButton: {
    width: '48%',
  },
  segmentButtonActive: {
    backgroundColor: COLORS.secondary,
  },
  segmentText: {
    color: COLORS.text,
    fontSize: TYPOGRAPHY.body,
    fontWeight: 'bold',
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: SPACING.md,
  },
  button: {
    flex: 1,
    paddingVertical: SPACING.md,
    borderRadius: 8,
    marginHorizontal: SPACING.xs,
    alignItems: 'center',
  },
  cancelButton: {
    backgroundColor: COLORS.background,
  },
  submitButton: {
    backgroundColor: COLORS.success,
  },
  buttonText: {
    color: COLORS.text,
    fontSize: TYPOGRAPHY.body,
    fontWeight: 'bold',
  },
});
