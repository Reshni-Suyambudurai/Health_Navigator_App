import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ToastState } from './toast-state';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './toast.html',
  styleUrl: './toast.scss',
})
export class Toast {
  protected readonly toastState = inject(ToastState);
}
