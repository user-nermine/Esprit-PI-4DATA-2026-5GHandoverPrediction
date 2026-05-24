import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, interval } from 'rxjs';
import { map } from 'rxjs/operators';

export interface ClusterKPI {
  rsrp: number;
  rsrq: number;
  sinr: number;
  cqi: number;
  tx_power: number;
  velocity: number;
  n_records: number;
}

export interface ClusterData {
  timestamp: string;
  cluster_id: number;
  cluster_kpi: ClusterKPI;
  predictions: {
    no_handover: number;
    intra_freq_handover: number;
    inter_freq_handover: number;
    inter_rat_handover: number;
  };
  confidence: number;
}

export interface DashboardKPI {
  title: string;
  value: string;
  sub: string;
  trend: number[];
  color: string;
}

export interface DashboardCell {
  id: string;
  clusterId: number;
  zone: string;
  status: 'Healthy' | 'Warning' | 'Critical';
  ho: string;
  ues: number;
  alarms: number;
  rsrp: number;
  rsrq: number;
  sinr: number;
}

export interface DashboardAlert {
  priority: 'P1' | 'P2' | 'P3';
  message: string;
  time: string;
  clusterId: number;
  zone?: string;
}

export interface HOEvent {
  timestamp: string;
  clusterId: number;
  from: string;
  to: string;
  type: 'intra' | 'inter' | 'inter_rat';
  rsrp: number;
  zone: string;
  success: boolean;
}

@Injectable({ providedIn: 'root' })
export class ClusterDataService {
  private readonly API_URL = 'http://127.0.0.1:8000';
  
  private kpisSubject = new BehaviorSubject<DashboardKPI[]>([]);
  private cellsSubject = new BehaviorSubject<DashboardCell[]>([]);
  private alertsSubject = new BehaviorSubject<DashboardAlert[]>([]);
  private hoEventsSubject = new BehaviorSubject<HOEvent[]>([]);
  
  public kpis$ = this.kpisSubject.asObservable();
  public cells$ = this.cellsSubject.asObservable();
  public alerts$ = this.alertsSubject.asObservable();
  public hoEvents$ = this.hoEventsSubject.asObservable();

  constructor(private http: HttpClient) {
    this.startRealTimeUpdates();
  }

  private startRealTimeUpdates() {
    // Mettre à jour immédiatement
    this.fetchAndUpdateData();
    
    // Puis toutes les 3 secondes
    interval(3000).subscribe(() => {
      this.fetchAndUpdateData();
    });
  }

  private fetchAndUpdateData() {
    this.http.get<ClusterData[]>(`${this.API_URL}/api/v1/logs/dynamic/limit/5`).subscribe({
      next: (clusters) => {
        if (clusters && clusters.length > 0) {
          console.log('📊 Real cluster data received:', clusters.length, 'clusters');
          this.updateKPIs(clusters);
          this.updateCells(clusters);
          this.updateAlerts(clusters);
          this.updateHOEvents(clusters);
        }
      },
      error: (error) => {
        console.error('❌ API Error:', error);
        this.useFallbackData();
      }
    });
  }

  private updateKPIs(clusters: ClusterData[]) {
    const avgConfidence = clusters.reduce((sum, c) => sum + c.confidence, 0) / clusters.length;
    const avgHO = clusters.reduce((sum, c) => sum + c.predictions.no_handover, 0) / clusters.length;
    const totalUEs = clusters.reduce((sum, c) => sum + c.cluster_kpi.n_records, 0);
    const avgRSRP = clusters.reduce((sum, c) => sum + c.cluster_kpi.rsrp, 0) / clusters.length;
    
    const kpis: DashboardKPI[] = [
      { 
        title: 'Active Clusters', 
        value: clusters.length.toString(), 
        sub: `${clusters.filter(c => c.confidence > 0.8).length} healthy`,
        trend: [3, 4, 4, 5, 4, clusters.length],
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
        title: 'Model Accuracy', 
        value: `${(avgConfidence * 100).toFixed(1)}%`,
        sub: 'XGBoost confidence',
        trend: [91, 92, 93, 94, 95, avgConfidence * 100],
        color: '#8b5cf6'
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
    
    this.kpisSubject.next(kpis);
    console.log('✅ KPIs updated:', kpis);
  }

  private updateCells(clusters: ClusterData[]) {
    const cells: DashboardCell[] = clusters.map((cluster, index) => ({
      id: `gNB-${String(index + 1).padStart(3, '0')}`,
      clusterId: cluster.cluster_id,
      zone: ['Zone A', 'Zone B', 'Zone C', 'Zone D', 'Zone E'][index % 5],
      status: this.getHealthStatus(cluster.confidence),
      ho: `${(cluster.predictions.no_handover * 100).toFixed(1)}%`,
      ues: cluster.cluster_kpi.n_records,
      alarms: cluster.confidence < 0.7 ? Math.floor((1 - cluster.confidence) * 5) : 0,
      rsrp: cluster.cluster_kpi.rsrp,
      rsrq: cluster.cluster_kpi.rsrq,
      sinr: cluster.cluster_kpi.sinr
    }));
    
    this.cellsSubject.next(cells);
    console.log('✅ Cells updated:', cells);
  }

  private updateAlerts(clusters: ClusterData[]) {
    const alerts: DashboardAlert[] = [];
    
    clusters.forEach((cluster, index) => {
      if (cluster.confidence < 0.7) {
        alerts.push({
          priority: cluster.confidence < 0.5 ? 'P1' : 'P2',
          message: cluster.confidence < 0.5 
            ? `Critical HO failure in Cluster ${cluster.cluster_id}` 
            : `HO performance degraded in Cluster ${cluster.cluster_id}`,
          time: `${Math.floor(Math.random() * 30) + 1}m ago`,
          clusterId: cluster.cluster_id,
          zone: ['Zone A', 'Zone B', 'Zone C', 'Zone D', 'Zone E'][index % 5]
        });
      }
    });
    
    this.alertsSubject.next(alerts);
    console.log('✅ Alerts updated:', alerts);
  }

  private getHealthStatus(confidence: number): 'Healthy' | 'Warning' | 'Critical' {
    if (confidence > 0.8) return 'Healthy';
    if (confidence > 0.6) return 'Warning';
    return 'Critical';
  }

  private updateHOEvents(clusters: ClusterData[]) {
    const hoEvents: HOEvent[] = [];
    
    clusters.forEach((cluster, index) => {
      const zones = ['Zone A', 'Zone B', 'Zone C', 'Zone D', 'Zone E'];
      const types: ('intra' | 'inter' | 'inter_rat')[] = ['intra', 'inter', 'inter_rat'];
      const fromCells = ['gNB-001', 'gNB-002', 'gNB-003', 'gNB-004', 'gNB-005'];
      const toCells = ['gNB-002', 'gNB-003', 'gNB-004', 'gNB-005', 'gNB-001'];
      
      // Generate 1-2 HO events per cluster
      const eventCount = Math.floor(Math.random() * 2) + 1;
      
      for (let i = 0; i < eventCount; i++) {
        hoEvents.push({
          timestamp: new Date(Date.now() - Math.floor(Math.random() * 300000)).toISOString(),
          clusterId: cluster.cluster_id,
          from: fromCells[index],
          to: toCells[(index + 1) % 5],
          type: types[Math.floor(Math.random() * types.length)],
          rsrp: cluster.cluster_kpi.rsrp + Math.floor(Math.random() * 10 - 5),
          zone: zones[index % 5],
          success: cluster.predictions.no_handover > 0.8
        });
      }
    });
    
    // Sort by timestamp (most recent first)
    hoEvents.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    
    this.hoEventsSubject.next(hoEvents.slice(0, 10)); // Keep only 10 most recent
    console.log('✅ HO Events updated:', hoEvents.length, 'events');
  }

  private useFallbackData() {
    console.log('⚠️ Using fallback data - backend might be offline');
    
    const fallbackKpis: DashboardKPI[] = [
      { title: 'Active Clusters', value: '4', sub: '3 healthy', trend: [3, 4, 4, 5, 4, 4], color: '#22c55e' },
      { title: 'HO Success Rate', value: '95.2%', sub: 'Real-time', trend: [94, 95, 93, 96, 97, 95.2], color: '#3b82f6' },
      { title: 'Model Accuracy', value: '94.3%', sub: 'XGBoost confidence', trend: [91, 92, 93, 94, 95, 94.3], color: '#8b5cf6' },
      { title: 'Avg RSRP', value: '-84.2 dBm', sub: 'Signal strength', trend: [-85, -87, -83, -89, -84, -84.2], color: '#f59e0b' },
      { title: 'Total UEs', value: '8,742', sub: 'Connected devices', trend: [8000, 8200, 8500, 8300, 8700, 8742], color: '#ef4444' }
    ];
    
    this.kpisSubject.next(fallbackKpis);
  }
}
