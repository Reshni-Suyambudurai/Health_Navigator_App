import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-refresh-button',
  standalone: true,
  template: `
    <button
      type="button"
      class="ui-refresh-button"
      [attr.title]="label"
      [attr.aria-label]="label"
      [disabled]="disabled"
      (click)="refresh.emit()"
    >
      <span aria-hidden="true">&#8635;</span>
    </button>
  `,
})
export class RefreshButton {
  @Input() label = 'Refresh';
  @Input() disabled = false;
  @Output() readonly refresh = new EventEmitter<void>();
}
