import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-pagination',
  standalone: true,
  template: `
    <nav class="ui-pagination" [attr.aria-label]="ariaLabel">
      <span class="ui-pagination__range">{{ start }}-{{ end }} of {{ total }}</span>
      <div class="ui-pagination__actions">
        <button
          type="button"
          class="secondary-button"
          (click)="previous.emit()"
          [disabled]="previousDisabled || disabled"
        >
          Previous
        </button>
        <button
          type="button"
          class="secondary-button"
          (click)="next.emit()"
          [disabled]="nextDisabled || disabled"
        >
          Next
        </button>
      </div>
    </nav>
  `,
})
export class Pagination {
  @Input() start = 0;
  @Input() end = 0;
  @Input() total = 0;
  @Input() ariaLabel = 'Pages';
  @Input() previousDisabled = false;
  @Input() nextDisabled = false;
  @Input() disabled = false;
  @Output() readonly previous = new EventEmitter<void>();
  @Output() readonly next = new EventEmitter<void>();
}
