import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { useTheme } from '../themes/ThemeContext';
import type { Theme } from '../themes';
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
  const { colors, spacing, typography, shadows } = useTheme();

  useEffect(() => {
    loadStoredConnection();

    const unsubscribe = wsService.onStatusChange((status) => {
      setConnectionStatus(status);
    });

    return unsubscribe;
  }, []);

  const handleConnect = async () => {
    if (!host.trim() || !port.trim()) {
      Alert.alert('Missing details', 'Please enter the IP address and port.');
      return;
    }

    setIsLoading(true);

    try {
      apiService.initialize(host, port);
      await apiService.getHealth();
      await saveConnection();
      navigation.navigate('Setup', { gameId: '' });
    } catch (error) {
      console.error('Connection failed:', error);
      Alert.alert(
        'Connection failed',
        'Could not reach the server. Check the IP address and port.',
      );
    } finally {
      setIsLoading(false);
    }
  };

  const styles = createStyles(colors, spacing, typography, shadows);

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* Hero card */}
          <View style={styles.heroCard}>
            <View style={styles.heroTopRow}>
              <View style={styles.heroDotBadge} />
              <Text style={styles.heroBadgeText}>PI Darts Counter</Text>
            </View>
            <Text style={styles.heroHeadline}>Throw{'\n'}some darts.</Text>
            <TouchableOpacity
              style={[styles.heroButton, isLoading && styles.heroButtonDisabled]}
              onPress={handleConnect}
              disabled={isLoading}
              activeOpacity={0.85}
            >
              {isLoading ? (
                <ActivityIndicator color={colors.primary} size="small" />
              ) : (
                <>
                  <View style={styles.heroButtonDot} />
                  <Text style={styles.heroButtonText}>Start game</Text>
                </>
              )}
            </TouchableOpacity>
          </View>

          {/* Connection config card */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Raspberry Pi Connection</Text>

            <Text style={styles.label}>IP Address</Text>
            <TextInput
              style={styles.input}
              value={host}
              onChangeText={setHost}
              placeholder="192.168.1.5"
              placeholderTextColor={colors.placeholder}
              keyboardType="numeric"
              autoCapitalize="none"
            />

            <Text style={styles.label}>Port</Text>
            <TextInput
              style={styles.input}
              value={port}
              onChangeText={setPort}
              placeholder="8000"
              placeholderTextColor={colors.placeholder}
              keyboardType="numeric"
            />

            <View style={styles.statusRow}>
              <ConnectionStatusIndicator status={connectionStatus} />
            </View>
          </View>

          <Text style={styles.footer}>v1.0 • React Native + FastAPI</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function createStyles(
  colors: Theme['colors'],
  spacing: Theme['spacing'],
  typography: Theme['typography'],
  shadows: Theme['shadows'],
) {
  return StyleSheet.create({
    safeArea: {
      flex: 1,
      backgroundColor: colors.background,
    },
    keyboardView: {
      flex: 1,
    },
    scroll: {
      flex: 1,
    },
    scrollContent: {
      padding: spacing.lg,
      paddingBottom: spacing.xxl,
    },
    // Hero card
    heroCard: {
      backgroundColor: colors.primary,
      borderRadius: 16,
      padding: spacing.xl,
      marginBottom: spacing.lg,
      ...shadows.large,
    },
    heroTopRow: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: spacing.lg,
    },
    heroDotBadge: {
      width: 10,
      height: 10,
      borderRadius: 5,
      backgroundColor: colors.textOnPrimary,
      marginRight: spacing.sm,
      opacity: 0.9,
    },
    heroBadgeText: {
      fontSize: typography.small,
      color: colors.textOnPrimary,
      opacity: 0.9,
      fontWeight: '600',
      letterSpacing: 0.5,
    },
    heroHeadline: {
      fontSize: 40,
      fontWeight: '800',
      color: colors.textOnPrimary,
      lineHeight: 46,
      marginBottom: spacing.xl,
    },
    heroButton: {
      backgroundColor: colors.textOnPrimary,
      borderRadius: 12,
      paddingVertical: spacing.md,
      paddingHorizontal: spacing.lg,
      flexDirection: 'row',
      alignItems: 'center',
      alignSelf: 'flex-start',
    },
    heroButtonDisabled: {
      opacity: 0.7,
    },
    heroButtonDot: {
      width: 8,
      height: 8,
      borderRadius: 4,
      backgroundColor: colors.primary,
      marginRight: spacing.sm,
    },
    heroButtonText: {
      fontSize: typography.body,
      fontWeight: '700',
      color: colors.primary,
    },
    // Config card
    card: {
      backgroundColor: colors.card,
      borderRadius: 16,
      padding: spacing.lg,
      marginBottom: spacing.lg,
      ...shadows.medium,
    },
    cardTitle: {
      fontSize: typography.h3,
      fontWeight: '700',
      color: colors.text,
      marginBottom: spacing.lg,
    },
    label: {
      fontSize: typography.small,
      color: colors.textSecondary,
      fontWeight: '600',
      marginBottom: spacing.xs,
      marginTop: spacing.md,
      textTransform: 'uppercase',
      letterSpacing: 0.5,
    },
    input: {
      backgroundColor: colors.inputBackground,
      borderRadius: 10,
      borderWidth: 1,
      borderColor: colors.border,
      paddingHorizontal: spacing.md,
      paddingVertical: spacing.md,
      fontSize: typography.body,
      color: colors.text,
    },
    statusRow: {
      marginTop: spacing.md,
      paddingTop: spacing.md,
      borderTopWidth: 1,
      borderTopColor: colors.border,
    },
    footer: {
      fontSize: typography.tiny,
      color: colors.placeholder,
      textAlign: 'center',
      marginTop: spacing.sm,
    },
  });
}
