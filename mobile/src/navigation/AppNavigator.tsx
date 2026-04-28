import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { useTheme } from '../themes/ThemeContext';
import HomeScreen from '../screens/HomeScreen';
import SetupScreen from '../screens/SetupScreen';
import GameScreen from '../screens/GameScreen';
import StatsScreen from '../screens/StatsScreen';
import type { RootStackParamList } from './types';

const Stack = createStackNavigator<RootStackParamList>();

export default function AppNavigator() {
  const { colors, typography } = useTheme();

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerStyle: {
            backgroundColor: colors.card,
            shadowColor: colors.border,
            shadowOpacity: 1,
            elevation: 1,
          },
          headerTintColor: colors.text,
          headerTitleStyle: {
            fontWeight: 'bold',
            fontSize: typography.body,
            color: colors.text,
          },
          cardStyle: {
            backgroundColor: colors.background,
          },
        }}
      >
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="Setup"
          component={SetupScreen}
          options={{ title: 'New Game' }}
        />
        <Stack.Screen
          name="Game"
          component={GameScreen}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="Stats"
          component={StatsScreen}
          options={{ title: 'Match Stats' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
