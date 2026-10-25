import { Component } from '@angular/core';
import { OutreachEventBrowser } from '../../../../shared/components/outreach-event-browser/outreach-event-browser';

@Component({
  selector: 'app-care-manager-outreach-events',
  standalone: true,
  imports: [OutreachEventBrowser],
  template: '<app-outreach-event-browser role="care-manager" />',
})
export class CareManagerOutreachEvents {}