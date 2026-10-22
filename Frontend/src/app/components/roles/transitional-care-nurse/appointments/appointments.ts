import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { finalize } from 'rxjs/operators';
import { getSessionUser } from '../../../../api/tokenstore';
import { AppointmentApi } from '../../../../api/navigator/appointment.api';
import {
	AppointmentRecord,
	AppointmentStatus,
	AvailabilityRecord,
	AvailabilityRequest,
	DayOfWeek,
} from '../../../../shared/types/navigator/appointment';
import { ToastState } from '../../../../shared/ui/toast/toast-state';

type AvailabilityDaySelection = DayOfWeek | 'WEEKDAYS';
type AvailabilityForm = Omit<AvailabilityRequest, 'day_of_week'> & {
	day_of_week: AvailabilityDaySelection;
};

@Component({
	selector: 'app-transitional-care-nurse-appointments',
	standalone: true,
	imports: [CommonModule, FormsModule],
	templateUrl: './appointments.html',
	styleUrl: './appointments.scss',
})
export class TransitionalCareNurseAppointments implements OnInit {
	private readonly appointmentApi = inject(AppointmentApi);
	private readonly toast = inject(ToastState);
	private readonly sessionUser = getSessionUser();

	readonly upcoming = signal<AppointmentRecord[]>([]);
	readonly history = signal<AppointmentRecord[]>([]);
	readonly availability = signal<AvailabilityRecord[]>([]);
	readonly loading = signal(false);
	readonly savingAvailability = signal(false);
	readonly updatingAvailabilityIds = signal<ReadonlySet<number>>(new Set<number>());
	readonly error = signal<string | null>(null);
	readonly availabilityModalOpen = signal(false);
	readonly availabilityError = signal<string | null>(null);
	readonly today = new Date().toISOString().slice(0, 10);

	readonly days: AvailabilityDaySelection[] = [
		'WEEKDAYS',
		'MONDAY',
		'TUESDAY',
		'WEDNESDAY',
		'THURSDAY',
		'FRIDAY',
		'SATURDAY',
		'SUNDAY',
	];

	availabilityForm: AvailabilityForm = this.defaultAvailabilityForm();

	ngOnInit(): void {
		this.loadPage();
	}

	loadPage(): void {
		const userId = this.sessionUser?.user_id ?? this.sessionUser?.userId;
		if (!userId) {
			this.error.set('Your session has expired. Please sign in again.');
			return;
		}

		this.loading.set(true);
		this.error.set(null);
		forkJoin({
			upcoming: this.appointmentApi.getNurseUpcoming(userId),
			history: this.appointmentApi.getNurseHistory(userId),
		})
			.pipe(finalize(() => this.loading.set(false)))
			.subscribe({
				next: (response) => {
					this.upcoming.set(response.upcoming.data.appointments);
					this.history.set(response.history.data.appointments);
				},
				error: (error: { error?: { message?: string } }) => {
					this.error.set(error?.error?.message ?? 'Unable to load appointments right now.');
				},
			});
	}

	openAvailability(): void {
		const userId = this.sessionUser?.user_id ?? this.sessionUser?.userId;
		if (!userId) {
			this.error.set('Your session has expired. Please sign in again.');
			return;
		}

		this.availabilityModalOpen.set(true);
		this.availabilityError.set(null);
		this.appointmentApi.getNurseAvailability(userId).subscribe({
			next: (response) => this.availability.set(response.data.availability),
			error: () => this.availabilityError.set('Unable to load your saved availability.'),
		});
	}

	closeAvailability(): void {
		this.availabilityModalOpen.set(false);
	}

	openPicker(input: HTMLInputElement): void {
		if (typeof input.showPicker === 'function') {
			input.showPicker();
		} else {
			input.focus();
		}
	}

	saveAvailability(): void {
		const userId = this.sessionUser?.user_id ?? this.sessionUser?.userId;
		if (!userId) {
			this.availabilityError.set('Your session has expired. Please sign in again.');
			return;
		}
		if (this.availabilityForm.end_time <= this.availabilityForm.start_time) {
			this.availabilityError.set('End time must be after start time.');
			return;
		}
		if ((this.availabilityForm.lunch_start_time === null) !== (this.availabilityForm.lunch_end_time === null)) {
			this.availabilityError.set('Enter both lunch start and lunch end, or leave both blank.');
			return;
		}
		if (
			this.availabilityForm.lunch_start_time &&
			this.availabilityForm.lunch_end_time &&
			(this.availabilityForm.lunch_start_time >= this.availabilityForm.lunch_end_time ||
				this.availabilityForm.lunch_start_time < this.availabilityForm.start_time ||
				this.availabilityForm.lunch_end_time > this.availabilityForm.end_time)
		) {
			this.availabilityError.set('Lunch must be inside the availability window.');
			return;
		}
		if (
			this.availabilityForm.effective_until &&
			this.availabilityForm.effective_until < this.availabilityForm.effective_from
		) {
			this.availabilityError.set('End date must not be before start date.');
			return;
		}

		this.savingAvailability.set(true);
		this.availabilityError.set(null);
		const selectedDays: DayOfWeek[] = this.availabilityForm.day_of_week === 'WEEKDAYS'
			? ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']
			: [this.availabilityForm.day_of_week];
		const requests = selectedDays.map((day) =>
			this.appointmentApi.createNurseAvailability(userId, {
				...this.availabilityForm,
				day_of_week: day,
			}),
		);

		forkJoin(requests)
			.pipe(finalize(() => this.savingAvailability.set(false)))
			.subscribe({
					next: () => {
						this.toast.success('Availability saved successfully.');
					this.availabilityForm = this.defaultAvailabilityForm();
					this.openAvailability();
				},
				error: (error: { error?: { message?: string } }) => {
					this.availabilityError.set(error?.error?.message ?? 'Unable to save availability.');
				},
			});
	}

	toggleAvailabilityStatus(item: AvailabilityRecord): void {
		const userId = this.sessionUser?.user_id ?? this.sessionUser?.userId;
		if (!userId || this.updatingAvailabilityIds().has(item.availability_id)) {
			return;
		}

		this.updatingAvailabilityIds.update((ids) => new Set(ids).add(item.availability_id));
		this.availabilityError.set(null);
		this.appointmentApi.updateNurseAvailability(userId, item.availability_id, {
			day_of_week: item.day_of_week,
			start_time: item.start_time,
			end_time: item.end_time,
			lunch_start_time: item.lunch_start_time,
			lunch_end_time: item.lunch_end_time,
			effective_from: item.effective_from,
			effective_until: item.effective_until,
			is_active: !item.is_active,
		})
			.pipe(finalize(() => {
				this.updatingAvailabilityIds.update((ids) => {
					const nextIds = new Set(ids);
					nextIds.delete(item.availability_id);
					return nextIds;
				});
			}))
			.subscribe({
				next: (response) => {
					this.availability.update((items) =>
						items.map((existing) => existing.availability_id === item.availability_id ? response.data : existing),
					);
					this.toast.success(response.message);
				},
				error: (error: { error?: { message?: string } }) => {
					this.availabilityError.set(error?.error?.message ?? 'Unable to update availability status.');
				},
			});
	}

	statusClass(status: AppointmentStatus): string {
		if (['CONFIRMED', 'SCHEDULED', 'REQUESTED', 'RESCHEDULED'].includes(status)) {
			return 'status-positive';
		}
		if (['CANCELLED', 'NO_SHOW'].includes(status)) {
			return 'status-critical';
		}
		if (status === 'COMPLETED') {
			return 'status-negative';
		}
		return 'status-warning';
	}

	formatDateTime(value: string): string {
		return new Date(value).toLocaleString([], {
			dateStyle: 'medium',
			timeStyle: 'short',
		});
	}

	private defaultAvailabilityForm(): AvailabilityForm {
		return {
			day_of_week: 'MONDAY',
			start_time: '09:00',
			end_time: '17:00',
			lunch_start_time: null,
			lunch_end_time: null,
			effective_from: new Date().toISOString().slice(0, 10),
			effective_until: null,
			is_active: true,
		};
	}
}
