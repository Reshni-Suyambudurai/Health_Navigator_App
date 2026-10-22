import { SessionUser, ThemeMode } from '../shared/types/session';

const STORAGE_KEYS = {
	session: 'pha.session.user',
	theme: 'pha.theme.mode',
} as const;

function hasWindow(): boolean {
	return typeof window !== 'undefined' && !!window.localStorage;
}

export function saveSessionUser(user: SessionUser): void {
	if (hasWindow()) {
		window.localStorage.setItem(STORAGE_KEYS.session, JSON.stringify(user));
	}
}

export function getSessionUser(): SessionUser | null {
	if (!hasWindow()) {
		return null;
	}

	const raw = window.localStorage.getItem(STORAGE_KEYS.session);
	if (!raw) {
		return null;
	}

	try {
		const user = JSON.parse(raw) as Partial<SessionUser>;
		const userId = user.user_id ?? user.userId;

		if (typeof userId !== 'number') {
			return null;
		}

		return {
			...user,
			user_id: userId,
			userId,
		} as SessionUser;
	} catch {
		return null;
	}
}

export function isLoggedIn(): boolean {
	return !!getSessionUser();
}

export function clearSessionUser(): void {
	if (!hasWindow()) {
		return;
	}

	window.localStorage.removeItem(STORAGE_KEYS.session);
}

export function setThemeMode(mode: ThemeMode): void {
	if (!hasWindow()) {
		return;
	}

	window.localStorage.setItem(STORAGE_KEYS.theme, mode);
}

export function getThemeMode(): ThemeMode {
	if (!hasWindow()) {
		return 'light';
	}

	const mode = window.localStorage.getItem(STORAGE_KEYS.theme);
	return mode === 'dark' ? 'dark' : 'light';
}

export function clearThemeMode(): void {
	if (!hasWindow()) {
		return;
	}

	window.localStorage.removeItem(STORAGE_KEYS.theme);
}
