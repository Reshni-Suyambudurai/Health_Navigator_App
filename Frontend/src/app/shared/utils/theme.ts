import { getThemeMode, setThemeMode } from '../../api/tokenstore';
import { ThemeMode } from '../types/session';

export function applyThemeMode(mode: ThemeMode): void {
  if (typeof document === 'undefined') {
    return;
  }

  document.documentElement.setAttribute('data-theme', mode);
}

export function initializeThemeMode(): ThemeMode {
  const mode = getThemeMode();
  setThemeMode(mode);
  applyThemeMode(mode);
  return mode;
}

export function toggleThemeMode(): ThemeMode {
  const nextMode: ThemeMode = getThemeMode() === 'light' ? 'dark' : 'light';
  setThemeMode(nextMode);
  applyThemeMode(nextMode);
  return nextMode;
}
