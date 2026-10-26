import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { AdminAuditApi } from '../../../../api/navigator/admin-audit.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { AdminAuditAction, AdminAuditEntry } from '../../../../shared/types/navigator/audit-trail';
import { Breadcrumb, BreadcrumbItem } from '../../../../shared/ui/breadcrumb/breadcrumb';
import { Pagination } from '../../../../shared/ui/pagination/pagination';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-system-admin-audit-trail',
  standalone: true,
  imports: [CommonModule, FormsModule, Breadcrumb, Pagination],
  templateUrl: './audit-trail.html',
  styleUrl: './audit-trail.scss',
})
export class SystemAdminAuditTrail implements OnInit {
  private readonly api = inject(AdminAuditApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();
  private readonly pageSize = 20;

  readonly entries = signal<AdminAuditEntry[]>([]);
  readonly total = signal(0);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly expandedId = signal<number | null>(null);
  readonly actions: AdminAuditAction[] = ['CREATE_USER', 'UPDATE_USER', 'DISABLE_USER', 'ENABLE_USER'];
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: 'System administration', route: '/system-admin/dashboard' },
    { label: 'Audit trail' },
  ];

  actionFilter: AdminAuditAction | '' = '';
  page = 0;

  ngOnInit(): void {
    this.loadEntries();
  }

  applyFilter(): void {
    this.page = 0;
    this.loadEntries();
  }

  previousPage(): void {
    if (this.page === 0) return;
    this.page -= 1;
    this.loadEntries();
  }

  nextPage(): void {
    if ((this.page + 1) * this.pageSize >= this.total()) return;
    this.page += 1;
    this.loadEntries();
  }

  toggleDetails(auditId: number): void {
    this.expandedId.set(this.expandedId() === auditId ? null : auditId);
  }

  formatLabel(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  formatDate(value: string | null): string {
    return value ? new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Not available';
  }

  changedFields(entry: AdminAuditEntry): string {
    const fields = entry.details?.changed_fields ?? [];
    return fields.length ? fields.map((field) => this.formatLabel(field)).join(', ') : 'Account record';
  }

  detailPairs(values: Record<string, unknown> | null | undefined): { key: string; value: string }[] {
    if (!values) return [];
    return Object.entries(values).map(([key, value]) => ({
      key: this.formatLabel(key),
      value: value === null || value === '' ? 'Not provided' : String(value),
    }));
  }

  get pageStart(): number {
    return this.total() ? this.page * this.pageSize + 1 : 0;
  }

  get pageEnd(): number {
    return Math.min((this.page + 1) * this.pageSize, this.total());
  }

  private loadEntries(): void {
    const actorId = this.sessionUser?.user_id ?? this.sessionUser?.userId ?? null;
    if (!actorId) {
      this.showError('Your session has expired. Please sign in again.');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.api.list(actorId, this.page * this.pageSize, this.pageSize, this.actionFilter)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => {
          this.entries.set(response.data.entries);
          this.total.set(response.data.count);
        },
        error: (error: unknown) => this.showError(
          (error as { error?: { message?: string } })?.error?.message ?? 'Unable to load the audit trail.',
        ),
      });
  }

  private showError(message: string): void {
    this.error.set(message);
    this.toast.error(message);
  }
}