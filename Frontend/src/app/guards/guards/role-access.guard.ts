import { CanActivateChildFn, RouterStateSnapshot, Router } from '@angular/router';
import { inject } from '@angular/core';
import { getSessionUser } from '../../api/tokenstore';
import { getDashboardRouteForRole } from '../../shared/utils/role-route';

function getRequestedRolePath(state: RouterStateSnapshot): string | null {
  const routePath = state.url.split('?')[0].split('#')[0];
  const segments = routePath.split('/').filter(Boolean);
  if (segments.length < 2) {
    return null;
  }

  const roleSegment = segments[0];
  return roleSegment || null;
}

export const roleAccessGuard: CanActivateChildFn = (_childRoute, state) => {
  const router = inject(Router);
  const session = getSessionUser();

  if (!session) {
    return router.createUrlTree(['/login']);
  }

  const expectedRoute = getDashboardRouteForRole(session.roleId, session.roleName);
  const expectedRoleSegment = expectedRoute.split('/').filter(Boolean)[0] ?? '';
  const requestedRoleSegment = getRequestedRolePath(state);

  if (!requestedRoleSegment) {
    return router.createUrlTree([expectedRoute]);
  }

  if (requestedRoleSegment !== expectedRoleSegment) {
    return router.createUrlTree([expectedRoute]);
  }

  return true;
};
