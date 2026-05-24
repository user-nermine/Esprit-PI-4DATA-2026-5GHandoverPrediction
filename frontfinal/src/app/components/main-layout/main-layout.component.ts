import { Component, Input } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { ROLES, Role } from '../login/login.component';

export interface PageMeta {
  icon: string;
  label: string;
}

export const PAGE_META: Record<string, PageMeta> = {
  kpi: { icon: '📊', label: 'KPI Monitoring' },
  anomaly: { icon: '⚠️', label: 'Signal Degradation' },
  diagnosis: { icon: '🔍', label: 'Radio Diagnosis' },
  optimization: { icon: '🎯', label: 'Optimization Support' },
  perfview: { icon: '📈', label: 'Performance View' },
  explainability: { icon: '💡', label: 'Explainability' },
  decisionsupport: { icon: '🤝', label: 'Decision Support' },
  nocoverview: { icon: '🖥️', label: 'NOC Overview' },
  reporting: { icon: '📑', label: 'Reporting' },
  mlflow: { icon: '🧪', label: 'ML Lifecycle' },
  retraining: { icon: '🔄', label: 'Retraining' },
  validation: { icon: '✅', label: 'Validation' },
  deployment: { icon: '🚀', label: 'Deployment' },
  users: { icon: '👤', label: 'Users & Roles' },
  datamgmt: { icon: '🗄️', label: 'Data Management' }
};

@Component({
  selector: 'app-main-layout',
  imports: [RouterOutlet],
  templateUrl: './main-layout.component.html',
  styleUrls: ['./main-layout.component.css']
})
export class MainLayoutComponent {
  @Input() currentUser: { role: string; email: string } | null = null;
  @Input() currentPage: string = '';

  constructor(private router: Router) {}

  get currentRole(): Role {
    return this.currentUser ? ROLES[this.currentUser.role] : ROLES['ran'];
  }

  get pageMeta(): PageMeta {
    return PAGE_META[this.currentPage] || { icon: '📄', label: 'Dashboard' };
  }

  navigateTo(page: string) {
    this.router.navigate([page]);
  }

  logout() {
    this.router.navigate(['/login']);
  }

  showReport() {
    // Navigate to report page or show report modal
    this.router.navigate(['/report']);
  }

  toggleDecision() {
    // Toggle decision widget visibility
    console.log('Toggle decision widget');
  }
}
