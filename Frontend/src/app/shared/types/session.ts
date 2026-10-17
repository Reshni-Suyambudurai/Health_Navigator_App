export type ThemeMode = 'light' | 'dark';

export interface SessionUser {
  userId: number;
  email: string;
  roleId: number;
  roleName: string | null;
  firstName: string;
  lastName: string;
  username: string;
}
