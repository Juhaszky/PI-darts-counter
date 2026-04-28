import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ConnectionStatus } from '../services/websocketService';
import { useTheme } from '../themes/ThemeContext';
import type { Theme } from '../themes';

interface ConnectionStatusProps {
  status: ConnectionStatus;
}

export default function ConnectionStatusIndicator({ status }: ConnectionStatusProps) {
  const { colors, spacing, typography } = useTheme();

  const getStatusColor = (): string => {
    switch (status) {
      case ConnectionStatus.CONNECTED:
        return colors.success;
      case ConnectionStatus.CONNECTING:
      case ConnectionStatus.RECONNECTING:
        return colors.warning;
      case ConnectionStatus.DISCONNECTED:
      case ConnectionStatus.ERROR:
        return colors.error;
      default:
        return colors.placeholder;
    }
  };

  const getStatusText = (): string => {
    switch (status) {
      case ConnectionStatus.CONNECTED:
        return 'Connected';
      case ConnectionStatus.CONNECTING:
        return 'Connecting...';
      case ConnectionStatus.RECONNECTING:
        return 'Reconnecting...';
      case ConnectionStatus.DISCONNECTED:
        return 'Disconnected';
      case ConnectionStatus.ERROR:
        return 'Connection error';
      default:
        return 'Unknown';
    }
  };

  const styles = createStyles(colors, spacing, typography);
  const statusColor = getStatusColor();

  return (
    <View style={styles.container}>
      <View style={[styles.indicator, { backgroundColor: statusColor }]} />
      <Text style={[styles.text, { color: statusColor }]}>{getStatusText()}</Text>
    </View>
  );
}

function createStyles(
  colors: Theme['colors'],
  spacing: Theme['spacing'],
  typography: Theme['typography'],
) {
  return StyleSheet.create({
    container: {
      flexDirection: 'row',
      alignItems: 'center',
    },
    indicator: {
      width: 8,
      height: 8,
      borderRadius: 4,
      marginRight: spacing.sm,
    },
    text: {
      fontSize: typography.small,
      fontWeight: '600',
    },
  });
}
