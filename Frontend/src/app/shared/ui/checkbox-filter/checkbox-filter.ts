import { CommonModule } from '@angular/common';
import { Component, ElementRef, EventEmitter, HostListener, Input, Output, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

export interface CheckboxFilterOption {
  value: string;
  label: string;
  description?: string;
}

export interface CheckboxFilterGroup {
  label: string;
  options: CheckboxFilterOption[];
}

@Component({
  selector: 'app-checkbox-filter',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './checkbox-filter.html',
  styleUrl: './checkbox-filter.scss',
})
export class CheckboxFilter {
  @Input({ required: true }) label = 'Filter';
  @Input() groups: CheckboxFilterGroup[] = [];
  @Input() selectedValues: string[] = [];
  @Input() searchable = true;
  @Output() readonly selectedValuesChange = new EventEmitter<string[]>();

  private readonly element = inject(ElementRef<HTMLElement>);
  readonly draft = new Set<string>();
  open = false;
  search = '';
  panelLeft = 0;
  panelTop = 0;

  get filteredGroups(): CheckboxFilterGroup[] {
    const query = this.search.trim().toLocaleLowerCase();
    if (!query) return this.groups;
    return this.groups
      .map((group) => ({
        ...group,
        options: group.options.filter((option) =>
          `${option.label} ${option.description ?? ''}`.toLocaleLowerCase().includes(query),
        ),
      }))
      .filter((group) => group.options.length > 0);
  }

  get visibleOptions(): CheckboxFilterOption[] {
    return this.filteredGroups.flatMap((group) => group.options);
  }

  get allVisibleSelected(): boolean {
    return this.visibleOptions.length > 0
      && this.visibleOptions.every((option) => this.draft.has(option.value));
  }

  togglePopup(): void {
    if (this.open) {
      this.cancel();
      return;
    }
    this.draft.clear();
    this.selectedValues.forEach((value) => this.draft.add(value));
    this.search = '';
    const bounds = this.element.nativeElement.getBoundingClientRect();
    this.panelLeft = Math.max(16, Math.min(bounds.left, window.innerWidth - 336));
    this.panelTop = bounds.bottom + 6;
    this.open = true;
  }

  toggle(value: string): void {
    if (this.draft.has(value)) {
      this.draft.delete(value);
    } else {
      this.draft.add(value);
    }
  }

  toggleAllVisible(): void {
    const select = !this.allVisibleSelected;
    this.visibleOptions.forEach((option) => {
      if (select) this.draft.add(option.value);
      else this.draft.delete(option.value);
    });
  }

  clear(): void {
    this.draft.clear();
  }

  apply(): void {
    this.selectedValuesChange.emit([...this.draft]);
    this.open = false;
  }

  cancel(): void {
    this.open = false;
    this.search = '';
  }

  @HostListener('document:click', ['$event'])
  closeOnOutsideClick(event: MouseEvent): void {
    if (this.open && !this.element.nativeElement.contains(event.target as Node)) this.cancel();
  }

  @HostListener('document:keydown.escape')
  closeOnEscape(): void {
    if (this.open) this.cancel();
  }

  @HostListener('window:resize')
  @HostListener('window:scroll')
  closeOnViewportChange(): void {
    if (this.open) this.cancel();
  }
}