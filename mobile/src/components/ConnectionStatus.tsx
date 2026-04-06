import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ConnectionStatus } from '../services/websocketService';
import { COLORS, SPACING, TYPOGRAPHY } from '../constants/theme';

interface ConnectionStatusProps {
  status: ConnectionStatus;
}

export default function ConnectionStatusIndicator({ status }: ConnectionStatusProps) {
  const getStatusColor = () => {
    switch (status) {
      case ConnectionStatus.CONNECTED:
        return COLORS.success;
      case ConnectionStatus.CONNECTING:
      case ConnectionStatus.RECONNECTING:
        return COLORS.warning;
      case ConnectionStatus.DISCONNECTED:
      case ConnectionStatus.ERROR:
        return COLORS.error;
      default:
        return COLORS.textSecondary;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case ConnectionStatus.CONNECTED:
        return 'Csatlakozva';
      case ConnectionStatus.CONNECTING:
        return 'Csatlakozás...';
      case ConnectionStatus.RECONNECTING:
        return 'Újracsatlakozás...';
      case ConnectionStatus.DISCONNECTED:
        return 'Nincs kapcsolat';
      case ConnectionStatus.ERROR:
        return 'Hiba';
      default:
        return 'Ismeretlen';
    }
  };

  return (
    <View style={styles.container}>
      <View style={[styles.indicator, { backgroundColor: getStatusColor() }]} />
      <Text style={styles.text}>{getStatusText()}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: SPACING.sm,
  },
  indicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: SPACING.sm,
  },
  text: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.text,
  },
});
