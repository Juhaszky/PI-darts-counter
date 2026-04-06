import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { COLORS, SPACING, TYPOGRAPHY, SHADOWS } from '../constants/theme';
import { useConnectionStore } from '../store/connectionStore';
import { apiService } from '../services/apiService';
import { wsService, ConnectionStatus } from '../services/websocketService';
import ConnectionStatusIndicator from '../components/ConnectionStatus';
import type { RootStackParamList } from '../navigation/types';

type HomeScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Home'>;

export default function HomeScreen() {
  const navigation = useNavigation<HomeScreenNavigationProp>();
  const { host, port, setHost, setPort, setGameId, loadStoredConnection, saveConnection } =
    useConnectionStore();
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState(ConnectionStatus.DISCONNECTED);

  useEffect(() => {
    loadStoredConnection();

    const unsubscribe = wsService.onStatusChange((status) => {
      setConnectionStatus(status);
    });

    return unsubscribe;
  }, []);

  const handleConnect = async () => {
    if (!host.trim() || !port.trim()) {
      Alert.alert('Hiba', 'Kérlek add meg az IP címet és a portot!');
      return;
    }

    setIsLoading(true);

    try {
      // Initialize API service
      apiService.initialize(host, port);

      // Test connection
      await apiService.getHealth();

      // Save connection
      await saveConnection();

      // Navigate to setup
      navigation.navigate('Setup', { gameId: '' });
    } catch (error) {
      console.error('Connection failed:', error);
      Alert.alert('Kapcsolódási hiba', 'Nem sikerült csatlakozni a szerverhez. Ellenőrizd az IP címet és a portot!');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>🎯 Darts Counter</Text>

      <View style={styles.card}>
        <Text style={styles.label}>Raspberry Pi IP címe</Text>
        <TextInput
          style={styles.input}
          value={host}
          onChangeText={setHost}
          placeholder="192.168.1.5"
          placeholderTextColor={COLORS.textSecondary}
          keyboardType="numeric"
          autoCapitalize="none"
        />

        <Text style={styles.label}>Port</Text>
        <TextInput
          style={styles.input}
          value={port}
          onChangeText={setPort}
          placeholder="8000"
          placeholderTextColor={COLORS.textSecondary}
          keyboardType="numeric"
        />

        <TouchableOpacity
          style={[styles.button, isLoading && styles.buttonDisabled]}
          onPress={handleConnect}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color={COLORS.text} />
          ) : (
            <Text style={styles.buttonText}>Csatlakozás</Text>
          )}
        </TouchableOpacity>
      </View>

      <ConnectionStatusIndicator status={connectionStatus} />

      <View style={styles.footer}>
        <Text style={styles.footerText}>v1.0 • React Native + FastAPI</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
    padding: SPACING.lg,
    justifyContent: 'center',
  },
  title: {
    fontSize: TYPOGRAPHY.h1,
    fontWeight: 'bold',
    color: COLORS.text,
    textAlign: 'center',
    marginBottom: SPACING.xxl,
  },
  card: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: SPACING.lg,
    ...SHADOWS.medium,
  },
  label: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textSecondary,
    marginBottom: SPACING.sm,
    marginTop: SPACING.md,
  },
  input: {
    backgroundColor: COLORS.background,
    borderRadius: 8,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.md,
    fontSize: TYPOGRAPHY.body,
    color: COLORS.text,
  },
  button: {
    backgroundColor: COLORS.primary,
    borderRadius: 8,
    paddingVertical: SPACING.md,
    alignItems: 'center',
    marginTop: SPACING.lg,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: COLORS.text,
    fontSize: TYPOGRAPHY.body,
    fontWeight: 'bold',
  },
  footer: {
    position: 'absolute',
    bottom: SPACING.lg,
    alignSelf: 'center',
  },
  footerText: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textSecondary,
  },
});
