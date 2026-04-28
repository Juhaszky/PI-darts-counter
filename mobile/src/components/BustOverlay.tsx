import React, { useEffect } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { useTheme } from '../themes/ThemeContext';
import type { Theme } from '../themes';

interface BustOverlayProps {
  visible: boolean;
  playerName: string;
}

export default function BustOverlay({ visible, playerName }: BustOverlayProps) {
  const { colors, typography } = useTheme();
  const opacity = React.useRef(new Animated.Value(0)).current;
  const scale = React.useRef(new Animated.Value(0.5)).current;

  useEffect(() => {
    if (visible) {
      Animated.parallel([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.spring(scale, {
          toValue: 1,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(opacity, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.timing(scale, {
          toValue: 0.5,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [visible, opacity, scale]);

  if (!visible) return null;

  const styles = createStyles(colors, typography);

  return (
    <View style={styles.container}>
      <Animated.View style={[styles.content, { opacity, transform: [{ scale }] }]}>
        <Text style={styles.bustText}>BUST!</Text>
        <Text style={styles.playerText}>{playerName}</Text>
      </Animated.View>
    </View>
  );
}

function createStyles(
  colors: Theme['colors'],
  typography: Theme['typography'],
) {
  return StyleSheet.create({
    container: {
      ...StyleSheet.absoluteFillObject,
      backgroundColor: 'rgba(0, 0, 0, 0.65)',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000,
    },
    content: {
      backgroundColor: colors.bust,
      borderRadius: 24,
      paddingVertical: 40,
      paddingHorizontal: 56,
      alignItems: 'center',
    },
    bustText: {
      fontSize: 52,
      fontWeight: '900',
      color: '#FFFFFF',
      marginBottom: 8,
      letterSpacing: 2,
    },
    playerText: {
      fontSize: typography.h3,
      color: 'rgba(255,255,255,0.85)',
      fontWeight: '600',
    },
  });
}
