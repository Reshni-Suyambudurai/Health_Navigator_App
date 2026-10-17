import { Injectable, signal } from '@angular/core';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastMessage {
  id: number;
  type: ToastType;
  message: string;
  durationMs: number;
}

@Injectable({ providedIn: 'root' })
export class ToastState {
  readonly toasts = signal<ToastMessage[]>([]);

  success(message: string, durationMs = 3000): void {
    this.show('success', message, durationMs);
  }

  error(message: string, durationMs = 4000): void {
    this.show('error', message, durationMs);
  }

  info(message: string, durationMs = 3000): void {
    this.show('info', message, durationMs);
  }

  warning(message: string, durationMs = 3500): void {
    this.show('warning', message, durationMs);
  }

  remove(id: number): void {
    this.toasts.update((items) => items.filter((item) => item.id !== id));
  }

  private show(type: ToastType, message: string, durationMs: number): void {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    this.toasts.update((items) => [...items, { id, type, message, durationMs }]);

    window.setTimeout(() => {
      this.remove(id);
    }, durationMs);
  }
}
