export interface ApiSuccessResponse<TData> {
	status: 'success' | string;
	message: string;
	data: TData;
}

export type FhirPrimitive = string | number | boolean | null;
export type FhirFieldValue = FhirPrimitive | FhirFieldValue[] | { [key: string]: FhirFieldValue };
export type FhirRecord = { [key: string]: FhirFieldValue };

export type PatientRecord = FhirRecord;
export type ConditionRecord = FhirRecord;
export type MedicationRecord = FhirRecord;
export type CarePlanRecord = FhirRecord;
export type EncounterRecord = FhirRecord;
export type ObservationRecord = FhirRecord;
export type AppointmentRecord = FhirRecord;
export type FhirResourceRecord = FhirRecord;
export type PatientContext = FhirRecord;
export type PatientContextSummary = FhirRecord;
export type PatientHealthRecord = FhirRecord;

export interface PatientListData {
	patients: PatientRecord[];
	count: number;
}

export interface ConditionListData {
	conditions: ConditionRecord[];
	count: number;
}

export interface MedicationListData {
	medications: MedicationRecord[];
	count: number;
}

export interface CarePlanListData {
	care_plans: CarePlanRecord[];
	count: number;
}

export interface EncounterListData {
	encounters: EncounterRecord[];
	count: number;
}

export interface ObservationListData {
	observations: ObservationRecord[];
	count: number;
}

export interface AppointmentListData {
	appointments: AppointmentRecord[];
	count: number;
}

export interface FhirResourceListData {
	resources: FhirResourceRecord[];
	count: number;
}

export interface PaginationParams {
	skip?: number;
	limit?: number;
}
