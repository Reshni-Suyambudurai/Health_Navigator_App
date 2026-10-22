export interface ApiSuccessResponse<TData> {
	status: 'success' | string;
	message: string;
	data: TData;
}

export interface UserRecord {
	user_id: number;
	first_name: string;
	last_name: string;
	email: string;
	status: string;
}

export interface UserCreateRequest {
	organization_id: number;
	role_id: number;
	first_name: string;
	last_name: string;
	email: string;
	password: string;
	phone?: string | null;
}

export interface LoginRequest {
	email: string;
	password: string;
}

export interface LoginData {
	user_id: number;
	userId?: number;
	email: string;
	roleId: number;
	roleName?: string | null;
	firstName: string;
	lastName: string;
	username?: string;
}

export interface UserListData {
	users: UserRecord[];
	count: number;
}

export interface CareTeamMember {
	user_id: number;
	first_name: string;
	last_name: string;
	phone: string | null;
	role_name: string;
}

export interface CareTeamData {
	users: CareTeamMember[];
	count: number;
}

export interface UserCreateData {
	user_id: number;
}

export interface UserDeleteData {
	// Backend returns data=None for delete; keep this empty type for semantic clarity.
}

export interface PatientOnboardingState {
	onboarding_required: boolean;
	user_complete: boolean;
	profile_complete: boolean;
	consent_complete: boolean;
	user: {
		user_id: number;
		first_name: string;
		last_name: string;
		email: string;
		phone: string | null;
	};
	profile: {
		patient_id: number;
		user_id: number;
		external_fhir_patient_id: string | null;
		date_of_birth: string | null;
		gender: string | null;
		preferred_language: string | null;
		preferred_contact_method: string | null;
		emergency_contact_name: string | null;
		emergency_contact_phone: string | null;
		risk_tier: string | null;
	} | null;
	consents: string[];
	options: {
		genders: string[];
		contact_methods: string[];
	};
}

export interface PatientProfileUpdateRequest {
	first_name: string;
	last_name: string;
	email: string;
	phone: string;
	date_of_birth: string;
	gender: string;
	preferred_language: string;
	preferred_contact_method: string;
	emergency_contact_name: string;
	emergency_contact_phone: string;
}

export interface PatientConsentRequest {
	consent_text_version?: string;
	ai_disclosure_accepted: boolean;
	reminders_accepted: boolean;
}

