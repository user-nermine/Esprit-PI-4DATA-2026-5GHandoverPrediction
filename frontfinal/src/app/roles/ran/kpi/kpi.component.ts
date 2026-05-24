import { Component, OnInit, AfterViewInit, OnDestroy, ViewChild, ElementRef, ChangeDetectorRef } from '@angular/core';
import { RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { DonNextApiService, RANKPI, RANCellData } from '../../../services/donext-api.service';
import { ClusterSyncService } from '../../../services/cluster-sync.service';
import { ClusterDataService, DashboardCell, DashboardKPI } from '../../../services/cluster-data.service';
import { HttpClient } from '@angular/common/http';
import { MonitoringService } from '../../../services/monitoring.service';
import { PredictionService } from '../../../services/prediction.service';
import { ExplainabilityService } from '../../../services/explainability.service';
declare const Chart: any;

@Component({
  selector: 'app-kpi',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './kpi.component.html',
  styleUrls: ['./kpi.component.scss']
})
export class KpiComponent implements OnInit, AfterViewInit, OnDestroy {

  @ViewChild('chartKPI1') chartKPI1!: ElementRef;
  @ViewChild('chartKPI2') chartKPI2!: ElementRef;

  metrics: RANKPI | null = null;
  cells: RANCellData[] = [];
  loading = true;
  lastUpdate: Date = new Date();

  // Visual indicators
  isUpdating: boolean = false;
  lastUpdateTime: string = '';
  currentClusters: string[] = [];
  currentClusterIndex: number = 0;
  

  // Real-time metrics for current cluster
  currentClusterMetrics: any = {
    clusterId: '',
    totalZones: 0,
    avgRsrp: 0,
    avgSinr: 0,
    activeCells: 0,
    healthyCells: 0,
    lastUpdate: ''
  };

  // Real radio KPI data from simulator
  realRadioData: any[] = [];
  radioSummary: any = {};
  clusterCategories: any[] = [];
  totalClusters: number = 0;

  // Zone selection properties
  selectedZone: string = 'Zone_77'; // Default selection
 availableZones: string[] = [];
  // Cluster data
  dashboardCells: DashboardCell[] = [];
  dashboardKPIs: DashboardKPI[] = [];

  private charts: any[] = [];
  private apiSubscription: Subscription = new Subscription();
  private clusterRotationInterval: any;

  constructor(
    private router: Router,
    private cdr: ChangeDetectorRef,
    private donNextApiService: DonNextApiService,
    private clusterSyncService: ClusterSyncService,
    private clusterDataService: ClusterDataService,
    private http: HttpClient,
    private monitoringService: MonitoringService,
    private predictionService: PredictionService,
    private explainabilityService: ExplainabilityService
  ) { }

  ngOnInit(): void {

  this.loadKpiData();

  setInterval(() => {

    this.loadKpiData();

  }, 5000);

}

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.drawCharts();
    }, 1000);
  }

  ngOnDestroy(): void {
    this.apiSubscription.unsubscribe();
    this.destroyCharts();
    if (this.clusterRotationInterval) {
      clearInterval(this.clusterRotationInterval);
    }
  }

  

  loadKpiData(): void {
    this.loading = true;
    this.monitoringService.getRealtimeMetrics().subscribe({
      next: (data: any) => {
        // Handle both array response and wrapped {metrics: [...]} response
        const items: any[] = Array.isArray(data) ? data : (data?.metrics || data?.data || []);
        if (items.length > 0) {
          this.cells = items.map((item: any) => ({
            id: item.cluster_id,
            cluster_id: item.cluster_id,
            zone: item.zone_id || `Zone_${item.cluster_id}`,
            rsrp: item.rsrp ?? (item.cpu_usage ? -80 - item.cpu_usage * 0.3 : -85),
            rsrq: item.rsrq ?? -10,
            sinr: item.sinr ?? (item.availability ? item.availability * 0.25 - 10 : 12),
            ues: item.connected_users || item.active_connections || 0,
            ho: `${Math.round((item.handover_success_rate || 0.95) * 100)}%`,
            status: (item.rsrp ?? -85) < -110 || (item.sinr ?? 12) < 0
              ? 'Critical'
              : (item.rsrp ?? -85) < -95
              ? 'Warning'
              : 'Healthy',
            th: item.dso_score || '0.7',
            alarms: item.alerts_count || 0
          }));
        } else {
          this.useFallbackCells();
        }
        this.loading = false;
        this.updateLastUpdateTime();
        this.availableZones = [...new Set(this.cells.map((c: any) => c.zone))];
        this.drawCharts();
      },
      error: () => {
        this.useFallbackCells();
        this.loading = false;
        this.updateLastUpdateTime();
        this.availableZones = [...new Set(this.cells.map((c: any) => c.zone))];
        this.drawCharts();
      }
    });
  }

  private useFallbackCells(): void {
    const zones = ['Zone_77', 'Zone_78', 'Zone_79', 'Zone_80', 'Zone_81'];
    this.cells = zones.map((zone, i) => {
      const rsrp = -80 - Math.random() * 30;
      const sinr = 5 + Math.random() * 20;
      return {
        id: String(77 + i),
        cluster_id: 77 + i,
        zone,
        rsrp: Math.round(rsrp * 10) / 10,
        rsrq: Math.round((-8 - Math.random() * 10) * 10) / 10,
        sinr: Math.round(sinr * 10) / 10,
        ues: Math.floor(100 + Math.random() * 500),
        ho: `${Math.round(90 + Math.random() * 9)}%`,
        status: rsrp < -110 || sinr < 0 ? 'Critical' : rsrp < -95 ? 'Warning' : 'Healthy',
        th: (0.6 + Math.random() * 0.35).toFixed(2),
        alarms: Math.floor(Math.random() * 3)
      };
    });
  }

  private loadCellData(): void {
    // Static data already loaded in loadKpiData()
  }

  private loadClusterCategories(): void {

    this.http.get('http://127.0.0.1:8004/api/v1/radio/clusters/categories')
      .subscribe({
        next: (response: any) => {
          this.clusterCategories = response.categories;
        },
        error: (error) => {
          console.log('Using static cluster categories from simulator');
        }
      });
  }

  private drawCharts(): void {
    if (!this.chartKPI1 || !this.chartKPI2 || !this.cells.length) {
      return;
    }

    if (typeof Chart === 'undefined') {
      this.loadChartJS();
      return;
    }

    this.destroyCharts();

    const clusterIds = this.cells.map((cell: any) => String(cell.cluster_id || cell.id));
    this.currentClusters = clusterIds;

    // Get current cluster data
    const currentClusterId = this.currentClusterMetrics.clusterId || clusterIds[0];
    const currentCluster = this.cells.find(cell => 
      String(cell.cluster_id || cell.id) === String(currentClusterId)
    );

    if (!currentCluster) return;

    // Chart 1: Current Cluster Performance
    const canvas1 = this.chartKPI1.nativeElement;
    const chart1 = new Chart(canvas1, {
      type: 'bar',
      data: {
        labels: ['Current Cluster'],
        datasets: [{
          label: 'HO Success Rate (%)',
          data: [parseFloat(currentCluster.ho.replace('%', ''))],
          backgroundColor: this.getClusterColor(0, 0.6),
          borderColor: this.getClusterColor(0),
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, position: 'bottom' },
          title: { display: true, text: `Zone ${currentClusterId} Performance` },
          tooltip: {
            callbacks: {
              label: (context: any) => {
                return `Success Rate: ${context.parsed.y.toFixed(1)}%`;
              }
            }
          }
        },
        scales: {
          x: { title: { display: true, text: 'Current Zone' } },
          y: { title: { display: true, text: 'Success Rate (%)' }, min: 0, max: 100 }
        }
      }
    });

    // Chart 2: RSRP Drop Analysis
    const canvas2 = this.chartKPI2.nativeElement;
    const rsrpDropData = this.generateRSRPDropData(currentCluster);
    const chart2 = new Chart(canvas2, {
      type: 'line',
      data: {
        labels: rsrpDropData.labels,
        datasets: [{
          label: 'RSRP Drop (dBm)',
          data: rsrpDropData.values,
          borderColor: '#EF4444',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, position: 'bottom' },
          title: { display: true, text: `RSRP Drop - Zone ${currentClusterId}` }
        },
        scales: {
          x: { title: { display: true, text: 'Time' } },
          y: { title: { display: true, text: 'RSRP Drop (dBm)' } }
        }
      }
    });

    this.charts.push(chart1);
    this.charts.push(chart2);
    
    // Initialize with first cluster but disable automatic rotation
    this.currentClusterIndex = 0;
    console.log('ðŸ“Š About to update current cluster metrics...');
    this.updateCurrentClusterMetrics();
    console.log('ðŸ“Š Automatic cluster rotation disabled - using manual zone selection');
    // this.startClusterRotation(); // Disabled - using manual zone selection instead
  }

  private loadChartJS(): void {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
    script.onload = () => {
      setTimeout(() => this.drawCharts(), 1000);
    };
    document.head.appendChild(script);
  }

  private destroyCharts(): void {
    this.charts.forEach(chart => {
      if (chart) chart.destroy();
    });
    this.charts = [];
  }

  private getHandoverType(probability: number): string {
    if (probability < 10) return 'Low';
    if (probability < 30) return 'Medium';
    return 'High';
  }

  private getClusterColor(index: number, alpha: number = 1): string {
    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];
    const color = colors[index % colors.length];
    return alpha < 1 ? this.hexToRgba(color, alpha) : color;
  }

  private hexToRgba(hex: string, alpha: number): string {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  private updateCurrentClusterMetrics(): void {
    if (this.cells.length === 0) return;

    const currentCell = this.cells[this.currentClusterIndex];

    this.currentClusterMetrics = {
      clusterId: currentCell.cluster_id || currentCell.id,
      totalZones: 4,
      avgRsrp: currentCell.rsrp || -85,
      avgSinr: currentCell.sinr || 15,
      activeCells: this.cells.length,
      healthyCells: this.cells.filter(c => c.status === 'Healthy').length,
      lastUpdate: new Date().toLocaleTimeString()
    };

    this.currentClusters = [String(this.currentClusterMetrics.clusterId)];
    
    // Emit current cluster change to synchronize with Anomaly Detection page
    this.clusterSyncService.updateCurrentCluster(
      this.currentClusterMetrics.clusterId,
      currentCell,
      this.cells
    );
    
    this.cdr.detectChanges();
  }

  private startClusterRotation(): void {
    // Clear any existing interval
    if (this.clusterRotationInterval) {
      clearInterval(this.clusterRotationInterval);
    }

    console.log('ðŸš€ Starting cluster rotation timer...');
    console.log(`ðŸ“Š Available clusters: ${this.cells.length}`);
    console.log(`ðŸ“‹ Cluster IDs:`, this.cells.map(c => c.cluster_id || c.id));

    // Start automatic rotation every 5 seconds
    this.clusterRotationInterval = setInterval(() => {
      console.log('â° Timer triggered - rotating cluster...');
      this.rotateCluster();
    }, 5000);

    console.log('âœ… Cluster rotation timer started (5s interval)');
  }

  private rotateCluster(): void {
    console.log(`ðŸ”„ rotateCluster called - cells.length: ${this.cells.length}, currentIndex: ${this.currentClusterIndex}`);
    
    if (this.cells.length === 0) {
      console.log('âŒ No cells available for rotation');
      return;
    }

    // Move to next cluster
    const oldIndex = this.currentClusterIndex;
    this.currentClusterIndex = (this.currentClusterIndex + 1) % this.cells.length;
    const newClusterId = this.cells[this.currentClusterIndex].cluster_id || this.cells[this.currentClusterIndex].id;
    
    console.log(`ðŸ”„ Moving from index ${oldIndex} to ${this.currentClusterIndex} (cluster ${newClusterId})`);
    
    // Update metrics for new cluster
    this.updateCurrentClusterMetrics();
    
    // Refresh charts with new cluster data
    this.refreshCharts();
    
    console.log(`âœ… Rotation completed - now showing cluster ${this.currentClusterMetrics.clusterId}`);
  }

  private refreshCharts(): void {
    if (!this.chartKPI1 || !this.chartKPI2 || !this.cells.length) return;

    const currentClusterId = this.currentClusterMetrics.clusterId;
    const currentCluster = this.cells.find(cell => 
      String(cell.cluster_id || cell.id) === String(currentClusterId)
    );

    if (!currentCluster) return;

    // Update Chart 1: Current Cluster Performance
    const chart1 = this.charts[0];
    if (chart1) {
      chart1.data.datasets[0].data = [parseFloat(currentCluster.ho.replace('%', ''))];
      chart1.options.plugins!.title!.text = `Cluster ${currentClusterId} Performance`;
      chart1.update();
    }

    // Update Chart 2: RSRP Drop Analysis
    const chart2 = this.charts[1];
    if (chart2) {
      const rsrpDropData = this.generateRSRPDropData(currentCluster);
      chart2.data.labels = rsrpDropData.labels;
      chart2.data.datasets[0].data = rsrpDropData.values;
      chart2.options.plugins!.title!.text = `RSRP Drop - Cluster ${currentClusterId}`;
      chart2.update();
    }
  }

  private generateRSRPDropData(cluster: any): { labels: string[], values: number[] } {
    const baseRSRP = cluster.rsrp || -85;
    const timeLabels = [];
    const rsrpValues = [];

    // Generate 24 hours of data with realistic RSRP drops
    for (let i = 0; i < 24; i++) {
      timeLabels.push(`${i}:00`);
      
      // Simulate RSRP variations with occasional drops
      let rsrp = baseRSRP + (Math.random() - 0.5) * 10; // Â±5dB variation
      
      // Add occasional drops (more likely for clusters with lower quality)
      if (cluster.status === 'Critical' && Math.random() < 0.3) {
        rsrp -= Math.random() * 15 + 5; // 5-20dB drop
      } else if (cluster.status === 'Warning' && Math.random() < 0.2) {
        rsrp -= Math.random() * 10 + 3; // 3-13dB drop
      } else if (cluster.status === 'Healthy' && Math.random() < 0.1) {
        rsrp -= Math.random() * 8 + 2; // 2-10dB drop
      }
      
      rsrpValues.push(Math.round(rsrp * 10) / 10);
    }

    return {
      labels: timeLabels,
      values: rsrpValues
    };
  }

  // Helper methods for template
  getColorStyle(value: string, isThreshold: boolean = false): string {
    let numValue = parseFloat(value.replace('%', ''));
    
    if (isThreshold) {
      // For threshold values (0.0-1.0 scale)
      if (numValue >= 0.8) return 'color: #10B981; font-weight: bold;';
      if (numValue >= 0.6) return 'color: #F59E0B; font-weight: bold;';
      return 'color: #EF4444; font-weight: bold;';
    } else {
      // For percentage values (HO success rate)
      if (numValue >= 95) return 'color: #10B981; font-weight: bold;';
      if (numValue >= 90) return 'color: #F59E0B; font-weight: bold;';
      return 'color: #EF4444; font-weight: bold;';
    }
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'Healthy': return 'badge-success';
      case 'Warning': return 'badge-warning';
      case 'Critical': return 'badge-danger';
      default: return 'badge-gray';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'Healthy': return 'âœ“ Healthy';
      case 'Warning': return 'âš  Warning';
      case 'Critical': return 'âœ— Critical';
      default: return status;
    }
  }

  // Helper methods for cluster categories
  getClusterCountByCategory(categoryId: number): number {
    const category = this.clusterCategories.find(cat => cat.category_id === categoryId);
    return category ? category.cluster_count : 0;
  }

  getIdentifiedClustersCount(): number {
    const lowDensity = this.clusterCategories.find(cat => cat.category_id === 0);
    const highDensity = this.clusterCategories.find(cat => cat.category_id === 1);
    return (lowDensity ? lowDensity.cluster_count : 0) + (highDensity ? highDensity.cluster_count : 0);
  }

  generatePDFReport(): void {
    this.router.navigate(['/ran-engineer/pdf-report/kpi']);
  }

  generateExcelReport(): void {
    let content = 'Cell ID,HO Count,HO Success Rate,Status\n';
    this.cells.forEach((cell: any) => {
      content += `${cell.id},${cell.ues},${cell.ho},${cell.status}\n`;
    });

    const blob = new Blob([content], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kpi-report-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  // Zone selection methods
  onZoneChange(event: any): void {
    this.selectedZone = event.target.value;
    this.filterCellsByZone();
    this.refreshCharts();
    this.updateLastUpdateTime();
  }

  refreshZoneData(): void {
    this.isUpdating = true;
    this.loadCellData();
    setTimeout(() => {
      this.isUpdating = false;
      this.updateLastUpdateTime();
    }, 1000);
  }

  private filterCellsByZone(): void {
    if (!this.selectedZone) {
      this.loadCellData();
      return;
    }
    this.cells = this.cells.filter(cell => cell.zone === this.selectedZone);
  }

  private updateLastUpdateTime(): void {
    this.lastUpdateTime = new Date().toLocaleString();
  }

  getFilteredCells(): any[] {
    if (!this.selectedZone || this.selectedZone === '') {
      return this.dashboardCells;
    }
    return this.dashboardCells.filter(cell => cell.zone === this.selectedZone);
  }

  
    


  private createKPIsFromSimulator(clusters: any[]): void {
    const avgHO = clusters.reduce((sum, c) => sum + c.ho_rate, 0) / clusters.length;
    const totalUEs = clusters.reduce((sum, c) => sum + c.n_records, 0);
    const avgRSRP = clusters.reduce((sum, c) => sum + c.rsrp, 0) / clusters.length;
    const healthyClusters = clusters.filter(c => c.status === 'healthy').length;

    this.dashboardKPIs = [
      { 
        title: 'Active Zones', 
        value: this.availableZones.length.toString(), 
        sub: `${healthyClusters} healthy`,
        trend: [3, 4, 4, 5, 4, this.availableZones.length],
        color: '#22c55e'
      },
      { 
        title: 'HO Success Rate', 
        value: `${(avgHO * 100).toFixed(1)}%`,
        sub: 'Real-time',
        trend: [94, 95, 93, 96, 97, avgHO * 100],
        color: '#3b82f6'
      },
      { 
        title: 'Avg RSRP', 
        value: `${avgRSRP.toFixed(1)} dBm`,
        sub: 'Signal strength',
        trend: [-85, -87, -83, -89, -84, avgRSRP],
        color: '#f59e0b'
      },
      { 
        title: 'Total UEs', 
        value: totalUEs.toLocaleString(),
        sub: 'Connected devices',
        trend: [8000, 8200, 8500, 8300, 8700, totalUEs],
        color: '#ef4444'
      }
    ];
  }
    }
