import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../demo/users/services/auth.service';
import { Router } from '@angular/router';

export interface Role {
  key: string;
  name: string;
  icon: string;
  description: string;
  color: string;
  bg: string;
  avatar: string;
  pages: string[];
}

export const ROLES: Record<string, Role> = {
  ran: { key: 'ran', name: 'RAN Engineer', icon: '??', description: 'Radio KPI & diagnosis', color: '#1E4FC2', bg: '#E8F0FE', avatar: 'RE', pages: ['kpi', 'anomaly', 'diagnosis'] },
  perf: { key: 'perf', name: 'Perf/Optim. Engineer', icon: '?', description: 'Performance & SHAP', color: '#7C3AED', bg: '#EDE9FE', avatar: 'PE', pages: ['perfview', 'explainability'] },
  noc: { key: 'noc', name: 'NOC Engineer', icon: '???', description: 'Operations center', color: '#0891B2', bg: '#CFFAFE', avatar: 'NE', pages: ['monitoring', 'reporting'] },
  ds: { key: 'ds', name: 'Data Scientist', icon: '??', description: 'ML lifecycle & models', color: '#059669', bg: '#D1FAE5', avatar: 'DS', pages: ['mlflow', 'retraining', 'validation'] },
  admin: { key: 'admin', name: 'System Admin', icon: '??', description: 'Users, roles & data', color: '#DC2626', bg: '#FEE2E2', avatar: 'SA', pages: ['users', 'datamgmt'] }
};

@Component({
  selector: 'app-login',
  imports: [FormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  email: string = '';
  password: string = '';
  errorMessage: string = '';

  constructor(private authService: AuthService, private router: Router) {}

  onLogin() {
    this.errorMessage = '';
    if (!this.email || !this.password) return;

    this.authService.login({ email: this.email, password: this.password }).subscribe({
      next: (response) => {
        // Rediriger selon le role
        const role = response.role;
        const routes: Record<string, string> = {
          'SYSTEM_ADMIN': '/dashboard',
          'DATA_SCIENTIST': '/data-scientist/mlflow',
          'RAN_ENGINEER': '/ran-engineer/kpi',
          'NOC_ENGINEER': '/monitoring',
          'CORE_ENGINEER': '/performance-view',
        };
        this.router.navigate([routes[role] || '/dashboard']);
      },
      error: (err) => {
        this.errorMessage = 'Email ou mot de passe incorrect';
        console.error('Login error:', err);
      }
    });
  }
}

