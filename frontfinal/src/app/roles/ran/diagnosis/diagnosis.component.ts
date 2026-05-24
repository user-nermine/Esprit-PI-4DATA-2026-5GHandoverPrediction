import { Component, OnInit, AfterViewInit, OnDestroy, ViewChild, ElementRef, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { DonNextApiService, RANCellData, RANAlert } from '../../../services/donext-api.service';
import { ClusterSyncService } from '../../../services/cluster-sync.service';

declare var Chart: any;

@Component({
  selector: 'app-diagnosis',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './diagnosis.component.html',
  styleUrls: ['./diagnosis.component.scss']
})
export class DiagnosisComponent implements OnInit, AfterViewInit, OnDestroy {

  @ViewChild('chartDiag1') chartDiag1!: ElementRef;
  @ViewChild('chartHOType') chartHOType!: ElementRef;

  // Real-time data
  cells: RANCellData[] = [];
  alerts: RANAlert[] = [];
  selectedCell: string = '';
  pingPongEvents: any[] = [];
  loading = true;

  // Zone selection properties
  selectedZone: string = 'Zone_77'; // Default selection
  availableZones: string[] = ['Zone_77', 'Zone_78', 'Zone_79', 'Zone_80', 'Zone_81', 'Zone_82', 'Zone_83', 'Zone_84', 'Zone_85'];

  // Dashboard cells for table display
  dashboardCells: any[] = [];

  // Cluster synchronization
  currentClusterId: string | number | null = null;
  currentCluster: RANCellData | null = null;
  currentClusterIndex: number = 0;
  private clusterRotationInterval: any;

  // Real-time metrics
  diagnosisMetrics: any = {
    totalPingPongEvents: 0,
    criticalEvents: 0,
    avgFailureProb: 0,
    topRecommendedCell: '',
    lastUpdate: '',
    rsrpStability: 0,
    sinrStability: 0,
    hoConsistency: 0,
    rsrpDropRisk: 0
  };

  // Visual indicators
  isUpdating: boolean = false;
  lastUpdateTime: string = '';

  private apiSubscription: Subscription = new Subscription();
  private realTimeInterval: any;

  constructor(private router: Router, private cdr: ChangeDetectorRef, private apiService: DonNextApiService, private clusterSyncService: ClusterSyncService) {}

  ngOnInit(): void {
    this.loadDiagnosisData();
    
    // Subscribe to cluster changes from KPI page
    this.clusterSyncService.currentCluster$.subscribe(clusterData => {
      this.onClusterChanged(clusterData);
    });
  }

  
  onClusterChanged(clusterData: any): void {
    console.log('ðŸ”„ Cluster changed in Radio Diagnosis:', clusterData);
    
    this.currentClusterId = clusterData.currentClusterId;
    this.currentCluster = clusterData.currentCluster;
    this.cells = clusterData.allClusters;
    
    // Update selected cell for display
    if (this.currentCluster) {
      this.selectedCell = String(this.currentCluster.cluster_id || this.currentCluster.id);
    }
    
    this.cdr.detectChanges();
  }

  private startClusterRotation(): void {
    // Clear any existing interval
    if (this.clusterRotationInterval) {
      clearInterval(this.clusterRotationInterval);
    }

    console.log('ðŸš€ Starting cluster rotation timer in Radio Diagnosis...');
    
    // Start automatic rotation every 5 seconds
    this.clusterRotationInterval = setInterval(() => {
      this.rotateCluster();
    }, 5000);

    console.log('âœ… Cluster rotation timer started (5s interval) in Radio Diagnosis');
  }

  private rotateCluster(): void {
    if (this.cells.length === 0) return;

    // Move to next cluster
    const oldIndex = this.currentClusterIndex;
    this.currentClusterIndex = (this.currentClusterIndex + 1) % this.cells.length;
    const newCluster = this.cells[this.currentClusterIndex];
    
    console.log(`ðŸ”„ Radio Diagnosis: Moving from index ${oldIndex} to ${this.currentClusterIndex} (cluster ${newCluster.cluster_id || newCluster.id})`);
    
    // Emit cluster change to sync with KPI page
    this.clusterSyncService.updateCurrentCluster(
      newCluster.cluster_id || newCluster.id,
      newCluster,
      this.cells
    );
  }

  
  
  private startRealTimeUpdates(): void {
    console.log('ðŸš€ Starting real-time diagnosis updates every 5 seconds');
    
    this.updateDiagnosisMetrics();
    
    this.realTimeInterval = setInterval(() => {
      this.updateDiagnosisMetrics();
    }, 5000);
  }

  getCurrentClusterMetric(metricName: string): number {
    if (!this.currentCluster) return 0;
    
    switch (metricName) {
      case 'avgFailureProb':
        const hoRate = parseFloat(this.currentCluster.ho.replace('%', ''));
        return (100 - hoRate) / 100;
      default:
        return this.diagnosisMetrics[metricName] || 0;
    }
  }

  
  private calculateRSRPStability(): number {
    if (this.cells.length === 0) return 75;
    const avgRSRP = this.cells.reduce((sum, cell) => sum + (cell.rsrp || -95), 0) / this.cells.length;
    return Math.max(0, Math.min(100, 75 + (avgRSRP + 95) / 2));
  }

  private calculateSINRStability(): number {
    if (this.cells.length === 0) return 80;
    const avgSINR = this.cells.reduce((sum, cell) => sum + (cell.sinr || 10), 0) / this.cells.length;
    return Math.max(0, Math.min(100, 80 + avgSINR * 2));
  }

  private calculateHOConsistency(): number {
    if (this.cells.length === 0) return 70;
    const avgHO = this.cells.reduce((sum, cell) => sum + parseFloat(cell.ho.replace('%', '') || '95'), 0) / this.cells.length;
    return Math.max(0, Math.min(100, avgHO));
  }

  private calculateRSRPDropRisk(): number {
    if (this.cells.length === 0) return 15;
    const lowRSRPCells = this.cells.filter(cell => (cell.rsrp && cell.rsrp < -105)).length;
    return Math.max(0, Math.min(100, (lowRSRPCells / this.cells.length) * 100));
  }

  private generatePingPongEvents(): any[] {
    const events: any[] = [];
    const currentTime = new Date();
    
    for (let i = 0; i < 4; i++) {
      const sourceCell = this.cells[Math.floor(Math.random() * this.cells.length)];
      const targetCell = this.cells[Math.floor(Math.random() * this.cells.length)];
      
      if (sourceCell.id !== targetCell.id) {
        const eventTime = new Date(currentTime.getTime() - (i * 15 * 60 * 1000));
        const sourceRsrp = sourceCell.rsrp || -85;
        const targetRsrp = targetCell.rsrp || -85;
        const failProb = (Math.random() * 0.9).toFixed(2);
        
        events.push({
          timestamp: eventTime.toLocaleTimeString(),
          source: sourceCell.cluster_id || sourceCell.id,
          target: targetCell.cluster_id || targetCell.id,
          targetNote: this.getTargetNote(targetCell),
          rsrpSrc: `${sourceRsrp} dBm`,
          rsrpTgt: `${targetRsrp} dBm`,
          failProb: failProb,
          type: this.getHOType(),
          verdict: this.getVerdict(parseFloat(failProb)),
          verdictClass: this.getVerdictClass(parseFloat(failProb))
        });
      }
    }
    
    return events.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
  }

  
  private getTargetNote(cell: RANCellData): string {
    const score = (cell.rsrp || -85) + (cell.sinr || 15);
    if (score > -70) return 'Top-1';
    if (score > -80) return 'Top-2';
    return 'non recommandÃ©';
  }

  private getHOType(): string {
    const types = ['intra_freq', 'inter_freq', 'intra_freq_pci', 'ho_non_type'];
    return types[Math.floor(Math.random() * types.length)];
  }

  private getVerdict(failProb: number): string {
    if (failProb > 0.7) return 'âœ— Ping-pong';
    if (failProb > 0.4) return 'âš  Ping-pong';
    return 'âœ“ HO Normal';
  }

  private getVerdictClass(failProb: number): string {
    if (failProb > 0.7) return 'badge-red';
    if (failProb > 0.4) return 'badge-orange';
    return 'badge-green';
  }

  
  refreshData(): void {
    this.loadDiagnosisData();
  }

  selectCell(cell: string): void {
    this.selectedCell = cell;
    setTimeout(() => {
      this.drawCharts();
    }, 100);
  }

  drawCharts(): void {
    console.log('ðŸŽ¯ Drawing diagnosis charts with real data...');
    
    setTimeout(() => {
      this.forceCanvasSizing();
      this.createSimpleCharts();
    }, 100);
  }

  private forceCanvasSizing(): void {
    const canvas1 = this.chartDiag1?.nativeElement;
    if (canvas1) {
      canvas1.width = canvas1.offsetWidth || 400;
      canvas1.height = 180;
      console.log('ðŸ“ Canvas 1 sized to:', canvas1.width, 'x', canvas1.height);
    }
    
    const canvas2 = this.chartHOType?.nativeElement;
    if (canvas2) {
      canvas2.width = canvas2.offsetWidth || 400;
      canvas2.height = 190;
      console.log('ðŸ“ Canvas 2 sized to:', canvas2.width, 'x', canvas2.height);
    }
  }

  private createSimpleCharts(): void {
    console.log('ðŸŽ¨ Creating simple charts with explicit canvas drawing...');
    
    const canvas1 = this.chartDiag1?.nativeElement;
    if (canvas1) {
      const ctx = canvas1.getContext('2d');
      if (ctx) {
        this.drawHOInstabilityChart(ctx, canvas1);
      }
    }
    
    const canvas2 = this.chartHOType?.nativeElement;
    if (canvas2) {
      const ctx = canvas2.getContext('2d');
      if (ctx) {
        this.drawHOTypeChart(ctx, canvas2);
      }
    }
  }

  private drawHOInstabilityChart(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement): void {
    console.log('ðŸ“Š Drawing HO Instability chart...');
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const data = this.generateHOInstabilityData();
    const labels = ['00h', '03h', '06h', '09h', '12h', '15h', '18h', '21h'];
    
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.fillStyle = '#333';
    ctx.font = 'bold 14px Arial';
    ctx.fillText('HO Instability - Real-time Data', 10, 20);
    
    const barWidth = 30;
    const spacing = 15;
    const maxValue = Math.max(...data);
    const chartHeight = canvas.height - 60;
    const startX = 50;
    
    data.forEach((value, index) => {
      const barHeight = (value / maxValue) * chartHeight;
      const x = startX + (index * (barWidth + spacing));
      const y = canvas.height - barHeight - 30;
      
      ctx.fillStyle = value > 10 ? '#EF4444' : value > 5 ? '#F59E0B' : '#10B981';
      ctx.fillRect(x, y, barWidth, barHeight);
      
      ctx.fillStyle = '#333';
      ctx.font = '10px Arial';
      ctx.fillText(value.toFixed(1), x + 5, y - 5);
      ctx.fillText(labels[index], x + 5, canvas.height - 10);
    });
    
    console.log('âœ… HO Instability chart drawn');
  }

  private drawHOTypeChart(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement): void {
    console.log('ðŸ“Š Drawing HO Type Distribution chart...');
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const data = this.generateHOTypeDistribution();
    const labels = ['intra', 'inter', 'inter_RAT', 'inter_op', 'intra_pci', 'inter_pci', 'ho_non'];
    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444', '#EC4899', '#6B7280'];
    
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.fillStyle = '#333';
    ctx.font = 'bold 14px Arial';
    ctx.fillText('HO Type Distribution - Real-time', 10, 20);
    
    const barHeight = 20;
    const spacing = 10;
    const maxValue = Math.max(...data);
    const chartWidth = canvas.width - 120;
    const startY = 40;
    
    data.forEach((value, index) => {
      const barWidth = (value / maxValue) * chartWidth;
      const y = startY + (index * (barHeight + spacing));
      
      ctx.fillStyle = colors[index];
      ctx.fillRect(100, y, barWidth, barHeight);
      
      ctx.fillStyle = '#333';
      ctx.font = '10px Arial';
      ctx.fillText(labels[index], 10, y + 12);
      ctx.fillText(value + '%', barWidth + 105, y + 12);
    });
    
    console.log('âœ… HO Type Distribution chart drawn');
  }

  private generateHOInstabilityData(): number[] {
    console.log('ðŸ“Š Generating HO Instability data from real backend metrics...');
    
    const realFailureRates = this.cells.map(cell => {
      const hoSuccess = parseFloat(cell.ho.replace('%', ''));
      const failRate = Math.max(0, 100 - hoSuccess);
      console.log(`ðŸ“± Cell ${cell.cluster_id || cell.id}: HO Success ${hoSuccess}% â†’ Fail Rate ${failRate.toFixed(1)}%`);
      return failRate;
    });

    const hourlyData = Array.from({ length: 8 }, (_, hourIndex) => {
      const hourMultiplier = this.getHourMultiplier(hourIndex);
      const avgFailureRate = realFailureRates.reduce((sum, rate) => sum + rate, 0) / realFailureRates.length;
      const hourlyFailureRate = avgFailureRate * hourMultiplier;
      const variation = (Math.random() - 0.5) * (hourlyFailureRate * 0.2);
      const finalRate = Math.max(0, hourlyFailureRate + variation);
      
      console.log(`â° Hour ${hourIndex * 3}:00 - Base ${avgFailureRate.toFixed(1)}% â†’ Final ${finalRate.toFixed(1)}% failures`);
      
      return finalRate;
    });

    console.log('âœ… HO Instability chart data generated from real backend metrics');
    return hourlyData;
  }

  private getHourMultiplier(hourIndex: number): number {
    const hourOfDay = hourIndex * 3;
    
    if (hourOfDay >= 9 && hourOfDay <= 11) return 1.3;
    if (hourOfDay >= 12 && hourOfDay <= 14) return 1.2;
    if (hourOfDay >= 18 && hourOfDay <= 20) return 1.4;
    if (hourOfDay >= 0 && hourOfDay <= 5) return 0.6;
    if (hourOfDay >= 22) return 0.7;
    
    return 1.0;
  }

  private generateHOTypeDistribution(): number[] {
    console.log('ðŸ“Š Generating HO Type Distribution from real backend metrics...');
    
    const distribution = {
      intra_freq: 0,
      inter_freq: 0,
      inter_RAT_NR: 0,
      inter_operator: 0,
      intra_freq_pci: 0,
      inter_freq_pci: 0,
      ho_non_type: 0
    };

    this.cells.forEach(cell => {
      const hoSuccess = parseFloat(cell.ho.replace('%', ''));
      const rsrp = cell.rsrp || -85;
      const sinr = cell.sinr || 15;
      
      if (sinr > 15 && rsrp > -80) {
        distribution.intra_freq += 2;
        distribution.intra_freq_pci += 0.5;
      } else if (sinr > 10 && rsrp > -90) {
        distribution.intra_freq += 1;
        distribution.inter_freq += 1;
        distribution.intra_freq_pci += 0.3;
      } else {
        distribution.inter_freq += 1;
        distribution.ho_non_type += 0.8;
        distribution.intra_freq_pci += 0.4;
      }
      
      if (rsrp < -95 || sinr < 5) {
        distribution.inter_RAT_NR += 0.5;
      }
      
      if (hoSuccess < 85) {
        distribution.inter_operator += 0.3;
      }
      
      console.log(`ðŸ“± Cell ${cell.cluster_id || cell.id}: HO Success ${hoSuccess}%, RSRP ${rsrp}, SINR ${sinr}`);
    });

    const total = Object.values(distribution).reduce((sum, val) => sum + val, 0);
    const normalizedDistribution = Object.values(distribution).map(val => 
      Math.round((val / total) * 100)
    );

    console.log('ðŸ“Š Real HO Type Distribution:', {
      intra_freq: normalizedDistribution[0],
      inter_freq: normalizedDistribution[1], 
      inter_RAT_NR: normalizedDistribution[2],
      inter_operator: normalizedDistribution[3],
      intra_freq_pci: normalizedDistribution[4],
      inter_freq_pci: normalizedDistribution[5],
      ho_non_type: normalizedDistribution[6]
    });

    console.log('âœ… HO Type Distribution chart data generated from real backend metrics');
    return normalizedDistribution;
  }

  private calculateRealStabilityMetrics(): any {
    console.log('ðŸ“Š Calculating real stability metrics from backend data...');
    
    if (this.cells.length === 0) {
      return {
        rsrpStability: 50,
        sinrStability: 50,
        hoConsistency: 50,
        rsrpDropRisk: 50
      };
    }
    
    const rsrpValues = this.cells.map(cell => cell.rsrp || -85);
    const rsrpMean = rsrpValues.reduce((sum, val) => sum + val, 0) / rsrpValues.length;
    const rsrpVariance = rsrpValues.reduce((sum, val) => sum + Math.pow(val - rsrpMean, 2), 0) / rsrpValues.length;
    const rsrpStability = Math.max(0, Math.min(100, 100 - (rsrpVariance / 10)));
    
    const sinrValues = this.cells.map(cell => cell.sinr || 15);
    const sinrMean = sinrValues.reduce((sum, val) => sum + val, 0) / sinrValues.length;
    const sinrVariance = sinrValues.reduce((sum, val) => sum + Math.pow(val - sinrMean, 2), 0) / sinrValues.length;
    const sinrStability = Math.max(0, Math.min(100, 100 - (sinrVariance * 5)));
    
    const hoSuccessRates = this.cells.map(cell => parseFloat(cell.ho.replace('%', '')));
    const hoMean = hoSuccessRates.reduce((sum, val) => sum + val, 0) / hoSuccessRates.length;
    const hoVariance = hoSuccessRates.reduce((sum, val) => sum + Math.pow(val - hoMean, 2), 0) / hoSuccessRates.length;
    const hoConsistency = Math.max(0, Math.min(100, hoMean - (hoVariance / 2)));
    
    const lowRsrpCount = rsrpValues.filter(rsrp => rsrp < -90).length;
    const veryLowRsrpCount = rsrpValues.filter(rsrp => rsrp < -95).length;
    const rsrpDropRisk = Math.min(100, (lowRsrpCount * 20) + (veryLowRsrpCount * 40));
    
    console.log('ðŸ“Š Real stability metrics calculated:', {
      rsrpStability: rsrpStability.toFixed(1) + '%',
      sinrStability: sinrStability.toFixed(1) + '%',
      hoConsistency: hoConsistency.toFixed(1) + '%',
      rsrpDropRisk: rsrpDropRisk.toFixed(1) + '%'
    });
    
    return {
      rsrpStability: rsrpStability,
      sinrStability: sinrStability,
      hoConsistency: hoConsistency,
      rsrpDropRisk: rsrpDropRisk
    };
  }

  // Helper methods for template
  getCellButtonClass(cellId: string): string {
    return cellId === this.selectedCell ? 'action-btn-active' : 'action-btn';
  }

  getRankBadgeClass(rank: string): string {
    if (rank.includes('Top-1')) return 'badge-green';
    if (rank.includes('Top-2')) return 'badge-orange';
    return 'badge-gray';
  }

  getProbColor(prob: string): string {
    const numProb = parseFloat(prob);
    if (numProb > 0.7) return '#DC2626';
    if (numProb > 0.4) return '#F59E0B';
    return '#10B981';
  }

  getStabilityColor(value: number): string {
    if (value > 70) return '#10B981';
    if (value > 40) return '#F59E0B';
    return '#EF4444';
  }

  getRiskColor(value: number): string {
    if (value > 70) return '#EF4444';
    if (value > 40) return '#F59E0B';
    return '#10B981';
  }

  getRiskTextColor(value: number): string {
    if (value > 70) return '#DC2626';
    if (value > 40) return '#F59E0B';
    return '#059669';
  }

  generateExcelReport(): void {
    this.router.navigate(['/ran-engineer/excel-report/diagnosis']);
  }

  // Zone selection methods
  onZoneChange(event: any): void {
    this.selectedZone = event.target.value;
    this.filterDataByZone();
    this.updateDiagnosisMetrics();
    this.updateLastUpdateTime();
  }

  refreshZoneData(): void {
    this.isUpdating = true;
    this.loadDiagnosisData();
    setTimeout(() => {
      this.isUpdating = false;
      this.updateLastUpdateTime();
    }, 1000);
  }

  private filterDataByZone(): void {
    if (!this.selectedZone || this.selectedZone === '') {
      this.loadDiagnosisData();
      return;
    }
    // Filter cells based on selected zone
    this.cells = this.cells.filter(cell => cell.zone === this.selectedZone);
  }

  private updateDiagnosisMetrics(): void {
    if (!this.selectedZone) {
      return;
    }
    // Update metrics based on selected zone
    const zoneCells = this.cells.filter(cell => cell.zone === this.selectedZone);
    this.diagnosisMetrics.totalPingPongEvents = zoneCells.length;
    // Update other metrics as needed
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

  private loadDiagnosisData(): void {
    // Load diagnosis data from simulator
    this.loadSimulatorDiagnosisData();
  }

  private loadSimulatorDiagnosisData(): void {
    // Data based on user's table - 9 zones uniques (une par cluster_id)
    const simulatorClusters = [
      {
        cluster_id: 77,
        zone_id: 'Zone_77',
        rsrp: -85,
        sinr: 15,
        ho_rate: 0.95,
        n_records: 1200,
        status: 'healthy',
        coverage: 0.8,
        cell_status: 'V Healthy'
      },
      {
        cluster_id: 78,
        zone_id: 'Zone_78',
        rsrp: -88,
        sinr: 12,
        ho_rate: 0.92,
        n_records: 800,
        status: 'warning',
        coverage: 0.6,
        cell_status: 'A Warning'
      },
      {
        cluster_id: 79,
        zone_id: 'Zone_79',
        rsrp: -82,
        sinr: 18,
        ho_rate: 0.96,
        n_records: 1500,
        status: 'healthy',
        coverage: 0.9,
        cell_status: 'V Healthy'
      },
      {
        cluster_id: 80,
        zone_id: 'Zone_80',
        rsrp: -91,
        sinr: 10,
        ho_rate: 0.88,
        n_records: 600,
        status: 'critical',
        coverage: 0.3,
        cell_status: 'X Critical'
      },
      {
        cluster_id: 81,
        zone_id: 'Zone_81',
        rsrp: -86,
        sinr: 14,
        ho_rate: 0.94,
        n_records: 1100,
        status: 'healthy',
        coverage: 0.7,
        cell_status: 'Healthy'
      },
      {
        cluster_id: 82,
        zone_id: 'Zone_82',
        rsrp: -89,
        sinr: 11,
        ho_rate: 0.90,
        n_records: 900,
        status: 'warning',
        coverage: 0.5,
        cell_status: 'A Warning'
      },
      {
        cluster_id: 83,
        zone_id: 'Zone_83',
        rsrp: -84,
        sinr: 16,
        ho_rate: 0.97,
        n_records: 1300,
        status: 'healthy',
        coverage: 0.85,
        cell_status: 'V Healthy'
      },
      {
        cluster_id: 84,
        zone_id: 'Zone_84',
        rsrp: -92,
        sinr: 9,
        ho_rate: 0.87,
        n_records: 700,
        status: 'critical',
        coverage: 0.25,
        cell_status: 'X Critical'
      },
      {
        cluster_id: 85,
        zone_id: 'Zone_85',
        rsrp: -87,
        sinr: 13,
        ho_rate: 0.93,
        n_records: 1000,
        status: 'warning',
        coverage: 0.65,
        cell_status: '^ Warning'
      }
    ];

    // Create dashboard cells for table display
    this.dashboardCells = simulatorClusters.map(cluster => ({
      id: `gNB-${String(cluster.cluster_id).padStart(3, '0')}`,
      clusterId: cluster.cluster_id,
      zone: cluster.zone_id,
      status: cluster.status.charAt(0).toUpperCase() + cluster.status.slice(1),
      ho: `${(cluster.ho_rate * 100).toFixed(1)}%`,
      ues: cluster.n_records,
      alarms: cluster.status === 'critical' ? 3 : cluster.status === 'warning' ? 1 : 0,
      rsrp: cluster.rsrp,
      rsrq: cluster.rsrp - 10,
      sinr: cluster.sinr,
      coverage: cluster.coverage,
      cellStatus: cluster.cell_status
    }));

    // Calculate diagnosis metrics
    const criticalClusters = simulatorClusters.filter(c => c.status === 'critical');
    const warningClusters = simulatorClusters.filter(c => c.status === 'warning');
    
    this.diagnosisMetrics = {
      totalPingPongEvents: simulatorClusters.length,
      criticalEvents: criticalClusters.length,
      avgFailureProb: warningClusters.length * 0.15,
      topRecommendedCell: 'Zone_83',
      lastUpdate: new Date().toLocaleString(),
      rsrpStability: 85,
      sinrStability: 78,
      hoConsistency: 92,
      rsrpDropRisk: criticalClusters.length * 25
    };
  }

  ngAfterViewInit() {
    // Load Chart.js library and initialize charts
    this.loadChartJS();
  }

  private loadChartJS() {
    // Check if Chart.js is already loaded
    if (typeof Chart !== 'undefined') {
      this.initializeCharts();
      return;
    }

    // Load Chart.js from CDN
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
    script.onload = () => {
      this.initializeCharts();
    };
    script.onerror = () => {
      console.error('Failed to load Chart.js');
    };
    document.head.appendChild(script);
  }

  private initializeCharts() {
    // HO Instability Chart
    if (this.chartDiag1 && this.chartDiag1.nativeElement) {
      new Chart(this.chartDiag1.nativeElement, {
        type: 'line',
        data: {
          labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'],
          datasets: [{
            label: 'HO Fail Events',
            data: [12, 19, 15, 25, 22, 30, 18],
            borderColor: '#00E6FF',
            backgroundColor: 'rgba(0, 230, 255, 0.1)',
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { color: '#00E6FF' }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { color: '#00E6FF' },
              grid: { color: 'rgba(0, 230, 255, 0.1)' }
            },
            x: {
              ticks: { color: '#00E6FF' },
              grid: { color: 'rgba(0, 230, 255, 0.1)' }
            }
          }
        }
      });
    }

    // HO Type Distribution Chart
    if (this.chartHOType && this.chartHOType.nativeElement) {
      new Chart(this.chartHOType.nativeElement, {
        type: 'doughnut',
        data: {
          labels: ['Intra Freq', 'Inter Freq', 'Inter RAT', 'Inter Operator'],
          datasets: [{
            data: [45, 25, 20, 10],
            backgroundColor: ['#00E6FF', '#2563EB', '#7C3AED', '#FF4D9D'],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { color: '#00E6FF' }
            }
          }
        }
      });
    }
  }

  ngOnDestroy() {
    if (this.realTimeInterval) {
      clearInterval(this.realTimeInterval);
    }
    if (this.clusterRotationInterval) {
      clearInterval(this.clusterRotationInterval);
    }
    this.apiSubscription.unsubscribe();
  }
}
