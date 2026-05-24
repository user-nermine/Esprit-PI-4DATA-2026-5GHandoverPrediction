import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, interval } from 'rxjs';
import { map } from 'rxjs/operators';

export interface SHAPValue {
  feature: string;
  value: number;
  importance: number;
  impact: 'positive' | 'negative';
}

export interface ExplainabilityData {
  cluster_id: number;
  shap_values: Record<string, number>;
  feature_importance: Record<string, number>;
  dominant_prediction: string;
  confidence: number;
  timestamp: string;
}

export interface WaterfallData {
  base_value: number;
  features: Array<{
    name: string;
    value: number;
    contribution: number;
  }>;
  final_prediction: number;
}

@Injectable({ providedIn: 'root' })
export class ExplainabilityService {
  private readonly API_URL = 'http://localhost:8083';
  
  private shapValuesSubject = new BehaviorSubject<SHAPValue[]>([]);
  private waterfallSubject = new BehaviorSubject<WaterfallData | null>(null);
  private explainabilitySubject = new BehaviorSubject<ExplainabilityData | null>(null);
  
  public shapValues$ = this.shapValuesSubject.asObservable();
  public waterfall$ = this.waterfallSubject.asObservable();
  public explainability$ = this.explainabilitySubject.asObservable();

  constructor(private http: HttpClient) {
    console.log('🔬 ExplainabilityService initialized');
    this.startRealTimeUpdates();
  }

  private startRealTimeUpdates() {
    console.log('⏰ Starting explainability updates every 3 seconds');
    
    // Mettre à jour immédiatement
    this.fetchExplainabilityData();
    
    // Puis toutes les 3 secondes
    interval(5000).subscribe(() => {
      this.fetchExplainabilityData();
    });
  }

  private fetchExplainabilityData() {
    console.log('🔍 Fetching explainability data from microservice...');
    
    // Récupérer les vraies données du microservice explainability
    this.http.get<ExplainabilityData>(`${this.API_URL}/api/v1/explainability/cluster/77`).subscribe({
      next: (data) => {
        console.log('✅ Explainability data received:', data);
        
        if (data) {
          this.updateSHAPValues(data);
          this.updateWaterfallChart(data);
          this.explainabilitySubject.next(data);
        }
      },
      error: (error) => {
        console.error('❌ Explainability API error:', error);
        this.logWaitingForData();
      }
    });
  }

  private updateSHAPValues(data: ExplainabilityData) {
    // Transformer les SHAP values du backend en format pour le graphique
    const shapArray: SHAPValue[] = Object.entries(data.shap_values).map(([feature, value]) => ({
      feature: this.formatFeatureName(feature),
      value: value,
      importance: Math.abs(value),
      impact: (value > 0 ? 'positive' : 'negative') as 'positive' | 'negative'
    })).sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

    this.shapValuesSubject.next(shapArray.slice(0, 10)); // Top 10 features
    console.log('📊 SHAP values updated:', shapArray.length, 'features');
  }

  private updateWaterfallChart(data: ExplainabilityData) {
    // Créer un waterfall chart avec les vraies données SHAP
    const features = Object.entries(data.shap_values).map(([feature, value]) => ({
      name: this.formatFeatureName(feature),
      value: value,
      contribution: value
    }));

    const waterfallData: WaterfallData = {
      base_value: 0.5, // Base probability
      features: features.slice(0, 8), // Top 8 features
      final_prediction: data.confidence
    };

    this.waterfallSubject.next(waterfallData);
    console.log('💧 Waterfall chart updated with', features.length, 'features');
  }

  private formatFeatureName(feature: string): string {
    // Formater les noms de features pour l'affichage
    const featureMap: Record<string, string> = {
      'rsrp_delta': 'RSRP Delta',
      'sinr_source': 'SINR Source', 
      'ho_history_1h': 'HO History (1h)',
      'cell_load': 'Cell Load',
      'ue_velocity': 'UE Velocity',
      'a3_offset': 'A3 Offset',
      'ttt_value': 'TTT Value',
      'rsrq_delta': 'RSRQ Delta',
      'cqi_source': 'CQI Source',
      'tx_power': 'TX Power'
    };
    
    return featureMap[feature] || feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  // No fallback data - only real backend SHAP values
  private logWaitingForData() {
    console.log('🔬 Waiting for real SHAP data from backend explainability service...');
  }

  // Méthodes pour accéder aux différents clusters
  getClusterExplainability(clusterId: number): Observable<ExplainabilityData> {
    return this.http.get<ExplainabilityData>(`${this.API_URL}/api/v1/explainability/cluster/${clusterId}`);
  }

  compareClusters(clusterIds: number[]): Observable<any> {
    return this.http.post<any>(`${this.API_URL}/api/v1/explainability/compare`, { cluster_ids: clusterIds });
  }
}




