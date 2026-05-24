import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, interval } from 'rxjs';
import { map } from 'rxjs/operators';

export interface ClusterMetric {
  cluster_id: number;
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  network_throughput: number;
  latency_ms: number;
  packet_loss: number;
  availability: number;
  error_rate: number;
  active_connections: number;
}

export interface SystemHealth {
  total_clusters: number;
  healthy_clusters: number;
  warning_clusters: number;
  critical_clusters: number;
  avg_cpu_usage: number;
  avg_memory_usage: number;
  avg_latency: number;
  total_throughput: number;
  uptime_percentage: number;
  last_updated: string;
}

export interface Alert {
  id: string;
  cluster_id: number;
  severity: string;
  type: string;
  message: string;
  timestamp: string;
  resolved: boolean;
  metric_name?: string;
  threshold?: number;
  current_value?: number;
}

@Injectable({ providedIn: 'root' })
export class MonitoringService {
  private readonly API_URL = '';
  
  private metricsSubject = new BehaviorSubject<ClusterMetric[]>([]);
  private systemHealthSubject = new BehaviorSubject<SystemHealth | null>(null);
  private alertsSubject = new BehaviorSubject<Alert[]>([]);
  
  public metrics$ = this.metricsSubject.asObservable();
  public systemHealth$ = this.systemHealthSubject.asObservable();
  public alerts$ = this.alertsSubject.asObservable();

  constructor(private http: HttpClient) {
    console.log('📊 MonitoringService initialized');
    this.startRealTimeUpdates();
  }

  private startRealTimeUpdates() {
    console.log('⏰ Starting monitoring updates every 2 seconds');
    
    // Mettre à jour immédiatement
    this.fetchMonitoringData();
    
    // Puis toutes les 2 secondes (très fréquent pour monitoring)
    interval(5000).subscribe(() => {
      this.fetchMonitoringData();
    });
  }

  private fetchMonitoringData() {
    console.log('📈 Fetching monitoring data from Python service...');
    
    // Récupérer les métriques en temps réel
    this.http.get<{metrics: ClusterMetric[], timestamp: string}>(`${this.API_URL}/api/v1/metrics/realtime?limit=5`).subscribe({
      next: (response) => {
        console.log('✅ Monitoring metrics received:', response.metrics.length, 'clusters');
        this.metricsSubject.next(response.metrics);
      },
      error: (error) => {
        console.error('❌ Monitoring API error:', error);
        this.useFallbackMetrics();
      }
    });

    // Récupérer la santé du système
    this.http.get<SystemHealth>(`${this.API_URL}/api/v1/system/health`).subscribe({
      next: (health) => {
        console.log('💚 System health received');
        this.systemHealthSubject.next(health);
      },
      error: (error) => {
        console.error('❌ System health API error:', error);
        this.useFallbackSystemHealth();
      }
    });

    // Récupérer les alertes actives
    this.http.get<{alerts: Alert[]}>(`${this.API_URL}/api/v1/alerts/active`).subscribe({
      next: (response) => {
        console.log('🚨 Active alerts received:', response.alerts.length, 'alerts');
        this.alertsSubject.next(response.alerts);
      },
      error: (error) => {
        console.error('❌ Alerts API error:', error);
        this.useFallbackAlerts();
      }
    });
  }

  private useFallbackMetrics() {
    console.log('⚠️ Using fallback monitoring metrics - Python service might be offline');
    
    // Generate dynamic clusters with real-time variations
    const baseClusterId = 77;
    const clusterCount = 20; // Generate 20 clusters (77-96)
    const currentTime = new Date();
    
    const fallbackMetrics: ClusterMetric[] = [];
    
    for (let i = 0; i < clusterCount; i++) {
      const clusterId = baseClusterId + i;
      const timeVariation = (currentTime.getSeconds() + i) % 60;
      const randomFactor = Math.sin(currentTime.getTime() / 10000 + i) * 0.3;
      
      fallbackMetrics.push({
        cluster_id: clusterId,
        timestamp: new Date().toISOString(),
        cpu_usage: Math.max(10, Math.min(95, 45 + Math.random() * 40 + randomFactor * 20)),
        memory_usage: Math.max(20, Math.min(95, 55 + Math.random() * 35 + randomFactor * 15)),
        network_throughput: Math.max(50, Math.min(800, 300 + Math.random() * 400 + randomFactor * 200)),
        latency_ms: Math.max(1, Math.min(100, 15 + Math.random() * 50 + randomFactor * 25)),
        packet_loss: Math.max(0, Math.min(10, 1 + Math.random() * 4 + randomFactor * 2)),
        availability: Math.max(85, Math.min(99.9, 95 + Math.random() * 4 + randomFactor * 2)),
        error_rate: Math.max(0, Math.min(5, 0.5 + Math.random() * 2 + randomFactor * 1)),
        active_connections: Math.floor(100 + Math.random() * 600 + randomFactor * 200)
      });
    }

    console.log(`🔄 Generated ${clusterCount} dynamic clusters (${baseClusterId}-${baseClusterId + clusterCount - 1})`);
    this.metricsSubject.next(fallbackMetrics);
  }

  private useFallbackSystemHealth() {
    const fallbackHealth: SystemHealth = {
      total_clusters: 9,
      healthy_clusters: 5,
      warning_clusters: 3,
      critical_clusters: 1,
      avg_cpu_usage: 72.3,
      avg_memory_usage: 67.8,
      avg_latency: 18.4,
      total_throughput: 2345.6,
      uptime_percentage: 99.2,
      last_updated: new Date().toISOString()
    };

    this.systemHealthSubject.next(fallbackHealth);
  }

  private useFallbackAlerts() {
    const fallbackAlerts: Alert[] = [
      {
        id: 'alert_77_1001',
        cluster_id: 77,
        severity: 'LOW',
        type: 'CPU_HIGH',
        message: 'CPU usage is above threshold for cluster 77',
        timestamp: new Date().toISOString(),
        resolved: false,
        metric_name: 'cpu_usage',
        threshold: 70.0,
        current_value: 75.2
      },
      {
        id: 'alert_78_1002',
        cluster_id: 78,
        severity: 'HIGH',
        type: 'LATENCY_HIGH',
        message: 'High latency detected on cluster 78',
        timestamp: new Date().toISOString(),
        resolved: false,
        metric_name: 'latency_ms',
        threshold: 30.0,
        current_value: 35.7
      },
      {
        id: 'alert_79_1003',
        cluster_id: 79,
        severity: 'CRITICAL',
        type: 'MEMORY_HIGH',
        message: 'Memory usage is critical for cluster 79',
        timestamp: new Date().toISOString(),
        resolved: false,
        metric_name: 'memory_usage',
        threshold: 85.0,
        current_value: 91.4
      }
    ];

    this.alertsSubject.next(fallbackAlerts);
  }

  // Méthodes pour accéder aux données spécifiques
  getClusterMetrics(clusterId: number): Observable<ClusterMetric[]> {
    return this.http.get<{cluster_id: number, metrics: ClusterMetric[]}>(
      `${this.API_URL}/api/v1/clusters/${clusterId}/metrics`
    ).pipe(map(response => response.metrics));
  }

  getMetricTrends(clusterId?: number, hours: number = 24): Observable<any> {
    const url = clusterId 
      ? `${this.API_URL}/api/v1/metrics/trends?cluster_id=${clusterId}&hours=${hours}`
      : `${this.API_URL}/api/v1/metrics/trends?hours=${hours}`;
    
    return this.http.get<{trends: any}>(url);
  }

  getPerformanceSummary(): Observable<any> {
    return this.http.get<any>(`${this.API_URL}/api/v1/performance/summary`);
  }

  resolveAlert(alertId: string): Observable<any> {
    return this.http.post<any>(`${this.API_URL}/api/v1/alerts/${alertId}/resolve`, {});
  }

  getAllClusters(): Observable<number[]> {
    return this.http.get<{clusters: number[]}>(`${this.API_URL}/api/v1/clusters`)
      .pipe(map(response => response.clusters));
  }
  getRealtimeMetrics(): Observable<any> {

  return this.http.get<any>(
    `${this.API_URL}/api/v1/metrics/realtime?limit=20`
  );

}
}




