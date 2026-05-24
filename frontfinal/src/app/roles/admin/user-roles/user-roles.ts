import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

interface Role {
  name: string;
  description: string;
  permissions: string[];
  usersCount: number;
  color: string;
}

interface PermissionFeature {
  name: string;
  ran: boolean;
  perf: boolean;
  noc: boolean;
  ds: boolean;
  admin: boolean;
}

@Component({
  selector: 'app-user-roles',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './user-roles.html',
  styleUrl: './user-roles.scss'
})
export class UserRoles {
  roles: Role[] = [
    {
      name: 'System Admin',
      description: 'Full access to all platform features',
      permissions: ['Manage Users', 'View Reports', 'Configure System', 'Access All Data', 'Manage Roles'],
      usersCount: 2,
      color: 'bg-danger'
    },
    {
      name: 'Data Scientist',
      description: 'Access to ML models and datasets',
      permissions: ['View Models', 'Train Models', 'Access Datasets', 'View Reports'],
      usersCount: 5,
      color: 'bg-primary'
    },
    {
      name: 'RAN Engineer',
      description: 'Access to network and handover data',
      permissions: ['View Network Data', 'View Handover Stats', 'View Reports'],
      usersCount: 4,
      color: 'bg-warning'
    },
    {
      name: 'NOC Engineer',
      description: 'Monitoring and alerting access',
      permissions: ['View Monitoring', 'Manage Alerts', 'View Reports'],
      usersCount: 3,
      color: 'bg-info'
    }
  ];

  permissionsMatrix: PermissionFeature[] = [
    { name: 'KPI Dashboard',      ran: true,  perf: true,  noc: true,  ds: true,  admin: true  },
    { name: 'Signal Degradation',  ran: true,  perf: true,  noc: true,  ds: true,  admin: true  },
    { name: 'SHAP Explainability',ran: false, perf: true,  noc: false, ds: true,  admin: true  },
    { name: 'Model Deployment',   ran: false, perf: false, noc: false, ds: true,  admin: true  },
    { name: 'User Management',    ran: false, perf: false, noc: false, ds: false, admin: true  },
    { name: 'Data Management',    ran: false, perf: false, noc: false, ds: true,  admin: true  },
  ];
}