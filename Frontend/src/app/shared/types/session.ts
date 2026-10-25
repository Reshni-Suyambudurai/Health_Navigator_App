export type ThemeMode = 'light' | 'dark';

export interface SessionUser {
  user_id: number;
  userId: number;
  organization_id?: number;
  email: string;
  roleId: number;
  roleName: string | null;
  firstName: string;
  lastName: string;
  username: string;
}
