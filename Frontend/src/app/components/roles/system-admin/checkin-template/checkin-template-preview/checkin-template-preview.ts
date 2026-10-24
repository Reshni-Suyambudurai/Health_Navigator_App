import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdminCheckinTemplate } from '../../../../../shared/types/navigator/admin-checkin-template';

@Component({
  selector: 'app-checkin-template-preview',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './checkin-template-preview.html',
  styleUrl: './checkin-template-preview.scss',
})
export class CheckinTemplatePreview {
  @Input({ required: true }) template!: AdminCheckinTemplate;

  label(value: string): string {
    return value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
  }
}