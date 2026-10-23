import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

interface AdminArea {
  title: string;
  description: string;
  status: string;
}

@Component({
  selector: 'app-system-admin-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './system-admin-dashboard.html',
  styleUrl: './system-admin-dashboard.scss',
})
export class SystemAdminDashboard {
  readonly adminAreas: AdminArea[] = [
    { title: 'Users and roles', description: 'Accounts, role assignments, and access state', status: 'Access' },
    { title: 'Organizations', description: 'Care organizations and operational status', status: 'Directory' },
    { title: 'Audit trail', description: 'Security and administrative activity records', status: 'Compliance' },
    { title: 'System configuration', description: 'Application settings and reference values', status: 'Platform' },
    { title: 'Integration health', description: 'Navigator and PatientFHIR connectivity', status: 'Integrations' },
    { title: 'Data governance', description: 'Consent, retention, and access controls', status: 'Governance' },
  ];
}