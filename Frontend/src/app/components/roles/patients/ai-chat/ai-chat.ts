import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

interface DemoChatMessage {
  sender: 'patient' | 'assistant';
  text: string;
  time: string;
}

@Component({
  selector: 'app-ai-chat',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.scss',
})
export class AiChat {
  readonly messages: DemoChatMessage[] = [
    {
      sender: 'patient',
      text: 'I have a question about my care plan.',
      time: '9:14 AM',
    },
    {
      sender: 'assistant',
      text: 'I can help explain your care plan in plain language. For urgent symptoms, contact your care team or call 911.',
      time: '9:15 AM',
    },
    {
      sender: 'patient',
      text: 'Can you remind me what I should do today?',
      time: '9:16 AM',
    },
    {
      sender: 'assistant',
      text: 'Your next check-in is scheduled for today. You can also review your medicines and follow-up tasks in the care plan.',
      time: '9:16 AM',
    },
  ];
}
