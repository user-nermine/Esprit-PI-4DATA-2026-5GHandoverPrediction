/**
 * Service API pour connecter front-w avec les microservices DoNext 5G
 */
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ClusterData {
  cluster_id: number;
  cluster_kpi: {
    rsrp: number;
    rsrq: number;
    sinr: number;
    cqi: number;
    tx_power: number;
    velocity: number;
    n_records: number;
  };
  predictions: {
    no_handover: number;
    intra_freq_handover: number;
    inter_freq_handover: number;
    inter_rat_handover: number;
  };
  explainability: {
    shap_values: Record<string, number>;
    feature_importance: Record<string, number>;
  };
  dominant_prediction: string;
  confidence: number;
  timestamp: string;
}

export interface MonitoringMetrics {
  timestamp: string;
  gnbs: any;
  alarms: any;
  handover_success: any;
  throughput: any;
  ues_connected: any;
  model_accuracy: any;
}

@Injectable({
  providedIn: 'root'
})
export class DonextBackendService {
  private readonly httpOptions = {
    headers: new HttpHeaders({ 'Content-Type': 'application/json' })
  };

  // Subjects pour le temps réel
  private metricsSubject = new BehaviorSubject<MonitoringMetrics | null>(null);
  private clustersSubject = new BehaviorSubject<ClusterData[]>([]);

  // Observables publics
  metricsData$ = this.metricsSubject.asObservable();
  clusters$ = this.clustersSubject.asObservable();

  constructor(private http: HttpClient) {
    this.startRealTimeUpdates();
  }

  // ───────── ENDPOINTS PREDICTION SERVICE ─────────
  
  getPredictionModels(): Observable<any> {
    return this.http.get(`${environment.apiUrls.predictionService}/api/v1/predict/models`);
  }

  predictCluster(clusterId: number, features: any): Observable<any> {
    return this.http.post(`${environment.apiUrls.predictionService}/api/v1/predict/cluster/${clusterId}`, features);
  }

  getPredictionStats(): Observable<any> {
    return this.http.get(`${environment.apiUrls.predictionService}/api/v1/predict/stats`);
  }

  // ───────── ENDPOINTS MONITORING SERVICE ─────────
  
  getMonitoringMetrics(): Observable<MonitoringMetrics> {
    return this.http.get<MonitoringMetrics>(`${environment.apiUrls.monitoringService}/api/v1/monitoring/metrics`);
  }

  getKPIData(): Observable<any> {
    return this.http.get(`${environment.apiUrls.monitoringService}/api/v1/monitoring/kpi`);
  }

  getAlerts(): Observable<any> {
    return this.http.get(`${environment.apiUrls.monitoringService}/api/v1/monitoring/alerts`);
  }

  // ───────── ENDPOINTS EXPLAINABILITY SERVICE ─────────
  
  getClusterExplainability(clusterId: number): Observable<any> {
    return this.http.get(`${environment.apiUrls.explainabilityService}/api/v1/explainability/cluster/${clusterId}`);
  }

  getSHAPValues(clusterId: number): Observable<any> {
    return this.http.get(`${environment.apiUrls.explainabilityService}/api/v1/explainability/cluster/${clusterId}/shap`);
  }

  getFeatureImportance(clusterId: number): Observable<any> {
    return this.http.get(`${environment.apiUrls.explainabilityService}/api/v1/explainability/cluster/${clusterId}/feature-importance`);
  }

  compareClusters(clusterIds: number[]): Observable<any> {
    return this.http.post(`${environment.apiUrls.explainabilityService}/api/v1/explainability/compare`, { cluster_ids: clusterIds });
  }

  // ───────── ENDPOINTS REPORTING SERVICE ─────────
  
  getReportsList(): Observable<any> {
    return this.http.get(`${environment.apiUrls.reportingService}/api/reports/list`);
  }

  generateReport(type: string, params?: any): Observable<any> {
    return this.http.post(`${environment.apiUrls.reportingService}/api/reports/generate/${type}`, params);
  }

  downloadReport(reportId: string): Observable<Blob> {
    return this.http.get(`${environment.apiUrls.reportingService}/api/reports/download/${reportId}`, {
      responseType: 'blob'
    });
  }

  // ───────── ENDPOINTS DATA PIPELINE ─────────
  
  getPipelineClusters(): Observable<any> {
    return this.http.get(`${environment.apiUrls.dataPipeline}/api/v1/pipeline/clusters`);
  }

  getClusterFeatures(clusterId: number): Observable<any> {
    return this.http.get(`${environment.apiUrls.dataPipeline}/api/v1/pipeline/cluster/${clusterId}/features`);
  }

  getPipelineSummary(): Observable<any> {
    return this.http.get(`${environment.apiUrls.dataPipeline}/api/v1/pipeline/summary`);
  }

  // ───────── MÉTHODES COMBINÉES ─────────
  
  getCompleteClusterData(clusterId: number): Observable<any> {
    // Combine les données de plusieurs services
    const prediction$ = this.predictCluster(clusterId, {});
    const explainability$ = this.getClusterExplainability(clusterId);
    const features$ = this.getClusterFeatures(clusterId);
    
    // Retourner une combinaison des données
    return new Observable(observer => {
      Promise.all([
        prediction$.toPromise(),
        explainability$.toPromise(),
        features$.toPromise()
      ]).then(([prediction, explainability, features]) => {
        observer.next({
          cluster_id: clusterId,
          prediction,
          explainability,
          features,
          timestamp: new Date().toISOString()
        });
        observer.complete();
      }).catch(error => {
        observer.error(error);
      });
    });
  }

  // ───────── MISES À JOUR TEMPS RÉEL ─────────
  
  private startRealTimeUpdates() {
    // Mise à jour des métriques toutes les 5 secondes
    setInterval(() => {
      this.getMonitoringMetrics().subscribe(metrics => {
        this.metricsSubject.next(metrics);
      });
    }, 5000);

    // Mise à jour des clusters toutes les 10 secondes
    setInterval(() => {
      this.getPipelineClusters().subscribe(response => {
        const clusterPromises = response.clusters.map((clusterId: number) => 
          this.getCompleteClusterData(clusterId).toPromise()
        );
        
        Promise.all(clusterPromises).then(clusters => {
          this.clustersSubject.next(clusters as ClusterData[]);
        });
      });
    }, 10000);
  }

  // ───────── UTILITAIRES ─────────
  
  getHealthStatus(): Observable<any> {
    return this.http.get(`${environment.apiUrls.monitoringService}/health`);
  }

  formatSignalQuality(rsrp: number): string {
    if (rsrp > -70) return 'Excellent';
    if (rsrp > -85) return 'Good';
    if (rsrp > -100) return 'Fair';
    return 'Poor';
  }

  formatInterferenceLevel(sinr: number): string {
    if (sinr > 20) return 'Low';
    if (sinr > 10) return 'Medium';
    return 'High';
  }
}
