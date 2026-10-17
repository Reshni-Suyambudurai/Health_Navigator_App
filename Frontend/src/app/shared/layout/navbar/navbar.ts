import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { getThemeMode } from '../../../api/tokenstore';
import { initializeThemeMode, toggleThemeMode } from '../../utils/theme';

@Component({
  selector: 'app-role-navbar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './navbar.html',
  styleUrl: './navbar.scss',
})
export class RoleNavbar {
  readonly theme = signal<'light' | 'dark'>(getThemeMode());

  constructor() {
    this.theme.set(initializeThemeMode());
  }

  toggleTheme(): void {
    this.theme.set(toggleThemeMode());
  }
}
