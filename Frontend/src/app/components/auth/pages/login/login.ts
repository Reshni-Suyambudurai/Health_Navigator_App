import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { UserApi } from '../../../../api/navigator/user.api';
import { LoginData, LoginRequest } from '../../../../shared/types/navigator/user';
import { ToastState } from '../../../../shared/ui/toast/toast-state';
import { saveSessionUser } from '../../../../api/tokenstore';
import { SessionUser } from '../../../../shared/types/session';
import { getDashboardRouteForRole } from '../../../../shared/utils/role-route';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private readonly router = inject(Router);
  private readonly userApi = inject(UserApi);
  private readonly toast = inject(ToastState);

  email = signal('');
  password = signal('');
  showPassword = signal(false);
  rememberMe = signal(false);
  showAlert = signal(true);
  loading = signal(false);

  togglePasswordVisibility(): void {
    this.showPassword.set(!this.showPassword());
  }

  signIn(): void {
    this.submit();
  }

  submit(): void {
    const email = this.email().trim();
    const password = this.password();

    if (!email || !password) {
      this.toast.warning('Please enter your email and password.');
      return;
    }

    const payload: LoginRequest = { email, password };

    this.loading.set(true);

    this.userApi
      .login(payload)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => {
          const loginData = response.data;
          const route = this.resolveRouteByRole(loginData);
          saveSessionUser(this.toSessionUser(loginData));

          this.toast.success(`Welcome ${loginData.firstName} ${loginData.lastName}`);
          this.router.navigate([route]);
        },
        error: (error: unknown) => {
          const message = this.extractErrorMessage(error);
          this.toast.error(message);
        },
      });
  }

  private resolveRouteByRole(loginData: LoginData): string {
    return getDashboardRouteForRole(loginData.roleId, loginData.roleName);
  }

  private toSessionUser(loginData: LoginData): SessionUser {
    return {
      user_id: loginData.user_id,
      userId: loginData.user_id,
      organization_id: loginData.organization_id,
      email: loginData.email,
      roleId: loginData.roleId,
      roleName: loginData.roleName ?? null,
      firstName: loginData.firstName,
      lastName: loginData.lastName,
      username: loginData.username ?? `${loginData.firstName} ${loginData.lastName}`,
    };
  }

  private extractErrorMessage(error: unknown): string {
    const fallback = 'Login failed. Please check your credentials and try again.';

    if (typeof error !== 'object' || error === null) {
      return fallback;
    }

    const maybeError = error as {
      error?: { message?: string };
      message?: string;
    };

    return maybeError.error?.message ?? maybeError.message ?? fallback;
  }
}
