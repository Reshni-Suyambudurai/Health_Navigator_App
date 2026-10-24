import { Component, OnInit, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { RoleNavbar } from '../navbar/navbar';
import { RoleSidebar } from '../sidebar/sidebar';
import { NotificationState } from '../../state/notification-state';

@Component({
  selector: 'app-role-shell',
  standalone: true,
  imports: [RouterOutlet, RoleNavbar, RoleSidebar],
  templateUrl: './role-shell.html',
  styleUrl: './role-shell.scss',
})
export class RoleShell implements OnInit {
  private readonly notifications = inject(NotificationState);

  ngOnInit(): void {
    this.notifications.initialize();
  }
}
