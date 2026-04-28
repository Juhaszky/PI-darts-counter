import React, { createContext, useContext, type ReactNode } from 'react';
import { theme, type Theme } from './index';

const ThemeContext = createContext<Theme>(theme);

interface ThemeProviderProps {
  children: ReactNode;
  value?: Theme;
}

export function ThemeProvider({ children, value = theme }: ThemeProviderProps) {
  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): Theme {
  return useContext(ThemeContext);
}
