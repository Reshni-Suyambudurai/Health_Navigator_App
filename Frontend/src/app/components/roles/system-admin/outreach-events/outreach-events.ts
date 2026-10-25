import { Component } from '@angular/core';
import { OutreachEventBrowser } from '../../../../shared/components/outreach-event-browser/outreach-event-browser';

@Component({
  selector: 'app-system-admin-outreach-events',
  standalone: true,
  imports: [OutreachEventBrowser],
  template: '<app-outreach-event-browser role="admin" />',
})
export class SystemAdminOutreachEvents {}