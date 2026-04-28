export const COLORS = {
  // Backgrounds
  background: '#F5F5F0',
  backgroundElevated: '#FFFFFF',

  // Cards
  card: '#FFFFFF',
  cardElevated: '#FAFAFA',

  // Brand / accent
  primary: '#E8393A',       // Vivid red — hero card, active CTAs
  primaryDark: '#C42F30',   // Darker red for pressed states
  secondary: '#1A1A1A',     // Charcoal — inactive pills, nav icons

  // Text
  text: '#1A1A1A',
  textSecondary: '#6B6B6B',
  textOnPrimary: '#FFFFFF', // Text sitting on a red/dark background

  // Semantic
  success: '#2D6A4F',       // Dark green — winner card, Team B tag
  successLight: '#D1FAE5',  // Light green tint
  error: '#E8393A',         // Same red used for bust/error
  warning: '#F59E0B',       // Amber — stat highlights, XP numbers

  // Dart-specific
  bust: '#E8393A',
  bull: '#F59E0B',          // Amber bull highlight
  triple: '#E8393A',
  double: '#2D6A4F',

  // Team tags
  teamA: '#E8393A',
  teamB: '#2D6A4F',

  // UI chrome
  border: '#E5E5E5',
  separator: '#E5E5E5',
  inputBackground: '#F5F5F0',
  placeholder: '#B0B0B0',
  overlay: 'rgba(0, 0, 0, 0.6)',
} as const;

export type ColorTokens = typeof COLORS;
