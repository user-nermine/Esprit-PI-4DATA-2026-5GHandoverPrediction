import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthService } from 'src/app/demo/users/services/auth.service';

@Component({
  selector: 'app-admin-dashboard',
  imports: [CommonModule, RouterModule],
  templateUrl: './admin-dashboard.component.html',
  styleUrls: ['./admin-dashboard.component.scss']
})
export class AdminDashboardComponent {
  currentUser: any;

  constructor(private authService: AuthService) {
    this.currentUser = this.authService.getCurrentUser();
  }

  getStats() {
    return [
      { title: 'Total Utilisateurs', value: '1,234', icon: 'users', color: 'primary' },
      { title: 'Utilisateurs Actifs', value: '892', icon: 'user-check', color: 'success' },
      { title: 'Sessions Aujourd\'hui', value: '456', icon: 'activity', color: 'info' },
      { title: 'Alertes Système', value: '12', icon: 'alert-triangle', color: 'warning' }
    ];
  }

  getQuickActions() {
    return [
      { title: 'Gérer les Utilisateurs', route: '/users', icon: 'users', description: 'Ajouter, modifier ou supprimer des utilisateurs' },
      { title: 'Audit Logs', route: '/audit-logs', icon: 'file-text', description: 'Voir les logs d\'activité système' },
      { title: 'Configuration Système', route: '/system-config', icon: 'settings', description: 'Configurer les paramètres système' },
      { title: 'Rapports', route: '/reports', icon: 'bar-chart', description: 'Générer des rapports système' }
    ];
  }
}
