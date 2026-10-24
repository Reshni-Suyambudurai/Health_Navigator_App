import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { OrganizationApi } from '../../../../api/navigator/organization.api';
import { getSessionUser } from '../../../../api/tokenstore';
import {
  OrganizationRecord,
  OrganizationStatus,
  OrganizationType,
  OrganizationUpdateRequest,
} from '../../../../shared/types/navigator/organization';
import { Breadcrumb, BreadcrumbItem } from '../../../../shared/ui/breadcrumb/breadcrumb';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-system-admin-organization',
  standalone: true,
  imports: [CommonModule, FormsModule, Breadcrumb],
  templateUrl: './organization.html',
  styleUrl: './organization.scss',
})
export class SystemAdminOrganization implements OnInit {
  private readonly api = inject(OrganizationApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly organization = signal<OrganizationRecord | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly editing = signal(false);
  readonly error = signal<string | null>(null);
  readonly organizationTypes: OrganizationType[] = [
    'HOSPITAL',
    'CLINIC',
    'HEALTHCARE_GROUP',
    'PHARMACY',
    'HEALTH_PLAN',
  ];
  readonly organizationStatuses: OrganizationStatus[] = ['ACTIVE', 'INACTIVE'];
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: 'System administration', route: '/system-admin/dashboard' },
    { label: 'Organizations' },
  ];

  draft: OrganizationUpdateRequest = this.emptyDraft();

  ngOnInit(): void {
    this.loadOrganization();
  }

  beginEdit(): void {
    const organization = this.organization();
    if (!organization) return;
    this.draft = this.toDraft(organization);
    this.error.set(null);
    this.editing.set(true);
  }

  cancelEdit(): void {
    const organization = this.organization();
    if (organization) this.draft = this.toDraft(organization);
    this.error.set(null);
    this.editing.set(false);
  }

  saveOrganization(): void {
    const userId = this.userId();
    if (!userId) {
      this.showError('Your session has expired. Please sign in again.');
      return;
    }
    if (!this.validDraft()) return;

    const payload: OrganizationUpdateRequest = {
      ...this.draft,
      organization_name: this.draft.organization_name.trim(),
      npi_number: this.cleanOptional(this.draft.npi_number),
      address: this.cleanOptional(this.draft.address),
      phone: this.cleanOptional(this.draft.phone),
      contact_first_name: this.draft.contact_first_name.trim(),
      contact_last_name: this.draft.contact_last_name.trim(),
      contact_email: this.draft.contact_email.trim().toLowerCase(),
      contact_phone: this.cleanOptional(this.draft.contact_phone),
    };

    this.saving.set(true);
    this.error.set(null);
    this.api.updateCurrent(userId, payload)
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: (response) => {
          this.organization.set(response.data);
          this.draft = this.toDraft(response.data);
          this.editing.set(false);
          this.toast.success(response.message);
        },
        error: (error: unknown) => this.showError(this.errorMessage(error, 'Unable to save organization details.')),
      });
  }

  formatLabel(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  formatDate(value: string | null): string {
    return value ? new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Not available';
  }

  private loadOrganization(): void {
    const userId = this.userId();
    if (!userId) {
      this.showError('Your session has expired. Please sign in again.');
      return;
    }

    this.loading.set(true);
    this.error.set(null);
    this.api.getCurrent(userId)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => {
          this.organization.set(response.data);
          this.draft = this.toDraft(response.data);
        },
        error: (error: unknown) => this.showError(this.errorMessage(error, 'Unable to load organization details.')),
      });
  }

  private validDraft(): boolean {
    if (!this.draft.organization_name.trim()) {
      this.showError('Organization name is required.');
      return false;
    }
    if (!this.draft.contact_first_name.trim() || !this.draft.contact_last_name.trim()) {
      this.showError('Contact first and last name are required.');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.draft.contact_email.trim())) {
      this.showError('Enter a valid contact email address.');
      return false;
    }
    return true;
  }

  private toDraft(organization: OrganizationRecord): OrganizationUpdateRequest {
    return {
      organization_name: organization.organization_name,
      organization_type: organization.organization_type,
      npi_number: organization.npi_number,
      address: organization.address,
      phone: organization.phone,
      status: organization.status,
      contact_first_name: organization.contact.first_name,
      contact_last_name: organization.contact.last_name,
      contact_email: organization.contact.email,
      contact_phone: organization.contact.phone,
    };
  }

  private emptyDraft(): OrganizationUpdateRequest {
    return {
      organization_name: '',
      organization_type: 'HOSPITAL',
      npi_number: null,
      address: null,
      phone: null,
      status: 'ACTIVE',
      contact_first_name: '',
      contact_last_name: '',
      contact_email: '',
      contact_phone: null,
    };
  }

  private userId(): number | null {
    return this.sessionUser?.user_id ?? this.sessionUser?.userId ?? null;
  }

  private cleanOptional(value: string | null): string | null {
    const cleaned = value?.trim();
    return cleaned || null;
  }

  private showError(message: string): void {
    this.error.set(message);
    this.toast.error(message);
  }

  private errorMessage(error: unknown, fallback: string): string {
    return (error as { error?: { message?: string } })?.error?.message ?? fallback;
  }
}