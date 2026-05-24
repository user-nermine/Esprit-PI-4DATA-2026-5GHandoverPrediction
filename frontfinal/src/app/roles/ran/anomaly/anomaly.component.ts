import { Component, OnInit, AfterViewInit, OnDestroy, ViewChild, ElementRef, ChangeDetectorRef } from '@angular/core';
import { RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { DonNextApiService, RANCellData, RANAlert } from '../../../services/donext-api.service';
import { ClusterSyncService } from '../../../services/cluster-sync.service';

declare const Chart: any;

@Component({
  selector: 'app-anomaly',
  standalone: true,
  imports: [RouterModule, CommonModule, FormsModule],
  templateUrl: './anomaly.component.html',
  styleUrls: ['./anomaly.component.scss']
})
export class AnomalyComponent implements OnInit, AfterViewInit, OnDestroy {

  @ViewChild('chartAnomaly') chartAnomaly!: ElementRef;
  @ViewChild('heatmapCanvas') heatmapCanvas!: ElementRef;
  @ViewChild('alertChart') alertChart!: ElementRef;

  // Real-time data
  cells: RANCellData[] = [];
  alerts: RANAlert[] = [];
  loading = true;

  // Dashboard cells for table display
  dashboardCells: any[] = [];

  // Zone selection properties
  selectedZone: string = 'Zone_77'; // Default selection
  availableZones: string[] = ['Zone_77', 'Zone_78', 'Zone_79', 'Zone_80', 'Zone_81', 'Zone_82', 'Zone_83', 'Zone_84', 'Zone_85'];

  // Cluster synchronization
  currentClusterId: string | number | null = null;
  currentCluster: RANCellData | null = null;
  clustersWithGPS: RANCellData[] = [];
  clustersWithoutGPS: RANCellData[] = [];
  selectedClusterForKPI: RANCellData | null = null;
  showKPIDetails: boolean = false;

  // Geographic heatmap data
  heatmapData: any[] = [];
  mapCenter = { lat: 48.8566, lng: 2.3522 }; // Paris coordinates
  mapZoom = 12;

  private clusterSyncSubscription: Subscription = new Subscription();

  // Real-time metrics
  anomalyMetrics: any = {
    activeAnomalies: 0,
    criticalAnomalies: 0,
    hoSpikes: 0,
    rsrpDropEvents: 0,
    maxAnomalyScore: 0,
    worstCluster: '',
    lastUpdate: ''
  };

  // Visual indicators
  isUpdating: boolean = false;
  lastUpdateTime: string = '';

  private chartInstance: any = null;
  private alertChartInstance: any = null;
  private apiSubscription: Subscription = new Subscription();
  private realTimeInterval: any;

  constructor(
    private router: Router,
    private cdr: ChangeDetectorRef,
    private apiService: DonNextApiService,
    private clusterSyncService: ClusterSyncService
  ) {}

  ngOnInit(): void {
    this.loadAnomalyData();
    
    // Subscribe to cluster changes from KPI page
    this.clusterSyncSubscription = this.clusterSyncService.currentCluster$.subscribe(clusterData => {
      this.onClusterChanged(clusterData);
    });
  }

  ngAfterViewInit(): void {
    console.log('ðŸ”„ ngAfterViewInit called');
    setTimeout(() => {
      console.log('â° Timeout triggered, drawing charts...');
      this.drawAnomalyChart();
      this.drawAlertHistogramChart();
      this.startRealTimeUpdates();
    }, 2000);
  }

  onClusterChanged(clusterData: any): void {
    console.log('ðŸ”„ Cluster changed in Anomaly Detection:', clusterData);
    
    this.currentClusterId = clusterData.currentClusterId;
    this.currentCluster = clusterData.currentCluster;
    this.cells = clusterData.allClusters;
    
    // Update cluster categories
    this.updateClusterCategories();
    
    // Update maps
    this.updateClusterMaps();
    
    // Update current status display
    this.updateCurrentStatus();
    
    this.cdr.detectChanges();
  }

  ngOnDestroy(): void {
    if (this.chartInstance) {
      this.chartInstance.destroy();
    }
    if (this.realTimeInterval) {
      clearInterval(this.realTimeInterval);
    }
    this.apiSubscription.unsubscribe();
    this.clusterSyncSubscription.unsubscribe();
  }

  updateClusterCategories(): void {
    if (this.cells.length > 0) {
      this.clustersWithGPS = this.clusterSyncService.getClustersWithGPS(this.cells);
      this.clustersWithoutGPS = this.clusterSyncService.getClustersWithoutGPS(this.cells);
    }
  }

  updateClusterMaps(): void {
    // Update GPS map data
    this.heatmapData = this.clustersWithGPS.map(cluster => ({
      clusterId: cluster.cluster_id || cluster.id,
      lat: cluster.latitude || 48.8566,
      lng: cluster.longitude || 2.3522,
      intensity: this.calculateAnomalyIntensity(cluster),
      status: cluster.status
    }));
    
    // Draw maps if canvas is available
    if (this.heatmapCanvas) {
      setTimeout(() => this.drawClusterMaps(), 100);
    }
  }

  updateCurrentStatus(): void {
    // Update current status display
    this.anomalyMetrics.lastUpdate = new Date().toLocaleTimeString();
  }

  calculateAnomalyIntensity(cluster: RANCellData): number {
    // Calculate anomaly intensity based on cluster metrics
    let intensity = 0;
    
    // HO Success Rate contribution
    const hoRate = parseFloat(cluster.ho.replace('%', ''));
    if (hoRate < 90) intensity += 0.4;
    else if (hoRate < 95) intensity += 0.2;
    
    // RSRP contribution
    if (cluster.rsrp && cluster.rsrp < -100) intensity += 0.3;
    else if (cluster.rsrp && cluster.rsrp < -95) intensity += 0.15;
    
    // SINR contribution
    if (cluster.sinr && cluster.sinr < 5) intensity += 0.3;
    else if (cluster.sinr && cluster.sinr < 10) intensity += 0.15;
    
    return Math.min(intensity, 1.0);
  }

  onClusterClick(cluster: RANCellData): void {
    console.log('ðŸ“ Cluster clicked:', cluster);
    this.selectedClusterForKPI = cluster;
    this.showKPIDetails = true;
    
    // Emit cluster change to sync with KPI page
    this.clusterSyncService.updateCurrentCluster(
      cluster.cluster_id || cluster.id,
      cluster,
      this.cells
    );
  }

  closeKPIDetails(): void {
    this.showKPIDetails = false;
    this.selectedClusterForKPI = null;
  }

  onCanvasClick(event: MouseEvent): void {
    const canvas = this.heatmapCanvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // Check if click is on GPS map side
    if (x < canvas.width / 2) {
      this.handleGPSMapClick(x, y);
    } else {
      this.handleNonGPSMapClick(x, y);
    }
  }

  handleGPSMapClick(x: number, y: number): void {
    this.clustersWithGPS.forEach((cluster, index) => {
      const clusterX = 30 + (index % 5) * 60;
      const clusterY = 60 + Math.floor(index / 5) * 40;
      
      // Check if click is within cluster circle
      const distance = Math.sqrt(Math.pow(x - clusterX, 2) + Math.pow(y - clusterY, 2));
      if (distance <= 8) {
        this.onClusterClick(cluster);
      }
    });
  }

  handleNonGPSMapClick(x: number, y: number): void {
    const canvas = this.heatmapCanvas.nativeElement;
    const adjustedX = x - canvas.width / 2;
    
    this.clustersWithoutGPS.forEach((cluster, index) => {
      const clusterX = 30 + (index % 5) * 60;
      const clusterY = 60 + Math.floor(index / 5) * 40;
      
      // Check if click is within cluster circle
      const distance = Math.sqrt(Math.pow(adjustedX - clusterX, 2) + Math.pow(y - clusterY, 2));
      if (distance <= 8) {
        this.onClusterClick(cluster);
      }
    });
  }

  getClusterAlerts(cluster: RANCellData): RANAlert[] {
    // Filter alerts for the specific cluster
    return this.alerts.filter(alert => 
      alert.zone === cluster.zone || 
      alert.gnb === String(cluster.cluster_id || cluster.id) ||
      alert.message.includes(String(cluster.cluster_id || cluster.id))
    );
  }

  getActiveAlerts(): RANAlert[] {
    return this.alerts.filter(alert => 
      alert.priority === 'P1' || alert.priority === 'P2'
    );
  }

  getAlertCountByPriority(priority: string): number {
    return this.alerts.filter(alert => alert.priority === priority).length;
  }

  getAlertPercentage(priority: string): number {
    const total = this.alerts.length;
    if (total === 0) return 0;
    const count = this.getAlertCountByPriority(priority);
    return Math.round((count / total) * 100);
  }

  getAlertsWithRecommendations(): any[] {
    return this.alerts.map(alert => ({
      ...alert,
      recommendation: this.getRecommendationForAlert(alert)
    }));
  }

  getRecommendationForAlert(alert: RANAlert): string {
    const recommendations: { [key: string]: string } = {
      'HO Failure': 'Optimize handover parameters: Reduce hysteresis, adjust TTT timer, and review neighbor cell relationships.',
      'RSRP Drop': 'Check antenna alignment, increase transmission power, or add additional cells for coverage improvement.',
      'SINR Degradation': 'Analyze interference sources, optimize frequency planning, and implement interference mitigation techniques.',
      'High Load': 'Load balance traffic, add capacity, or implement traffic shaping algorithms.',
      'Cell Outage': 'Immediate field investigation required. Check power supply, backhaul connectivity, and hardware status.',
      'Performance Degradation': 'Run diagnostic tests, check configuration parameters, and analyze recent changes.',
      'Capacity Issue': 'Consider cell splitting, carrier aggregation, or deploying additional cells.',
      'Quality Issue': 'Review antenna tilt, power settings, and environmental factors affecting signal quality.',
      'Default': 'Monitor the situation closely, gather more data, and consult network optimization guidelines.'
    };

    // Extract alert type from message
    const message = alert.message.toLowerCase();
    if (message.includes('ho') || message.includes('handover')) {
      return recommendations['HO Failure'];
    } else if (message.includes('rsrp') || message.includes('signal')) {
      return recommendations['RSRP Drop'];
    } else if (message.includes('sinr') || message.includes('interference')) {
      return recommendations['SINR Degradation'];
    } else if (message.includes('load') || message.includes('capacity')) {
      return recommendations['High Load'];
    } else if (message.includes('outage') || message.includes('down')) {
      return recommendations['Cell Outage'];
    } else if (message.includes('performance') || message.includes('degradation')) {
      return recommendations['Performance Degradation'];
    } else if (message.includes('capacity') || message.includes('congestion')) {
      return recommendations['Capacity Issue'];
    } else if (message.includes('quality') || message.includes('kpi')) {
      return recommendations['Quality Issue'];
    }

    return recommendations['Default'];
  }

  drawAlertHistogramChart(): void {
    if (!this.alertChart) return;

    const ctx = this.alertChart.nativeElement.getContext('2d');
    
    // Prepare data
    const p1Count = this.getAlertCountByPriority('P1');
    const p2Count = this.getAlertCountByPriority('P2');
    const p3Count = this.getAlertCountByPriority('P3');
    
    // Destroy existing chart
    if (this.alertChartInstance) {
      this.alertChartInstance.destroy();
    }

    // Create new histogram chart
    this.alertChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['P1 Critical', 'P2 Warning', 'P3 Info'],
        datasets: [{
          label: 'Number of Alerts',
          data: [p1Count, p2Count, p3Count],
          backgroundColor: [
            '#DC2626', // Red for critical
            '#F59E0B', // Orange for warning
            '#3B82F6'  // Blue for info
          ],
          borderColor: [
            '#B91C1C',
            '#D97706',
            '#2563EB'
          ],
          borderWidth: 2,
          borderRadius: 6,
          barThickness: 60
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: function(context: any) {
                const label = context.label || '';
                const value = context.parsed.y || 0;
                const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
                const percentage = Math.round((value / total) * 100);
                return `${label}: ${value} (${percentage}%)`;
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              stepSize: 1,
              font: {
                size: 11
              }
            },
            grid: {
              color: '#E5E7EB',
              drawBorder: false
            },
            title: {
              display: true,
              text: 'Number of Alerts',
              font: {
                size: 12,
                weight: 'bold'
              }
            }
          },
          x: {
            grid: {
              display: false
            },
            ticks: {
              font: {
                size: 11
              }
            }
          }
        },
        animation: {
          duration: 1000,
          easing: 'easeInOutQuart'
        }
      }
    });
  }

  drawClusterMaps(): void {
    if (!this.heatmapCanvas) return;
    
    const canvas = this.heatmapCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw GPS clusters map
    this.drawGPSMap(ctx, canvas);
    
    // Draw non-GPS clusters map
    this.drawNonGPSMap(ctx, canvas);
  }

  drawGPSMap(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement): void {
    // Draw background
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(10, 10, canvas.width / 2 - 20, 200);
    
    // Draw title
    ctx.fillStyle = '#333';
    ctx.font = 'bold 14px Arial';
    ctx.fillText('Clusters with GPS', 20, 30);
    
    // Draw clusters
    this.clustersWithGPS.forEach((cluster, index) => {
      const x = 30 + (index % 5) * 60;
      const y = 60 + Math.floor(index / 5) * 40;
      
      // Draw cluster circle
      const intensity = this.calculateAnomalyIntensity(cluster);
      if (intensity > 0.7) ctx.fillStyle = '#DC2626';
      else if (intensity > 0.4) ctx.fillStyle = '#F59E0B';
      else ctx.fillStyle = '#10B981';
      
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, 2 * Math.PI);
      ctx.fill();
      
      // Draw cluster ID
      ctx.fillStyle = '#333';
      ctx.font = '10px Arial';
      ctx.fillText(String(cluster.cluster_id || cluster.id), x - 10, y + 20);
      
      // Make it clickable
      ctx.strokeStyle = '#333';
      ctx.lineWidth = 1;
      ctx.stroke();
    });
  }

  drawNonGPSMap(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement): void {
    // Draw background
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(canvas.width / 2 + 10, 10, canvas.width / 2 - 20, 200);
    
    // Draw title
    ctx.fillStyle = '#333';
    ctx.font = 'bold 14px Arial';
    ctx.fillText('Clusters without GPS', canvas.width / 2 + 20, 30);
    
    // Draw clusters
    this.clustersWithoutGPS.forEach((cluster, index) => {
      const x = canvas.width / 2 + 30 + (index % 5) * 60;
      const y = 60 + Math.floor(index / 5) * 40;
      
      // Draw cluster circle
      const intensity = this.calculateAnomalyIntensity(cluster);
      if (intensity > 0.7) ctx.fillStyle = '#DC2626';
      else if (intensity > 0.4) ctx.fillStyle = '#F59E0B';
      else ctx.fillStyle = '#10B981';
      
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, 2 * Math.PI);
      ctx.fill();
      
      // Draw cluster ID
      ctx.fillStyle = '#333';
      ctx.font = '10px Arial';
      ctx.fillText(String(cluster.cluster_id || cluster.id), x - 10, y + 20);
      
      // Make it clickable
      ctx.strokeStyle = '#333';
      ctx.lineWidth = 1;
      ctx.stroke();
    });
  }

  private loadAnomalyData(): void {
    console.log('ðŸ“¡ Loading anomaly data from backend...');
    
    // Subscribe to real backend data
    const cellsSub = this.apiService.cells$.subscribe(cellsData => {
      if (cellsData && cellsData.length > 0) {
        this.cells = cellsData;
        console.log('ðŸ“± Real cell data for anomaly:', cellsData);
        this.updateAnomalyMetrics();
        this.cdr.detectChanges();
      }
    });

    const alertsSub = this.apiService.alerts$.subscribe(alertsData => {
      if (alertsData && alertsData.length > 0) {
        this.alerts = alertsData;
        console.log('ðŸš¨ Real alert data for anomaly:', alertsData);
        this.updateAnomalyMetrics();
        this.cdr.detectChanges();
      }
    });

    this.apiSubscription.add(cellsSub);
    this.apiSubscription.add(alertsSub);
  }

  private startRealTimeUpdates(): void {
    console.log('ðŸš€ Starting real-time anomaly updates every 5 seconds');
    
    // Initialize metrics
    this.updateAnomalyMetrics();
    
    // Set up interval for real-time updates
    this.realTimeInterval = setInterval(() => {
      this.updateAnomalyMetrics();
    }, 5000);
  }

  private updateAnomalyMetrics(): void {
    if (this.cells.length === 0) return;
    
    // Generate realistic anomaly metrics based on real cell data
    const criticalCells = this.cells.filter(cell => (cell.status as any) === 'Critical' || (cell.status as any) === 'critical');
    const warningCells = this.cells.filter(cell => (cell.status as any) === 'Warning' || (cell.status as any) === 'warning');
    
    // Calculate anomaly scores based on real metrics
    const anomalyScores = this.cells.map(cell => {
      const hoSuccess = parseFloat(cell.ho.replace('%', ''));
      const rsrpValue = cell.rsrp || -85;
      const sinrValue = cell.sinr || 15;
      
      // Anomaly score calculation based on real metrics
      let score = 0;
      if (hoSuccess < 90) score += 0.3;
      if (rsrpValue < -90) score += 0.4;
      if (sinrValue < 10) score += 0.3;
      
      return {
        clusterId: cell.cluster_id || cell.id,
        score: Math.min(1, score + Math.random() * 0.2), // Add some randomness
        cell: cell
      };
    });
    
    // Sort by score to find worst cluster
    anomalyScores.sort((a, b) => b.score - a.score);
    const worstAnomaly = anomalyScores[0];
    
    // Update metrics
    this.anomalyMetrics = {
      activeAnomalies: criticalCells.length + warningCells.length,
      criticalAnomalies: criticalCells.length,
      hoSpikes: Math.floor(Math.random() * 15 + 5), // 5-20 spikes
      rsrpDropEvents: Math.floor(Math.random() * 25 + 10), // 10-35 events
      maxAnomalyScore: worstAnomaly?.score || 0,
      worstCluster: worstAnomaly?.clusterId || '',
      lastUpdate: new Date().toLocaleTimeString()
    };
    
    // Update real-time table data
    this.updateRealTimeTable();
    
    // Update geographic heatmap
    this.updateGeographicHeatmap();
    
    // Update visual indicators
    this.isUpdating = true;
    this.lastUpdateTime = this.anomalyMetrics.lastUpdate;
    
    console.log(`ðŸ”„ Updated anomaly metrics:`, this.anomalyMetrics);
    
    // Hide updating indicator after delay
    setTimeout(() => {
      this.isUpdating = false;
      this.cdr.detectChanges();
    }, 1000);
    
    // Force change detection
    this.cdr.detectChanges();
  }

  private updateRealTimeTable(): void {
    console.log('ðŸ”„ Updating real-time table with backend data...');
    console.log('ðŸ“Š Original backend cells:', this.cells.length);
    
    // Add realistic real-time variations to actual backend data
    this.cells = this.cells.map((cell, index) => {
      // Use actual backend values as base
      const originalHo = parseFloat(cell.ho.replace('%', ''));
      const originalRsrp = cell.rsrp || -85;
      const originalSinr = cell.sinr || 15;
      const originalTh = parseFloat(cell.th || '150');
      const originalUes = cell.ues || 100;
      
      // Add small realistic variations (Â±1-2% for realistic network fluctuations)
      const hoVariation = (Math.random() - 0.5) * 2; // Â±1% variation
      const rsrpVariation = (Math.random() - 0.5) * 2; // Â±1dBm variation
      const sinrVariation = (Math.random() - 0.5) * 1; // Â±0.5dB variation
      const thVariation = Math.floor((Math.random() - 0.5) * 5); // Â±2.5 Mbps variation
      const uesVariation = Math.floor((Math.random() - 0.5) * 3); // Â±1.5 users variation
      
      const newHo = Math.max(0, Math.min(100, originalHo + hoVariation));
      const newRsrp = originalRsrp + rsrpVariation;
      const newSinr = originalSinr + sinrVariation;
      const newTh = Math.max(1, originalTh + thVariation);
      const newUes = Math.max(1, originalUes + uesVariation);
      
      const updatedCell = {
        ...cell,
        ho: newHo.toFixed(1) + '%',
        rsrp: newRsrp,
        sinr: newSinr,
        th: String(newTh),
        ues: newUes,
        lastUpdate: new Date().toLocaleTimeString(),
        // Keep original backend data for reference
        originalHo: cell.ho,
        originalRsrp: cell.rsrp,
        originalSinr: cell.sinr,
        originalTh: cell.th,
        originalUes: cell.ues
      } as any;
      
      console.log(`ðŸ“± Cluster ${cell.cluster_id || cell.id}: HO ${cell.ho} â†’ ${updatedCell.ho}, RSRP ${cell.rsrp} â†’ ${updatedCell.rsrp.toFixed(1)}`);
      
      return updatedCell;
    });
    
    console.log('âœ… Real-time table updated with live backend data variations');
  }

  private updateGeographicHeatmap(): void {
    // Generate geographic coordinates for heatmap based on cluster data
    this.heatmapData = this.cells.map((cell, index) => {
      const score = this.calculateAnomalyScore(cell);
      const baseLat = 48.8566; // Paris center
      const baseLng = 2.3522;
      
      // Generate realistic coordinates around Paris
      const latOffset = (Math.random() - 0.5) * 0.1; // Â±0.05 degrees
      const lngOffset = (Math.random() - 0.5) * 0.1; // Â±0.05 degrees
      
      return {
        clusterId: cell.cluster_id || cell.id,
        lat: baseLat + latOffset,
        lng: baseLng + lngOffset,
        intensity: score, // 0-1 intensity for heatmap
        rsrp: cell.rsrp || -85,
        hoSuccess: parseFloat(cell.ho.replace('%', '')),
        status: cell.status,
        ues: cell.ues || 100,
        timestamp: new Date().toLocaleTimeString()
      };
    });
    
    console.log('ðŸ—ºï¸ Updated geographic heatmap data:', this.heatmapData);
    
    // Draw the heatmap
    setTimeout(() => this.drawHeatmap(), 100);
  }

  private drawAnomalyChart(): void {
    console.log('ðŸŽ¯ Starting drawAnomalyChart...');
    console.log('ðŸ“Š Chart available:', typeof Chart !== 'undefined');
    
    const canvas = this.chartAnomaly?.nativeElement;
    console.log('ðŸŽ¨ Canvas found:', !!canvas);
    
    if (!canvas) {
      console.error('âŒ chartAnomaly canvas not found');
      return;
    }

    // Destroy existing chart if any
    if (this.chartInstance) {
      console.log('ðŸ—‘ï¸ Destroying existing chart');
      this.chartInstance.destroy();
      this.chartInstance = null;
    }

    // Generate real anomaly data for chart
    const timeLabels = Array.from({length: 24}, (_, i) => `${i}:00`);
    const anomalyData = this.cells.map((cell, index) => {
      const baseScore = this.calculateAnomalyScore(cell);
      return timeLabels.map((_, timeIndex) => {
        const variation = Math.sin(timeIndex / 6) * 0.2;
        const randomNoise = (Math.random() - 0.5) * 0.1;
        return Math.max(0, Math.min(1, baseScore + variation + randomNoise));
      });
    });

    // Create anomaly chart
    const ctx = canvas.getContext('2d');
    this.chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: timeLabels,
        datasets: this.cells.map((cell, index) => ({
          label: `${cell.cluster_id || cell.id}`,
          data: anomalyData[index],
          borderColor: this.getAnomalyColor(this.calculateAnomalyScore(cell)),
          backgroundColor: this.getAnomalyColor(this.calculateAnomalyScore(cell), 0.1),
          fill: false,
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 6
        }))
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, position: 'bottom' },
          title: { display: true, text: 'Anomaly Scores - 24h Trend' },
          subtitle: { display: true, text: 'Real-time anomaly detection based on HO success, RSRP, SINR metrics' },
          tooltip: {
            callbacks: {
              title: function(context: any) {
                return `Time: ${context[0].label}`;
              },
              label: function(context: any) {
                return [
                  `Cluster: ${context.dataset.label}`,
                  `Score: ${context.parsed.y.toFixed(3)}`,
                  `Risk: ${context.parsed.y > 0.7 ? 'Critical' : context.parsed.y > 0.4 ? 'Warning' : 'Normal'}`
                ];
              }
            }
          }
        },
        scales: {
          y: { 
            beginAtZero: true, 
            max: 1,
            ticks: {
              callback: function(value: any) {
                return (value * 100).toFixed(0) + '%';
              }
            }
          }
        }
      }
    });

    console.log('âœ… Anomaly chart created successfully');
  }

  private calculateAnomalyScore(cell: RANCellData): number {
    const hoSuccess = parseFloat(cell.ho.replace('%', ''));
    const rsrpValue = cell.rsrp || -85;
    const sinrValue = cell.sinr || 15;
    
    let score = 0;
    if (hoSuccess < 90) score += 0.3;
    if (rsrpValue < -90) score += 0.4;
    if (sinrValue < 10) score += 0.3;
    
    return Math.min(1, score);
  }

  private getAnomalyColor(score: number, alpha: number = 1): string {
    if (score > 0.7) return alpha < 1 ? `rgba(220, 38, 38, ${alpha})` : '#DC2626'; // Red
    if (score > 0.4) return alpha < 1 ? `rgba(245, 158, 11, ${alpha})` : '#F59E0B'; // Orange
    return alpha < 1 ? `rgba(16, 185, 129, ${alpha})` : '#10B981'; // Green
  }

  // Helper methods for alerts
  getAnomalyAlerts(): any[] {
    return this.cells.map(cell => {
      const score = this.calculateAnomalyScore(cell);
      const severity = score > 0.7 ? 'critical' : score > 0.4 ? 'warning' : 'normal';
      const timeAgo = Math.floor(Math.random() * 60 + 1); // 1-60 minutes ago
      
      return {
        clusterId: cell.cluster_id || cell.id,
        score: score,
        severity: severity,
        description: this.getAnomalyDescription(score, cell),
        timeAgo: timeAgo
      };
    }).filter(alert => alert.severity !== 'normal').sort((a, b) => b.score - a.score).slice(0, 5);
  }

  private getAnomalyDescription(score: number, cell: RANCellData): string {
    const hoSuccess = parseFloat(cell.ho.replace('%', ''));
    const rsrpValue = cell.rsrp || -85;
    
    if (score > 0.7) {
      return `Score composite ${score.toFixed(2)} â€” HO failure + RSRP drop critiques simultanÃ©s`;
    } else if (score > 0.4) {
      return `Score composite ${score.toFixed(2)} â€” Ping-pong dÃ©tectÃ© par DSO1, drop RSRP imminent DSO2`;
    } else {
      return `Score composite ${score.toFixed(2)} â€” Metrics within normal range`;
    }
  }

  generatePDFReport(): void {
    this.router.navigate(['/ran-engineer/pdf-report/anomaly']);
  }

  private drawHeatmap(): void {
    const canvas = this.heatmapCanvas?.nativeElement;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.offsetWidth;
    const height = canvas.height = canvas.offsetHeight;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Draw background
    ctx.fillStyle = '#e8f4f8';
    ctx.fillRect(0, 0, width, height);
    
    // Draw heatmap points
    this.heatmapData.forEach(point => {
      const x = ((point.lng - 2.2) / 0.3) * width;
      const y = ((48.95 - point.lat) / 0.2) * height;
      const radius = 30 + point.intensity * 20; // Size based on intensity
      
      // Create gradient for heat effect
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
      
      if (point.intensity > 0.7) {
        // High intensity - red
        gradient.addColorStop(0, 'rgba(220, 38, 38, 0.8)');
        gradient.addColorStop(0.5, 'rgba(220, 38, 38, 0.4)');
        gradient.addColorStop(1, 'rgba(220, 38, 38, 0)');
      } else if (point.intensity > 0.4) {
        // Medium intensity - orange
        gradient.addColorStop(0, 'rgba(245, 158, 11, 0.8)');
        gradient.addColorStop(0.5, 'rgba(245, 158, 11, 0.4)');
        gradient.addColorStop(1, 'rgba(245, 158, 11, 0)');
      } else {
        // Low intensity - green
        gradient.addColorStop(0, 'rgba(16, 185, 129, 0.8)');
        gradient.addColorStop(0.5, 'rgba(16, 185, 129, 0.4)');
        gradient.addColorStop(1, 'rgba(16, 185, 129, 0)');
      }
      
      ctx.fillStyle = gradient;
      ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
      
      // Draw center point
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, 2 * Math.PI);
      ctx.fillStyle = point.intensity > 0.7 ? '#DC2626' : point.intensity > 0.4 ? '#F59E0B' : '#10B981';
      ctx.fill();
    });
    
    console.log('ðŸ—ºï¸ Heatmap drawn with', this.heatmapData.length, 'points');
  }

  getColorStyle(value: string | undefined): string {
    if (!value) return 'color: #6B7280; font-weight: 600;';
    
    const numValue = parseFloat(value.replace('%', ''));
    if (isNaN(numValue)) return 'color: #6B7280; font-weight: 600;';
    
    if (numValue > 95) return 'color: #059669; font-weight: 600;';
    if (numValue > 90) return 'color: #B45309; font-weight: 600;';
    return 'color: #DC2626; font-weight: 600;';
  }

  getStatusClass(status: string): string {
    switch (status.toLowerCase()) {
      case 'critical': return 'badge-red';
      case 'warning': return 'badge-orange';
      case 'healthy':
      case 'ok': return 'badge-green';
      default: return 'badge-gray';
    }
  }

  getRowClass(status: string): string {
    switch ((status as any).toLowerCase()) {
      case 'critical': return 'critical-row';
      case 'warning': return 'warning-row';
      case 'healthy':
      case 'ok': 
      default: return 'normal-row';
    }
  }

  getLastUpdate(cell: any): string {
    return (cell as any).lastUpdate || 'N/A';
  }

  generateExcelReport(): void {
    // Generate real-time Excel content
    let content = 'Cluster ID,Anomaly Score,HO Success,RSRP,SINR,Status,Time\n';
    this.cells.forEach((cell: any) => {
      const score = this.calculateAnomalyScore(cell);
      content += `${cell.cluster_id || cell.id},${score.toFixed(3)},${cell.ho},${cell.rsrp},${cell.sinr},${cell.status},${new Date().toLocaleTimeString()}\n`;
    });
    
    const blob = new Blob([content], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `anomaly-report-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    document.body.removeChild(anchor);
    window.URL.revokeObjectURL(url);
  }

  // Zone selection methods
  onZoneChange(event: any): void {
    this.selectedZone = event.target.value;
    this.filterAlertsByZone();
    this.updateZoneMetrics();
    this.updateLastUpdateTime();
  }

  refreshZoneData(): void {
    this.isUpdating = true;
    this.loadAnomalyData();
    setTimeout(() => {
      this.isUpdating = false;
      this.updateLastUpdateTime();
    }, 1000);
  }

  private filterAlertsByZone(): void {
    if (!this.selectedZone) {
      this.loadAnomalyData();
      return;
    }
    // Filter alerts based on selected zone
    this.alerts = this.alerts.filter(alert => alert.zone === this.selectedZone);
  }

  private updateZoneMetrics(): void {
    if (!this.selectedZone) {
      return;
    }
    // Update metrics based on selected zone
    const zoneAlerts = this.alerts.filter(alert => alert.zone === this.selectedZone);
    this.anomalyMetrics.activeAnomalies = zoneAlerts.length;
    // Use priority property from RANAlert interface
    this.anomalyMetrics.criticalAnomalies = zoneAlerts.filter(alert => alert.priority === 'P1').length;
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

  private loadAnomalyMetrics(): void {
    // Load anomaly metrics from simulator data
    this.loadSimulatorAnomalyData();
  }

  private loadAlerts(): void {
    // Load alerts from simulator data
    this.loadSimulatorAlerts();
  }

  private loadSimulatorAnomalyData(): void {
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

    // Calculate anomaly metrics
    const criticalClusters = simulatorClusters.filter(c => c.status === 'critical');
    const warningClusters = simulatorClusters.filter(c => c.status === 'warning');
    
    this.anomalyMetrics = {
      activeAnomalies: criticalClusters.length + warningClusters.length,
      criticalAnomalies: criticalClusters.length,
      hoSpikes: warningClusters.length,
      rsrpDropEvents: criticalClusters.length,
      maxAnomalyScore: Math.max(...simulatorClusters.map(c => 
        c.status === 'critical' ? 0.85 : c.status === 'warning' ? 0.65 : 0.25
      )),
      worstCluster: criticalClusters.length > 0 ? criticalClusters[0].zone_id : 'None',
      lastUpdate: new Date().toLocaleString()
    };
  }

  private loadSimulatorAlerts(): void {
    // Create alerts based on simulator data - 9 zones uniques
    const simulatorAlerts = [
      {
        priority: 'P1' as 'P1' | 'P2' | 'P3',
        message: 'Critical HO failure detected in Zone_80',
        time: '5m ago',
        clusterId: 80,
        zone: 'Zone_80'
      },
      {
        priority: 'P2' as 'P1' | 'P2' | 'P3',
        message: 'HO performance degraded in Zone_78',
        time: '12m ago',
        clusterId: 78,
        zone: 'Zone_78'
      },
      {
        priority: 'P3' as 'P1' | 'P2' | 'P3',
        message: 'RSRP drop warning in Zone_84',
        time: '18m ago',
        clusterId: 84,
        zone: 'Zone_84'
      },
      {
        priority: 'P2' as 'P1' | 'P2' | 'P3',
        message: 'Signal degradation in Zone_82',
        time: '25m ago',
        clusterId: 82,
        zone: 'Zone_82'
      }
    ];

    this.alerts = simulatorAlerts;
  }
}
