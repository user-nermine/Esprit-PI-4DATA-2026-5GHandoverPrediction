import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject, Observable } from 'rxjs';
import { StreamlitService } from './streamlit.service';

export interface SharedData {
  anomalyMetrics: any;
  kpiMetrics: any;
  diagnosisData: any;
  optimizationData: any;
  lastUpdate: Date;
  isUpdating: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class DataSyncService {
  private sharedData = new BehaviorSubject<SharedData>({
    anomalyMetrics: null,
    kpiMetrics: null,
    diagnosisData: null,
    optimizationData: null,
    lastUpdate: new Date(),
    isUpdating: false
  });

  private dataUpdateTrigger = new Subject<void>();
  private refreshInterval: any;

  constructor(private streamlitService: StreamlitService) {
    this.startAutoSync();
  }

  // Observable pour les composants qui veulent écouter les changements
  public get sharedData$(): Observable<SharedData> {
    return this.sharedData.asObservable();
  }

  public get dataUpdateTrigger$(): Observable<void> {
    return this.dataUpdateTrigger.asObservable();
  }

  // Démarrer la synchronisation automatique
  private startAutoSync(): void {
    this.refreshInterval = setInterval(() => {
      this.syncAllData();
    }, 5000); // 5 secondes

    // Charger les données initiales
    this.syncAllData();
  }

  // Synchroniser toutes les données
  private syncAllData(): void {
    const currentData = this.sharedData.value;
    this.sharedData.next({
      ...currentData,
      isUpdating: true
    });

    // Lancer tous les appels API en parallèle
    Promise.all([
      this.fetchAnomalyData(),
      this.fetchKpiData(),
      this.fetchDiagnosisData(),
      this.fetchOptimizationData()
    ]).then(([anomalyData, kpiData, diagnosisData, optimizationData]) => {
      const updatedData: SharedData = {
        anomalyMetrics: anomalyData,
        kpiMetrics: kpiData,
        diagnosisData: diagnosisData,
        optimizationData: optimizationData,
        lastUpdate: new Date(),
        isUpdating: false
      };

      this.sharedData.next(updatedData);
      this.dataUpdateTrigger.next(); // Notifier tous les composants

      console.log('🔄 Synchronisation complète - Toutes les interfaces mises à jour');
    }).catch(error => {
      console.error('❌ Erreur de synchronisation:', error);
      const currentData = this.sharedData.value;
      this.sharedData.next({
        ...currentData,
        isUpdating: false
      });
    });
  }

  // Méthodes individuelles pour chaque type de données
  private async fetchAnomalyData(): Promise<any> {
    return new Promise((resolve, reject) => {
      this.streamlitService.getAnomalyMetrics().subscribe({
        next: (data) => resolve(data),
        error: (error) => reject(error)
      });
    });
  }

  private async fetchKpiData(): Promise<any> {
    return new Promise((resolve, reject) => {
      this.streamlitService.getKpiMetrics().subscribe({
        next: (data) => resolve(data),
        error: (error) => reject(error)
      });
    });
  }

  private async fetchDiagnosisData(): Promise<any> {
    return new Promise((resolve, reject) => {
      this.streamlitService.getDiagnosisData().subscribe({
        next: (data) => resolve(data),
        error: (error) => reject(error)
      });
    });
  }

  private async fetchOptimizationData(): Promise<any> {
    return new Promise((resolve, reject) => {
      this.streamlitService.getOptimizationRecommendations().subscribe({
        next: (data) => resolve(data),
        error: (error) => reject(error)
      });
    });
  }

  // Forcer une synchronisation manuelle (si nécessaire)
  public forceSync(): void {
    console.log('🔄 Forçage de la synchronisation manuelle');
    this.syncAllData();
  }

  // Obtenir des données spécifiques
  public getAnomalyMetrics(): Observable<any> {
    return new Observable(observer => {
      const subscription = this.sharedData$.subscribe(data => {
        if (data.anomalyMetrics) {
          observer.next(data.anomalyMetrics);
        }
      });
      return () => subscription.unsubscribe();
    });
  }

  public getKpiMetrics(): Observable<any> {
    return new Observable(observer => {
      const subscription = this.sharedData$.subscribe(data => {
        if (data.kpiMetrics) {
          observer.next(data.kpiMetrics);
        }
      });
      return () => subscription.unsubscribe();
    });
  }

  public getDiagnosisData(): Observable<any> {
    return new Observable(observer => {
      const subscription = this.sharedData$.subscribe(data => {
        if (data.diagnosisData) {
          observer.next(data.diagnosisData);
        }
      });
      return () => subscription.unsubscribe();
    });
  }

  public getOptimizationData(): Observable<any> {
    return new Observable(observer => {
      const subscription = this.sharedData$.subscribe(data => {
        if (data.optimizationData) {
          observer.next(data.optimizationData);
        }
      });
      return () => subscription.unsubscribe();
    });
  }

  // Nettoyer lors de la destruction
  public ngOnDestroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }
}
