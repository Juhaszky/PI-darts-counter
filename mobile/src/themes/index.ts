import { COLORS, type ColorTokens } from './colors';
import { SPACING, type SpacingTokens } from './spacing';
import { TYPOGRAPHY, type TypographyTokens } from './typography';
import { SHADOWS, type ShadowTokens } from './shadows';

export { COLORS, SPACING, TYPOGRAPHY, SHADOWS };
export type { ColorTokens, SpacingTokens, TypographyTokens, ShadowTokens };

export const theme = {
  colors: COLORS,
  spacing: SPACING,
  typography: TYPOGRAPHY,
  shadows: SHADOWS,
} as const;

export type Theme = typeof theme;
