import { Injectable, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { NotificationApi } from '../../api/notification.api';
import { getSessionUser } from '../../api/tokenstore';
import { NotificationRecord } from '../types/notification';
import { ToastState } from '../ui/toast/toast-state';

@Injectable({ providedIn: 'root' })
export class NotificationState {
  private readonly api = inject(NotificationApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly notifications = signal<NotificationRecord[]>([]);
  readonly unreadCount = signal(0);
  readonly total = signal(0);
  readonly panelOpen = signal(false);
  readonly selected = signal<NotificationRecord | null>(null);
  readonly loading = signal(false);
  readonly refreshing = signal(false);
  readonly detailLoading = signal(false);
  readonly openingNotificationId = signal<number | null>(null);

  initialize(): void {
    if (this.userId()) this.refresh(false);
  }

  togglePanel(): void {
    const opening = !this.panelOpen();
    this.panelOpen.set(opening);
    if (!opening) this.selected.set(null);
  }

  closePanel(): void {
    this.panelOpen.set(false);
    this.selected.set(null);
  }

  showList(): void {
    this.selected.set(null);
  }

  refresh(showSpinner = true): void {
    const userId = this.userId();
    if (!userId || this.refreshing()) return;
    if (showSpinner) this.refreshing.set(true);
    else this.loading.set(true);
    this.api.list(userId)
      .pipe(finalize(() => {
        this.loading.set(false);
        this.refreshing.set(false);
      }))
      .subscribe({
        next: (response) => {
          this.notifications.set(response.data.notifications);
          this.total.set(response.data.count);
          this.unreadCount.set(response.data.unread_count);
          const selectedId = this.selected()?.notification_id;
          if (selectedId) {
            this.selected.set(response.data.notifications.find((item) => item.notification_id === selectedId) ?? null);
          }
        },
        error: () => this.toast.error('Unable to refresh notifications.'),
      });
  }

  openNotification(notification: NotificationRecord): void {
    const userId = this.userId();
    if (!userId || this.detailLoading()) return;
    this.detailLoading.set(true);
    this.openingNotificationId.set(notification.notification_id);
    const request = notification.status === 'UNREAD'
      ? this.api.markRead(userId, notification.notification_id)
      : this.api.get(userId, notification.notification_id);
    request.pipe(finalize(() => {
      this.detailLoading.set(false);
      this.openingNotificationId.set(null);
    })).subscribe({
      next: (response) => {
        const updated = response.data;
        this.selected.set(updated);
        this.notifications.update((items) =>
          items.map((item) => item.notification_id === updated.notification_id ? updated : item),
        );
        if (notification.status === 'UNREAD') {
          this.unreadCount.update((count) => Math.max(0, count - 1));
        }
      },
      error: () => this.toast.error('Unable to open the notification.'),
    });
  }

  isPatient(): boolean {
    return this.sessionUser?.roleName === 'PATIENT';
  }

  private userId(): number {
    return Number(this.sessionUser?.user_id ?? this.sessionUser?.userId ?? 0);
  }
}