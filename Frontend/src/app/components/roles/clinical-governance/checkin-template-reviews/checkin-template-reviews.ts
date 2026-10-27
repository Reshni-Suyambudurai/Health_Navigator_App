import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { heroArrowPath, heroCheckCircle, heroClipboardDocumentList, heroClock, heroXCircle } from '@ng-icons/heroicons/outline';
import { finalize } from 'rxjs';
import { ClinicalCheckinTemplateReviewApi } from '../../../../api/navigator/admin-checkin-template.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { CheckinTemplateReview, ReviewOrganizationOption } from '../../../../shared/types/navigator/admin-checkin-template';
import { Breadcrumb, BreadcrumbItem } from '../../../../shared/ui/breadcrumb/breadcrumb';
import { CheckinTemplatePreview } from '../../system-admin/checkin-template/checkin-template-preview/checkin-template-preview';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-clinical-checkin-template-reviews',
  standalone: true,
  imports: [CommonModule, FormsModule, Breadcrumb, CheckinTemplatePreview, NgIcon],
  providers: [provideIcons({ heroArrowPath, heroCheckCircle, heroClipboardDocumentList, heroClock, heroXCircle })],
  templateUrl: './checkin-template-reviews.html',
  styleUrl: './checkin-template-reviews.scss',
})
export class ClinicalCheckinTemplateReviews implements OnInit {
  private readonly api = inject(ClinicalCheckinTemplateReviewApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly reviews = signal<CheckinTemplateReview[]>([]);
  readonly selected = signal<CheckinTemplateReview | null>(null);
  readonly loading = signal(false);
  readonly detailLoading = signal(false);
  readonly deciding = signal(false);
  readonly error = signal<string | null>(null);
  readonly viewMode = signal<'PENDING' | 'HISTORY'>('PENDING');
  readonly organizations = signal<ReviewOrganizationOption[]>([]);
  readonly selectedOrganizationId = signal<number | null>(null);
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: 'Clinical governance', route: '/clinical-governance/dashboard' },
    { label: 'Check-in template reviews' },
  ];

  reviewNotes = '';

  ngOnInit(): void {
    this.loadReviews();
  }

  refresh(): void {
    this.loadReviews();
  }

  changeOrganization(organizationId: number | string): void {
    this.selectedOrganizationId.set(Number(organizationId));
    this.selected.set(null);
    this.loadReviews();
  }

  selectReview(review: CheckinTemplateReview): void {
    this.error.set(null);
    this.reviewNotes = '';
    this.selected.set(review);
  }

  selectView(mode: 'PENDING' | 'HISTORY'): void {
    this.viewMode.set(mode);
    this.selected.set(this.visibleReviews[0] ?? null);
    this.reviewNotes = '';
  }

  get visibleReviews(): CheckinTemplateReview[] {
    return this.reviews().filter((review) => modeMatches(review.status, this.viewMode()));
  }

  get pendingCount(): number { return this.reviews().filter((review) => review.status === 'PENDING').length; }
  get historyCount(): number { return this.reviews().filter((review) => review.status !== 'PENDING').length; }

  decide(decision: 'APPROVED' | 'REJECTED'): void {
    const review = this.selected();
    const notes = this.reviewNotes.trim();
    if (!review || !notes) {
      this.showError('Clinical review notes are required.');
      return;
    }
    this.deciding.set(true);
    this.api.decide(this.userId(), review.review_id, decision, notes)
      .pipe(finalize(() => this.deciding.set(false)))
      .subscribe({
        next: (response) => {
          this.toast.success(response.message);
          this.selected.set(null);
          this.reviewNotes = '';
          this.loadReviews();
        },
        error: (error) => this.showError(this.errorMessage(error, 'Unable to record the review decision.')),
      });
  }

  label(value: string): string {
    return value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  private loadReviews(): void {
    this.loading.set(true);
    this.api.list(this.userId(), 'ALL', this.selectedOrganizationId()).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (response) => {
        this.reviews.set(response.data.reviews);
        this.organizations.set(response.data.organizations);
        this.selectedOrganizationId.set(response.data.selected_organization_id);
        const selectedStillVisible = this.visibleReviews.some((review) => review.review_id === this.selected()?.review_id);
        if (!selectedStillVisible) this.selected.set(this.visibleReviews[0] ?? null);
      },
      error: (error) => this.showError(this.errorMessage(error, 'Unable to load pending reviews.')),
    });
  }

  private userId(): number {
    return Number(this.sessionUser?.user_id ?? this.sessionUser?.userId ?? 0);
  }

  private showError(message: string): void {
    this.error.set(message);
    this.toast.error(message);
  }

  private errorMessage(error: unknown, fallback: string): string {
    return (error as { error?: { message?: string } })?.error?.message ?? fallback;
  }
}

function modeMatches(status: CheckinTemplateReview['status'], mode: 'PENDING' | 'HISTORY'): boolean {
  return mode === 'PENDING' ? status === 'PENDING' : status !== 'PENDING';
}
