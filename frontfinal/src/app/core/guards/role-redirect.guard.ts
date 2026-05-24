import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from '../../demo/users/services/auth.service';

@Injectable({
  providedIn: 'root'
})
export class RoleRedirectGuard implements CanActivate {
  constructor(private authService: AuthService, private router: Router) {}

  canActivate(): boolean {
    const currentUser = this.authService.getCurrentUser();
    
    if (!currentUser) {
      this.router.navigate(['/login']);
      return false;
    }

    // Rediriger selon le rôle de l'utilisateur - basé sur les dashboards originaux
    console.log('🔍 RoleRedirectGuard - User role:', currentUser.role);
    switch (currentUser.role) {
      case 'SYSTEM_ADMIN':
        this.router.navigate(['/admin']);
        return false;
      case 'DATA_SCIENTIST':
        console.log('🔍 Redirecting DATA_SCIENTIST to /data-scientist/mlflow');
        this.router.navigate(['/data-scientist/mlflow']);
        return false;
      case 'RAN_ENGINEER':
        console.log('🔍 Redirecting RAN_ENGINEER to /ran-engineer/kpi');
        this.router.navigate(['/ran-engineer/kpi']);
        return false;
      case 'NOC_ENGINEER':
        console.log('🔍 Redirecting NOC_ENGINEER to /noc/monitoring');
        this.router.navigate(['/noc/monitoring']);
        return false;
      case 'CORE_ENGINEER':
        console.log('?? Redirecting CORE_ENGINEER to /core-engineer/explainability');
        this.router.navigate(['/core-engineer/explainability']);
        return false;
      case 'PERFORMANCE_ENGINEER':
        console.log('🔍 Redirecting PERFORMANCE_ENGINEER to /core-engineer/performance-view');
        this.router.navigate(['/core-engineer/performance-view']);
        return false;
      default:
        console.log('🔍 Unknown role, redirecting to /dashboard');
        this.router.navigate(['/dashboard']); // Dashboard par défaut
        return false;
    }
  }
}

