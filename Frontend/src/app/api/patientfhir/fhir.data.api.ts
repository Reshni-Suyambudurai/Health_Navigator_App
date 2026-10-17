import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
	ApiSuccessResponse,
	AppointmentListData,
	AppointmentRecord,
	CarePlanListData,
	CarePlanRecord,
	ConditionListData,
	ConditionRecord,
	EncounterListData,
	EncounterRecord,
	FhirResourceListData,
	FhirResourceRecord,
	MedicationListData,
	MedicationRecord,
	ObservationListData,
	ObservationRecord,
	PaginationParams,
	PatientContext,
	PatientContextSummary,
	PatientHealthRecord,
	PatientListData,
	PatientRecord,
} from '../../shared/types/patientfhir/fhir';

@Injectable({ providedIn: 'root' })
export class FhirDataApi {
	private readonly http = inject(HttpClient);
	private readonly baseUrl = `${environment.apiBaseUrl}/patientFHIR`;

	getPatients(options: PaginationParams = {}): Observable<ApiSuccessResponse<PatientListData>> {
		const params = this.buildPaginationParams(options);
		return this.http.get<ApiSuccessResponse<PatientListData>>(`${this.baseUrl}/patients`, { params });
	}

	getPatientById(patientId: string): Observable<ApiSuccessResponse<PatientRecord>> {
		return this.http.get<ApiSuccessResponse<PatientRecord>>(`${this.baseUrl}/patients/${patientId}`);
	}

	getPatientByFhirId(fhirPatientId: string): Observable<ApiSuccessResponse<PatientRecord>> {
		return this.http.get<ApiSuccessResponse<PatientRecord>>(`${this.baseUrl}/patients/fhir/${fhirPatientId}`);
	}

	getPatientContext(patientId: string): Observable<ApiSuccessResponse<PatientContext>> {
		return this.http.get<ApiSuccessResponse<PatientContext>>(`${this.baseUrl}/patients/${patientId}/context`);
	}

	refreshPatientContext(patientId: string): Observable<ApiSuccessResponse<PatientContext>> {
		return this.http.post<ApiSuccessResponse<PatientContext>>(
			`${this.baseUrl}/patients/${patientId}/context/refresh`,
			{}
		);
	}

	getPatientContextSummary(patientId: string): Observable<ApiSuccessResponse<PatientContextSummary>> {
		return this.http.get<ApiSuccessResponse<PatientContextSummary>>(
			`${this.baseUrl}/patients/${patientId}/context/summary`
		);
	}

	getPatientConditions(patientId: string): Observable<ApiSuccessResponse<ConditionListData>> {
		return this.http.get<ApiSuccessResponse<ConditionListData>>(`${this.baseUrl}/patients/${patientId}/conditions`);
	}

	getPatientActiveConditions(patientId: string): Observable<ApiSuccessResponse<ConditionListData>> {
		return this.http.get<ApiSuccessResponse<ConditionListData>>(
			`${this.baseUrl}/patients/${patientId}/conditions/active`
		);
	}

	getCondition(conditionId: string): Observable<ApiSuccessResponse<ConditionRecord>> {
		return this.http.get<ApiSuccessResponse<ConditionRecord>>(`${this.baseUrl}/conditions/${conditionId}`);
	}

	getPatientMedications(patientId: string): Observable<ApiSuccessResponse<MedicationListData>> {
		return this.http.get<ApiSuccessResponse<MedicationListData>>(`${this.baseUrl}/patients/${patientId}/medications`);
	}

	getPatientActiveMedications(patientId: string): Observable<ApiSuccessResponse<MedicationListData>> {
		return this.http.get<ApiSuccessResponse<MedicationListData>>(
			`${this.baseUrl}/patients/${patientId}/medications/active`
		);
	}

	getPatientMedicationHistory(patientId: string): Observable<ApiSuccessResponse<MedicationListData>> {
		return this.http.get<ApiSuccessResponse<MedicationListData>>(
			`${this.baseUrl}/patients/${patientId}/medications/history`
		);
	}

	getMedication(medicationId: string): Observable<ApiSuccessResponse<MedicationRecord>> {
		return this.http.get<ApiSuccessResponse<MedicationRecord>>(`${this.baseUrl}/medications/${medicationId}`);
	}

	getPatientCarePlans(patientId: string): Observable<ApiSuccessResponse<CarePlanListData>> {
		return this.http.get<ApiSuccessResponse<CarePlanListData>>(`${this.baseUrl}/patients/${patientId}/care-plans`);
	}

	getPatientActiveCarePlans(patientId: string): Observable<ApiSuccessResponse<CarePlanListData>> {
		return this.http.get<ApiSuccessResponse<CarePlanListData>>(
			`${this.baseUrl}/patients/${patientId}/care-plans/active`
		);
	}

	getCarePlan(carePlanId: string): Observable<ApiSuccessResponse<CarePlanRecord>> {
		return this.http.get<ApiSuccessResponse<CarePlanRecord>>(`${this.baseUrl}/care-plans/${carePlanId}`);
	}

	getPatientEncounters(patientId: string): Observable<ApiSuccessResponse<EncounterListData>> {
		return this.http.get<ApiSuccessResponse<EncounterListData>>(`${this.baseUrl}/patients/${patientId}/encounters`);
	}

	getPatientRecentEncounters(patientId: string, limit = 10): Observable<ApiSuccessResponse<EncounterListData>> {
		const params = new HttpParams().set('limit', limit);
		return this.http.get<ApiSuccessResponse<EncounterListData>>(
			`${this.baseUrl}/patients/${patientId}/encounters/recent`,
			{ params }
		);
	}

	getPatientLatestHospitalization(patientId: string): Observable<ApiSuccessResponse<EncounterRecord>> {
		return this.http.get<ApiSuccessResponse<EncounterRecord>>(
			`${this.baseUrl}/patients/${patientId}/encounters/latest-hospitalization`
		);
	}

	getPatientObservations(patientId: string): Observable<ApiSuccessResponse<ObservationListData>> {
		return this.http.get<ApiSuccessResponse<ObservationListData>>(`${this.baseUrl}/patients/${patientId}/observations`);
	}

	getPatientRecentObservations(patientId: string, limit = 20): Observable<ApiSuccessResponse<ObservationListData>> {
		const params = new HttpParams().set('limit', limit);
		return this.http.get<ApiSuccessResponse<ObservationListData>>(
			`${this.baseUrl}/patients/${patientId}/observations/recent`,
			{ params }
		);
	}

	getPatientObservationsByCode(patientId: string, code: string): Observable<ApiSuccessResponse<ObservationListData>> {
		return this.http.get<ApiSuccessResponse<ObservationListData>>(
			`${this.baseUrl}/patients/${patientId}/observations/${code}`
		);
	}

	getPatientLatestObservationByCode(patientId: string, code: string): Observable<ApiSuccessResponse<ObservationRecord>> {
		return this.http.get<ApiSuccessResponse<ObservationRecord>>(
			`${this.baseUrl}/patients/${patientId}/observations/${code}/latest`
		);
	}

	getPatientAppointments(patientId: string): Observable<ApiSuccessResponse<AppointmentListData>> {
		return this.http.get<ApiSuccessResponse<AppointmentListData>>(`${this.baseUrl}/patients/${patientId}/appointments`);
	}

	getPatientUpcomingAppointments(patientId: string): Observable<ApiSuccessResponse<AppointmentListData>> {
		return this.http.get<ApiSuccessResponse<AppointmentListData>>(
			`${this.baseUrl}/patients/${patientId}/appointments/upcoming`
		);
	}

	getPatientNextAppointment(patientId: string): Observable<ApiSuccessResponse<AppointmentRecord>> {
		return this.http.get<ApiSuccessResponse<AppointmentRecord>>(`${this.baseUrl}/patients/${patientId}/appointments/next`);
	}

	getAppointment(appointmentId: string): Observable<ApiSuccessResponse<AppointmentRecord>> {
		return this.http.get<ApiSuccessResponse<AppointmentRecord>>(`${this.baseUrl}/appointments/${appointmentId}`);
	}

	getPatientFhirResources(patientId: string): Observable<ApiSuccessResponse<FhirResourceListData>> {
		return this.http.get<ApiSuccessResponse<FhirResourceListData>>(
			`${this.baseUrl}/fhir/patients/${patientId}/resources`
		);
	}

	getPatientFhirResourcesByType(
		patientId: string,
		resourceType: string
	): Observable<ApiSuccessResponse<FhirResourceListData>> {
		return this.http.get<ApiSuccessResponse<FhirResourceListData>>(
			`${this.baseUrl}/fhir/patients/${patientId}/resources/${resourceType}`
		);
	}

	getFhirResource(resourceType: string, resourceId: string): Observable<ApiSuccessResponse<FhirResourceRecord>> {
		return this.http.get<ApiSuccessResponse<FhirResourceRecord>>(
			`${this.baseUrl}/fhir/resources/${resourceType}/${resourceId}`
		);
	}

	getPatientHealthRecordByFhirId(fhirPatientId: string): Observable<ApiSuccessResponse<PatientHealthRecord>> {
		return this.http.get<ApiSuccessResponse<PatientHealthRecord>>(`${this.baseUrl}/records/fhir/${fhirPatientId}`);
	}

	getPatientHealthRecordByPatientId(patientId: string): Observable<ApiSuccessResponse<PatientHealthRecord>> {
		return this.http.get<ApiSuccessResponse<PatientHealthRecord>>(`${this.baseUrl}/records/patients/${patientId}`);
	}

	private buildPaginationParams(options: PaginationParams): HttpParams {
		let params = new HttpParams();

		if (options.skip !== undefined) {
			params = params.set('skip', options.skip);
		}

		if (options.limit !== undefined) {
			params = params.set('limit', options.limit);
		}

		return params;
	}
}
