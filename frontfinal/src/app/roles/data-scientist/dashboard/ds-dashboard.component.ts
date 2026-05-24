import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthService } from 'src/app/demo/users/services/auth.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-ds-dashboard',
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './ds-dashboard.component.html',
  // styleUrls: ['./ds-dashboard.component.scss'] // Commented out - file not found
})
export class DsDashboardComponent {
  currentUser: any;

  // Zone selection properties
  selectedZone: string = 'Zone_77'; // Default selection
  availableZones: string[] = ['Zone_77', 'Zone_78', 'Zone_79', 'Zone_80', 'Zone_81', 'Zone_82', 'Zone_83', 'Zone_84', 'Zone_85'];
  
  // Dashboard cells data
  dashboardCells: any[] = [];

  constructor(private authService: AuthService) {
    this.currentUser = this.authService.getCurrentUser();
    this.loadSimulatorData();
  }

  getStats() {
    return [
      { title: 'Modèles Actifs', value: '12', icon: 'cpu', color: 'primary' },
      { title: 'Précision Moyenne', value: '94.2%', icon: 'trending-up', color: 'success' },
      { title: 'Datasets', value: '28', icon: 'database', color: 'info' },
      { title: 'Entraînements en cours', value: '3', icon: 'play-circle', color: 'warning' }
    ];
  }

  getQuickActions() {
    return [
      { title: 'New Model Training', icon: 'plus', route: '/demo/data-scientist/model-training' },
      { title: 'View Predictions', icon: 'chart-bar', route: '/demo/data-scientist/predictions' },
      { title: 'Data Management', icon: 'database', route: '/demo/data-scientist/data-management' }
    ];
  }

  getRecentModels() {
    return [
      { name: 'LSTM v1.2', accuracy: '95.1%', status: 'En production', lastUpdate: 'Il y a 2h' },
      { name: 'XGBoost v2.3', accuracy: '94.3%', status: 'Actif', lastUpdate: 'Il y a 1j' },
      { name: 'Random Forest v1.8', accuracy: '92.7%', status: 'En validation', lastUpdate: 'Il y a 3j' }
    ];
  }

  // Zone selection methods
  onZoneChange(): void {
    console.log('Zone changed to:', this.selectedZone);
    this.loadDashboardData();
  }

  getFilteredCells(): any[] {
    if (!this.selectedZone || this.selectedZone === 'all') {
      return this.dashboardCells;
    }
    
    return this.dashboardCells.filter(cell => 
      cell.zone === this.selectedZone || 
      cell.zone_id === this.selectedZone ||
      `Zone_${cell.cluster_id}` === this.selectedZone
    );
  }

  private loadDashboardData(): void {
    // Load static data based on selected zone
    this.loadSimulatorData();
  }

  private loadSimulatorData(): void {
    // Static simulator data for 9 zones
    const zoneData = [
      { zone_id: 77, zone: 'Zone_77', cluster_id: 77, rsrp: -75, sinr: 18, ho_rate: 0.95, coverage: 0.98, cell_status: 'active' },
      { zone_id: 78, zone: 'Zone_78', cluster_id: 78, rsrp: -78, sinr: 16, ho_rate: 0.93, coverage: 0.96, cell_status: 'active' },
      { zone_id: 79, zone: 'Zone_79', cluster_id: 79, rsrp: -72, sinr: 19, ho_rate: 0.96, coverage: 0.99, cell_status: 'active' },
      { zone_id: 80, zone: 'Zone_80', cluster_id: 80, rsrp: -80, sinr: 15, ho_rate: 0.91, coverage: 0.94, cell_status: 'active' },
      { zone_id: 81, zone: 'Zone_81', cluster_id: 81, rsrp: -77, sinr: 17, ho_rate: 0.94, coverage: 0.97, cell_status: 'active' },
      { zone_id: 82, zone: 'Zone_82', cluster_id: 82, rsrp: -74, sinr: 18, ho_rate: 0.95, coverage: 0.98, cell_status: 'active' },
      { zone_id: 83, zone: 'Zone_83', cluster_id: 83, rsrp: -76, sinr: 16, ho_rate: 0.92, coverage: 0.95, cell_status: 'active' },
      { zone_id: 84, zone: 'Zone_84', cluster_id: 84, rsrp: -79, sinr: 15, ho_rate: 0.90, coverage: 0.93, cell_status: 'active' },
      { zone_id: 85, zone: 'Zone_85', cluster_id: 85, rsrp: -73, sinr: 19, ho_rate: 0.97, coverage: 0.99, cell_status: 'active' }
    ];
    
    this.dashboardCells = zoneData;
  }
}
