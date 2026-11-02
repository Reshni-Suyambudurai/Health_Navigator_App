import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { marked } from 'marked';

@Component({
  selector: 'app-markdown-preview',
  standalone: true,
  templateUrl: './markdown-preview.html',
  styleUrl: './markdown-preview.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MarkdownPreview {
  readonly markdown = input('');
  readonly content = computed(() => marked.parse(this.markdown(), { async: false }));
}