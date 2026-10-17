import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { RoleNavbar } from '../navbar/navbar';
import { RoleSidebar } from '../sidebar/sidebar';

@Component({
  selector: 'app-role-shell',
  standalone: true,
  imports: [RouterOutlet, RoleNavbar, RoleSidebar],
  templateUrl: './role-shell.html',
  styleUrl: './role-shell.scss',
})
export class RoleShell {}
