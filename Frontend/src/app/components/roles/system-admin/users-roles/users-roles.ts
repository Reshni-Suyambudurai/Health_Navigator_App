import { CommonModule } from '@angular/common';
import { Component, HostListener, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { AdminUserApi } from '../../../../api/navigator/admin-user.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  AdminRoleName,
  AdminRoleOption,
  AdminUserCreateRequest,
  AdminUserRecord,
  AdminUserStatus,
  AdminUserUpdateRequest,
} from '../../../../shared/types/navigator/admin-user';
import { Breadcrumb, BreadcrumbItem } from '../../../../shared/ui/breadcrumb/breadcrumb';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

interface UserDraft {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  password: string;
  role_name: AdminRoleName;
}

interface StatusChange {
  user: AdminUserRecord;
  status: AdminUserStatus;
}

@Component({
  selector: 'app-system-admin-users-roles',
  standalone: true,
  imports: [CommonModule, FormsModule, Breadcrumb],
  templateUrl: './users-roles.html',
  styleUrl: './users-roles.scss',
})
export class SystemAdminUsersRoles implements OnInit {
  private readonly api = inject(AdminUserApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();
  private readonly pageSize = 15;

  readonly users = signal<AdminUserRecord[]>([]);
  readonly roles = signal<AdminRoleOption[]>([]);
  readonly total = signal(0);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly dialogMode = signal<'create' | 'edit' | null>(null);
  readonly selectedUser = signal<AdminUserRecord | null>(null);
  readonly pendingStatus = signal<StatusChange | null>(null);
  readonly openColumnFilter = signal<'role' | 'status' | null>(null);
  readonly selectedRoles = signal<AdminRoleName[]>([]);
  readonly selectedStatuses = signal<AdminUserStatus[]>([]);
  readonly pendingRoles = signal<AdminRoleName[]>([]);
  readonly pendingStatuses = signal<AdminUserStatus[]>([]);
  readonly distinctRoles = computed(() => [...new Set(this.users().map((user) => user.role_name))].sort());
  readonly distinctStatuses = computed(() => [...new Set(this.users().map((user) => user.status))].sort());
  readonly displayedUsers = computed(() => {
    const roles = this.selectedRoles();
    const statuses = this.selectedStatuses();
    return this.users().filter((user) =>
      (!roles.length || roles.includes(user.role_name))
      && (!statuses.length || statuses.includes(user.status)),
    );
  });
  readonly statuses: AdminUserStatus[] = ['ACTIVE', 'INACTIVE', 'SUSPENDED'];
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: 'System administration', route: '/system-admin/dashboard' },
    { label: 'Users & roles' },
  ];

  search = '';
  roleFilter: AdminRoleName | '' = '';
  statusFilter: AdminUserStatus | '' = '';
  page = 0;
  draft: UserDraft = this.emptyDraft();

  ngOnInit(): void {
    this.loadRoles();
    this.loadUsers();
  }

  refresh(): void {
    this.loadRoles();
    this.loadUsers();
  }

  @HostListener('document:click')
  closeColumnFilter(): void {
    this.openColumnFilter.set(null);
  }

  @HostListener('document:keydown.escape')
  closeColumnFilterOnEscape(): void {
    this.openColumnFilter.set(null);
  }

  toggleColumnFilter(filter: 'role' | 'status', event: Event): void {
    event.stopPropagation();
    const next = this.openColumnFilter() === filter ? null : filter;
    if (next === 'role') this.pendingRoles.set([...this.selectedRoles()]);
    if (next === 'status') this.pendingStatuses.set([...this.selectedStatuses()]);
    this.openColumnFilter.set(next);
  }

  toggleRoleOption(role: AdminRoleName): void {
    this.pendingRoles.update((selected) =>
      selected.includes(role) ? selected.filter((item) => item !== role) : [...selected, role],
    );
  }

  toggleStatusOption(status: AdminUserStatus): void {
    this.pendingStatuses.update((selected) =>
      selected.includes(status) ? selected.filter((item) => item !== status) : [...selected, status],
    );
  }

  selectAllRoles(): void {
    this.pendingRoles.set([...this.distinctRoles()]);
  }

  selectAllStatuses(): void {
    this.pendingStatuses.set([...this.distinctStatuses()]);
  }

  clearPendingFilter(filter: 'role' | 'status'): void {
    if (filter === 'role') this.pendingRoles.set([]);
    else this.pendingStatuses.set([]);
  }

  applyColumnFilter(filter: 'role' | 'status'): void {
    if (filter === 'role') this.selectedRoles.set([...this.pendingRoles()]);
    else this.selectedStatuses.set([...this.pendingStatuses()]);
    this.openColumnFilter.set(null);
  }

  applyFilters(): void {
    this.page = 0;
    this.loadUsers();
  }

  resetFilters(): void {
    this.search = '';
    this.roleFilter = '';
    this.statusFilter = '';
    this.applyFilters();
  }

  previousPage(): void {
    if (this.page === 0) return;
    this.page -= 1;
    this.loadUsers();
  }

  nextPage(): void {
    if ((this.page + 1) * this.pageSize >= this.total()) return;
    this.page += 1;
    this.loadUsers();
  }

  openCreate(): void {
    this.selectedUser.set(null);
    this.draft = this.emptyDraft();
    this.error.set(null);
    this.dialogMode.set('create');
  }

  openEdit(user: AdminUserRecord): void {
    this.selectedUser.set(user);
    this.draft = {
      first_name: user.first_name,
      last_name: user.last_name,
      email: user.email,
      phone: user.phone ?? '',
      password: '',
      role_name: user.role_name,
    };
    this.error.set(null);
    this.dialogMode.set('edit');
  }

  closeDialog(): void {
    if (this.saving()) return;
    this.dialogMode.set(null);
    this.selectedUser.set(null);
    this.error.set(null);
  }

  saveUser(): void {
    const actorId = this.actorId();
    if (!actorId || !this.validDraft()) return;

    const base: AdminUserUpdateRequest = {
      first_name: this.draft.first_name.trim(),
      last_name: this.draft.last_name.trim(),
      email: this.draft.email.trim().toLowerCase(),
      phone: this.cleanOptional(this.draft.phone),
      role_name: this.draft.role_name,
    };
    const selected = this.selectedUser();
    const request = this.dialogMode() === 'create'
      ? this.api.create(actorId, { ...base, password: this.draft.password } as AdminUserCreateRequest)
      : this.api.update(actorId, selected!.user_id, base);

    this.saving.set(true);
    this.error.set(null);
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (response) => {
        this.toast.success(response.message);
        this.closeDialog();
        this.loadUsers();
      },
      error: (error: unknown) => this.showError(this.errorMessage(error, 'Unable to save the user account.')),
    });
  }

  requestStatus(user: AdminUserRecord, status: AdminUserStatus): void {
    if (status !== user.status) this.pendingStatus.set({ user, status });
  }

  cancelStatus(): void {
    if (!this.saving()) this.pendingStatus.set(null);
  }

  confirmStatus(): void {
    const actorId = this.actorId();
    const change = this.pendingStatus();
    if (!actorId || !change) return;
    this.saving.set(true);
    this.api.updateStatus(actorId, change.user.user_id, change.status)
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.toast.success(response.message);
          this.pendingStatus.set(null);
          this.loadUsers();
        },
        error: (error: unknown) => {
          this.pendingStatus.set(null);
          this.showError(this.errorMessage(error, 'Unable to update account status.'));
        },
      });
  }

  formatLabel(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  statusClass(status: AdminUserStatus): string {
    if (status === 'ACTIVE') return 'status-positive';
    return status === 'SUSPENDED' ? 'status-critical' : 'status-warning';
  }

  formatDate(value: string | null): string {
    return value ? new Date(value).toLocaleDateString([], { dateStyle: 'medium' }) : 'Not available';
  }

  get pageStart(): number {
    return this.total() ? this.page * this.pageSize + 1 : 0;
  }

  get pageEnd(): number {
    return Math.min((this.page + 1) * this.pageSize, this.total());
  }

  private loadUsers(): void {
    const actorId = this.actorId();
    if (!actorId) return this.showError('Your session has expired. Please sign in again.');
    this.loading.set(true);
    this.error.set(null);
    this.api.list(actorId, {
      skip: this.page * this.pageSize,
      limit: this.pageSize,
      search: this.search.trim(),
      role_name: this.roleFilter,
      user_status: this.statusFilter,
    }).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (response) => {
        this.users.set(response.data.users);
        this.total.set(response.data.count);
      },
      error: (error: unknown) => this.showError(this.errorMessage(error, 'Unable to load user accounts.')),
    });
  }

  private loadRoles(): void {
    const actorId = this.actorId();
    if (!actorId) return;
    this.api.listRoles(actorId).subscribe({
      next: (response) => {
        this.roles.set(response.data.roles);
        if (response.data.roles.length && !this.draft.role_name) {
          this.draft.role_name = response.data.roles[0].role_name;
        }
      },
      error: (error: unknown) => this.showError(this.errorMessage(error, 'Unable to load assignable roles.')),
    });
  }

  private validDraft(): boolean {
    if (!this.draft.first_name.trim() || !this.draft.last_name.trim()) {
      this.showError('First and last name are required.');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.draft.email.trim())) {
      this.showError('Enter a valid email address.');
      return false;
    }
    if (!this.draft.role_name) {
      this.showError('Select a role.');
      return false;
    }
    if (this.dialogMode() === 'create' && this.draft.password.length < 8) {
      this.showError('Temporary password must contain at least 8 characters.');
      return false;
    }
    return true;
  }

  private emptyDraft(): UserDraft {
    return {
      first_name: '',
      last_name: '',
      email: '',
      phone: '',
      password: 'Test@1234',
      role_name: 'CARE_MANAGER',
    };
  }

  private actorId(): number | null {
    return this.sessionUser?.user_id ?? this.sessionUser?.userId ?? null;
  }

  private cleanOptional(value: string): string | null {
    return value.trim() || null;
  }

  private showError(message: string): void {
    this.error.set(message);
    this.toast.error(message);
  }

  private errorMessage(error: unknown, fallback: string): string {
    return (error as { error?: { message?: string } })?.error?.message ?? fallback;
  }
}