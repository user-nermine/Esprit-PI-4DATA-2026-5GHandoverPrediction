import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from '../../demo/users/services/auth.service';

@Injectable({
  providedIn: 'root'
})
export class RoleRedirectDebugGuard implements CanActivate {
  constructor(private authService: AuthService, private router: Router) {}

  canActivate(): boolean {
    const currentUser = this.authService.getCurrentUser();
    
    console.log('🔍 DEBUG - RoleRedirectGuard activated');
    console.log('🔍 DEBUG - Current user:', currentUser);
    
    if (!currentUser) {
      console.log('🔍 DEBUG - No current user, redirecting to login');
      this.router.navigate(['/login']);
      return false;
    }

    console.log('🔍 DEBUG - User role:', currentUser.role);
    
    // Rediriger selon le rôle de l'utilisateur - basé sur les dashboards des dossiers séparés
    switch (currentUser.role) {
      case 'SYSTEM_ADMIN':
        console.log('🔍 DEBUG - Redirecting SYSTEM_ADMIN to /dashboard');
        this.router.navigate(['/dashboard']);
        return false;
      case 'DATA_SCIENTIST':
        console.log('🔍 DEBUG - Redirecting DATA_SCIENTIST to /data-scientist');
        this.router.navigate(['/data-scientist']);
        return false;
      case 'RAN_ENGINEER':
        console.log('🔍 DEBUG - Redirecting RAN_ENGINEER to /ran-engineer');
        this.router.navigate(['/ran-engineer']);
        return false;
      case 'NOC_ENGINEER':
        console.log('🔍 DEBUG - Redirecting NOC_ENGINEER to /dashboard (comme dans frontend3)');
        this.router.navigate(['/dashboard']);
        return false;
      case 'PERFORMANCE_ENGINEER':
        console.log('🔍 DEBUG - Redirecting PERFORMANCE_ENGINEER to /dashboard (comme dans frontend_performance)');
        this.router.navigate(['/dashboard']);
        return false;
      default:
        console.log('🔍 DEBUG - Unknown role, redirecting to /dashboard');
        this.router.navigate(['/dashboard']);
        return false;
    }
  }
}
