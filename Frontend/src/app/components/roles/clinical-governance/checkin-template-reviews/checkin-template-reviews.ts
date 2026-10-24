import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { ClinicalCheckinTemplateReviewApi } from '../../../../api/navigator/admin-checkin-template.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { CheckinTemplateReview } from '../../../../shared/types/navigator/admin-checkin-template';
import { Breadcrumb, BreadcrumbItem } from '../../../../shared/ui/breadcrumb/breadcrumb';
import { CheckinTemplatePreview } from '../../system-admin/checkin-template/checkin-template-preview/checkin-template-preview';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-clinical-checkin-template-reviews',
  standalone: true,
  imports: [CommonModule, FormsModule, Breadcrumb, CheckinTemplatePreview],
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

  selectReview(review: CheckinTemplateReview): void {
    this.detailLoading.set(true);
    this.error.set(null);
    this.reviewNotes = '';
    this.api.get(this.userId(), review.review_id)
      .pipe(finalize(() => this.detailLoading.set(false)))
      .subscribe({
        next: (response) => this.selected.set(response.data),
        error: (error) => this.showError(this.errorMessage(error, 'Unable to load the review.')),
      });
  }

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
    this.api.list(this.userId()).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (response) => {
        this.reviews.set(response.data.reviews);
        if (!this.selected() && response.data.reviews.length) this.selectReview(response.data.reviews[0]);
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
