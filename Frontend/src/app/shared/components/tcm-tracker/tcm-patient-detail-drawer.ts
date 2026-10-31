import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

import { TcmPatientDetail } from '../../types/navigator/tcm-tracker';

@Component({
  selector: 'app-tcm-patient-detail-drawer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './tcm-patient-detail-drawer.html',
  styleUrl: './tcm-patient-detail-drawer.scss',
})
export class TcmPatientDetailDrawer {
  @Input() detail: TcmPatientDetail | null = null;
  @Input() loading = false;
  @Input() error = '';
  @Output() readonly closed = new EventEmitter<void>();

  label(value: string | null | undefined): string {
    return value ? value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) : 'Not available';
  }
}