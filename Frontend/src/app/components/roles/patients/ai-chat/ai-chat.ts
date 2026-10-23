import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { ConversationApi } from '../../../../api/navigator/conversation.api';
import { getSessionUser } from '../../../../api/tokenstore';
import { CareTeamRequestStatus, ConversationMessage } from '../../../../shared/types/navigator/conversation';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

@Component({
  selector: 'app-ai-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.scss',
})
export class AiChat implements OnInit {
  private readonly conversationApi = inject(ConversationApi);
  private readonly toast = inject(ToastState);
  private readonly sessionUser = getSessionUser();

  readonly messages = signal<ConversationMessage[]>([]);
  readonly careTeamRequests = signal<CareTeamRequestStatus[]>([]);
  readonly messageDraft = signal('');
  readonly loading = signal(true);
  readonly isResponding = signal(false);
  readonly emergencyPaused = signal(false);
  readonly largeText = signal(false);
  readonly historyOpen = signal(false);
  private navigatorPrompt = this.navigationPromptFromState();

  ngOnInit(): void {
    if (!this.sessionUser) {
      this.loading.set(false);
      return;
    }

    this.conversationApi
      .getHistory(this.sessionUser.userId)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => {
          this.messages.set(response.data.messages);
          this.emergencyPaused.set(response.data.emergency_chat_paused);
          this.sendNavigationPrompt();
        },
        error: () => {
          this.toast.warning('Conversation history is temporarily unavailable.');
          this.sendNavigationPrompt();
        },
      });
    this.loadCareTeamRequests();
  }

  sendMessage(): void {
    const text = this.messageDraft().trim();
    if (!text || this.isResponding() || this.emergencyPaused() || !this.sessionUser) {
      return;
    }

    const optimisticMessage = this.optimisticPatientMessage(text);
    this.isResponding.set(true);
    this.messageDraft.set('');
    this.messages.update((messages) => [...messages, optimisticMessage]);
    this.conversationApi
      .sendMessage(this.sessionUser.userId, text)
      .pipe(finalize(() => this.isResponding.set(false)))
      .subscribe({
        next: (response) => {
          this.messages.update((messages) => [
            ...messages.filter((message) => message.message_id !== optimisticMessage.message_id),
            response.data.patient_message,
            response.data.assistant_message,
          ]);
          this.emergencyPaused.set(response.data.emergency_chat_paused);
          this.loadCareTeamRequests();
        },
        error: (error: unknown) => {
          this.messages.update((messages) => messages.filter((message) => message.message_id !== optimisticMessage.message_id));
          this.messageDraft.set(text);
          this.toast.error(this.extractErrorMessage(error));
        },
      });
  }

  onComposerKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  toggleLargeText(): void {
    this.largeText.set(!this.largeText());
  }

  toggleHistory(): void {
    this.historyOpen.set(!this.historyOpen());
  }

  acknowledgeAnswer(): void {
    this.messageDraft.set('Thank you, that helps.');
  }

  askForSimplerExplanation(): void {
    this.messageDraft.set('Please explain that in simpler words.');
  }

  formatTime(sentAt: string): string {
    return new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(new Date(sentAt));
  }

  formatRequestStatus(status: CareTeamRequestStatus['status']): string {
    return status.replace('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  careTeamRequestFor(escalationId: number): CareTeamRequestStatus | undefined {
    return this.careTeamRequests().find((request) => request.escalation_id === escalationId);
  }

  private loadCareTeamRequests(): void {
    if (!this.sessionUser) {
      return;
    }
    this.conversationApi.getCareTeamRequests(this.sessionUser.userId).subscribe({
      next: ({ data }) => this.careTeamRequests.set(data.requests),
      error: () => this.careTeamRequests.set([]),
    });
  }

  private navigationPromptFromState(): string | null {
    const state = history.state as Record<string, unknown> | null;
    const prompt = state?.['navigatorPrompt'];
    if (state && typeof prompt === 'string') {
      const { navigatorPrompt: _navigatorPrompt, ...remainingState } = state;
      history.replaceState(remainingState, document.title);
    }
    return typeof prompt === 'string' && prompt.trim() ? prompt.trim() : null;
  }

  private sendNavigationPrompt(): void {
    if (!this.navigatorPrompt || this.emergencyPaused()) {
      return;
    }

    this.messageDraft.set(this.navigatorPrompt);
    this.navigatorPrompt = null;
    this.sendMessage();
  }

  private optimisticPatientMessage(text: string): ConversationMessage {
    return {
      message_id: -Date.now(),
      sender: 'patient',
      text,
      sent_at: new Date().toISOString(),
      safety_category: null,
      escalation_id: null,
      is_guardrail_override: false,
      source_labels: [],
    };
  }

  private extractErrorMessage(error: unknown): string {
    if (typeof error !== 'object' || error === null) {
      return 'We could not send your message. Please try again.';
    }

    const response = error as { error?: { message?: string }; message?: string };
    return response.error?.message ?? response.message ?? 'We could not send your message. Please try again.';
  }
}
