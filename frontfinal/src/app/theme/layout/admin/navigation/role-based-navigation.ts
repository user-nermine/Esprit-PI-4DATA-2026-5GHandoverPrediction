import { Injectable } from '@angular/core';
import { AuthService } from 'src/app/demo/users/services/auth.service';

export interface NavigationItem {
  id: string;
  title: string;
  type: 'item' | 'collapse' | 'group';
  translate?: string;
  icon?: string;
  hidden?: boolean;
  url?: string;
  classes?: string;
  exactMatch?: boolean;
  external?: boolean;
  target?: boolean;
  breadcrumbs?: boolean;
  adminOnly?: boolean;
  children?: NavigationItem[];
}

@Injectable({
  providedIn: 'root'
})
export class RoleBasedNavigationService {
  
  constructor(private authService: AuthService) {}

  getNavigationItems(): NavigationItem[] {
    const currentUser = this.authService.getCurrentUser();
    
    if (!currentUser) {
      return [];
    }

    // Navigation selon le rôle de l'utilisateur
    switch (currentUser.role) {
      case 'SYSTEM_ADMIN':
        return this.getAdminNavigation();
      case 'DATA_SCIENTIST':
        return this.getDataScientistNavigation();
      case 'RAN_ENGINEER':
        return this.getRanEngineerNavigation();
      case 'NOC_ENGINEER':
        return this.getNocEngineerNavigation();
      case 'CORE_ENGINEER':
        return this.getPerformanceEngineerNavigation();
      case 'PERFORMANCE_ENGINEER':
        return this.getPerformanceEngineerNavigation();
      default:
        return this.getDefaultNavigation();
    }
  }

  private getAdminNavigation(): NavigationItem[] {
    return [
      {
        id: 'admin',
        title: 'Administration',
        type: 'group',
        icon: 'icon-user',
        adminOnly: true,
        children: [
          {
            id: 'user-list',
            title: 'All Users',
            type: 'item',
            url: '/admin',
            classes: 'nav-item',
            icon: 'feather icon-users',
            adminOnly: true
          },
          {
            id: 'user-add',
            title: 'Add User',
            type: 'item',
            url: '/admin/add',
            classes: 'nav-item',
            icon: 'feather icon-user-plus',
            adminOnly: true
          },
          {
            id: 'user-roles',
            title: 'Roles',
            type: 'item',
            url: '/admin/roles',
            classes: 'nav-item',
            icon: 'feather icon-shield',
            adminOnly: true
          },
          {
            id: 'audit-log',
            title: 'Audit Log',
            type: 'item',
            url: '/admin/audit-log',
            classes: 'nav-item',
            icon: 'feather icon-list',
            adminOnly: true
          }
        ]
      },

      // ── Role Views (read-only) ──────────────────
      {
        id: 'role-views',
        title: 'Role Views',
        type: 'group',
        icon: 'icon-eye',
        children: [
          {
            id: 'view-data-scientist',
            title: 'Data Scientist',
            type: 'collapse',
            icon: 'feather icon-pie-chart',
            children: [
              { id: 'ds-mlflow-v',      title: 'ML Lifecycle',       type: 'item', url: '/data-scientist/mlflow',      classes: 'nav-item', icon: 'feather icon-git-branch'    },
              { id: 'ds-retraining-v',  title: 'Retraining',         type: 'item', url: '/data-scientist/retraining',  classes: 'nav-item', icon: 'feather icon-refresh-cw'    },
              { id: 'ds-validation-v',  title: 'Validation',         type: 'item', url: '/data-scientist/validation',  classes: 'nav-item', icon: 'feather icon-check-circle'  }
            ]
          },
          {
            id: 'view-ran-engineer',
            title: 'RAN Engineer',
            type: 'collapse',
            icon: 'feather icon-radio',
            children: [
              { id: 'ran-kpi-v',     title: 'KPI Monitoring',    type: 'item', url: '/ran-engineer/kpi',    classes: 'nav-item', icon: 'feather icon-bar-chart'      },
              { id: 'ran-anomaly-v', title: 'Signal Degradation', type: 'item', url: '/ran-engineer/anomaly', classes: 'nav-item', icon: 'feather icon-alert-triangle' }
            ]
          },
          {
            id: 'view-noc-engineer',
            title: 'NOC Engineer',
            type: 'collapse',
            icon: 'feather icon-monitor',
            children: [
              { id: 'noc-monitoring-v', title: 'Monitoring', type: 'item', url: '/noc/monitoring', classes: 'nav-item', icon: 'feather icon-activity'  },
              { id: 'noc-reporting-v',  title: 'Reporting',  type: 'item', url: '/noc/reporting',  classes: 'nav-item', icon: 'feather icon-file-text' }
            ]
          },
          {
            id: 'view-performance-engineer',
            title: 'Core Engineer',
            type: 'collapse',
            icon: 'feather icon-trending-up',
            children: [
              { id: 'perf-view-v',          title: 'Performance View', type: 'item', url: '/core-engineer/performance-view', classes: 'nav-item', icon: 'feather icon-trending-up' },
              { id: 'perf-explainability-v', title: 'Explainability',  type: 'item', url: '/core-engineer/explainability',  classes: 'nav-item', icon: 'feather icon-help-circle'  }
            ]
          }
        ]
      }
    ];
  }

  private getDataScientistNavigation(): NavigationItem[] {
    return [
      {
        id: 'data-scientist',
        title: 'Data Scientist',
        type: 'group',
        icon: 'icon-pie-chart',
        children: [
          {
            id: 'ml-lifecycle',
            title: 'ML Lifecycle',
            type: 'item',
            url: '/data-scientist/mlflow',
            icon: 'feather icon-git-branch',
            classes: 'nav-item'
          },
          {
            id: 'ds-retraining',
            title: 'Retraining',
            type: 'item',
            url: '/data-scientist/retraining',
            icon: 'feather icon-refresh-cw',
            classes: 'nav-item'
          },
          {
            id: 'ds-validation',
            title: 'Validation',
            type: 'item',
            url: '/data-scientist/validation',
            icon: 'feather icon-check-circle',
            classes: 'nav-item'
          }
        ]
      }
    ];
  }

  private getRanEngineerNavigation(): NavigationItem[] {
    return [
      {
        id: 'ran-engineer',
        title: 'RAN Engineer',
        type: 'group',
        icon: 'icon-settings',
        children: [
          {
            id: 'ran-kpi',
            title: 'KPI Monitoring',
            type: 'item',
            url: '/ran-engineer/kpi',
            icon: 'feather icon-bar-chart',
            classes: 'nav-item'
          },
          {
            id: 'ran-anomaly',
            title: 'Signal Degradation',
            type: 'item',
            url: '/ran-engineer/anomaly',
            icon: 'feather icon-alert-triangle',
            classes: 'nav-item'
          },
        ]
      }
    ];
  }

  private getNocEngineerNavigation(): NavigationItem[] {
    return [
      {
        id: 'noc-engineer',
        title: 'NOC Engineer',
        type: 'group',
        icon: 'icon-monitor',
        children: [
          {
            id: 'monitoring',
            title: 'Monitoring',
            type: 'item',
            url: '/noc/monitoring',
            icon: 'feather icon-activity',
            classes: 'nav-item'
          },
          {
            id: 'reporting',
            title: 'Reporting',
            type: 'item',
            url: '/noc/reporting',
            icon: 'feather icon-file-text',
            classes: 'nav-item'
          }
        ]
      }
      
    ];
  }

  private getPerformanceEngineerNavigation(): NavigationItem[] {
    return [
      {
        id: 'core-engineer',
        title: 'Core Engineer',
        type: 'group',
        icon: 'icon-activity',
        children: [
          {
            id: 'performance-view',
            title: 'Performance View',
            type: 'item',
            url: '/core-engineer/performance-view',
            icon: 'feather icon-trending-up',
            classes: 'nav-item'
          },
          {
            id: 'explainability',
            title: 'Explainability',
            type: 'item',
            url: '/core-engineer/explainability',
            icon: 'feather icon-help-circle',
            classes: 'nav-item'
          }
        ]
      }
    ];
  }

  private getDefaultNavigation(): NavigationItem[] {
    return [];
  }
}

