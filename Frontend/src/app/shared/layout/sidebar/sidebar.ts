import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';

import { ROLE_SIDEBAR_CONFIG } from '../../../components/roles/role-nav';
import { clearSessionUser, getSessionUser, setThemeMode } from '../../../api/tokenstore';
import { getDashboardRouteForRole } from '../../utils/role-route';
import { initializeThemeMode } from '../../utils/theme';

@Component({
  selector: 'app-role-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
})
export class RoleSidebar {
  readonly showUserMenu = signal(false);
  readonly sessionUser = getSessionUser();
  readonly roleConfig = this.getRoleConfig();
  readonly topics = this.roleConfig.topics;
  readonly activeTopic = signal('Dashboard');
  readonly displayName = this.sessionUser?.username ?? 'Guest User';
  readonly displayRole = this.sessionUser?.roleName ? this.formatRoleName(this.sessionUser.roleName) : 'Viewer';
  readonly initials = this.getInitials(this.displayName);

  constructor(private readonly router: Router) {}

  toggleUserMenu(event: Event): void {
    event.stopPropagation();
    this.showUserMenu.set(!this.showUserMenu());
  }

  logout(): void {
    clearSessionUser();
    setThemeMode('light');
    initializeThemeMode();
    this.showUserMenu.set(false);
    this.router.navigate(['/login']);
  }

  selectTopic(label: string): void {
    this.activeTopic.set(label);
  }

  private getRoleConfig() {
    const fallback = ROLE_SIDEBAR_CONFIG.find((item) => item.route === '/clinical-governance/dashboard')!;

    if (!this.sessionUser) {
      return fallback;
    }

    const allowedRoute = getDashboardRouteForRole(this.sessionUser.roleId, this.sessionUser.roleName);
    return ROLE_SIDEBAR_CONFIG.find((item) => item.route === allowedRoute) ?? fallback;
  }

  private getInitials(name: string): string {
    const parts = name.trim().split(' ').filter(Boolean);
    if (parts.length === 0) {
      return 'GU';
    }

    const first = parts[0][0] ?? '';
    const last = parts.length > 1 ? parts[parts.length - 1][0] : '';
    return `${first}${last}`.toUpperCase();
  }

  private formatRoleName(roleName: string): string {
    return roleName
      .toLowerCase()
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }
}
