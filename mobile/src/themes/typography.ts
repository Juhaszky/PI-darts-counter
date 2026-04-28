export const TYPOGRAPHY = {
  h1: 32,
  h2: 24,
  h3: 20,
  body: 16,
  small: 14,
  tiny: 12,
} as const;

export type TypographyTokens = typeof TYPOGRAPHY;
