import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { getThemeMode } from '../../../api/tokenstore';
import { initializeThemeMode, toggleThemeMode } from '../../utils/theme';
import { NotificationState } from '../../state/notification-state';

@Component({
  selector: 'app-role-navbar',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './navbar.html',
  styleUrl: './navbar.scss',
})
export class RoleNavbar {
  readonly notifications = inject(NotificationState);
  readonly theme = signal<'light' | 'dark'>(getThemeMode());

  constructor() {
    this.theme.set(initializeThemeMode());
  }

  toggleTheme(): void {
    this.theme.set(toggleThemeMode());
  }

  label(value: string): string {
    return value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }
}
