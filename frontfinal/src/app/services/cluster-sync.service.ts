import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { RANCellData } from './donext-api.service';

export interface ClusterSyncData {
  currentClusterId: string | number;
  currentCluster: RANCellData | null;
  allClusters: RANCellData[];
  lastUpdate: string;
}

@Injectable({
  providedIn: 'root'
})
export class ClusterSyncService {
  private currentClusterSubject = new BehaviorSubject<ClusterSyncData>({
    currentClusterId: null,
    currentCluster: null,
    allClusters: [],
    lastUpdate: new Date().toLocaleTimeString()
  });

  public currentCluster$: Observable<ClusterSyncData> = this.currentClusterSubject.asObservable();

  constructor() { }

  /**
   * Update the current cluster and notify all subscribers
   */
  updateCurrentCluster(clusterId: string | number, cluster: RANCellData | null, allClusters: RANCellData[]): void {
    const syncData: ClusterSyncData = {
      currentClusterId: clusterId,
      currentCluster: cluster,
      allClusters: allClusters,
      lastUpdate: new Date().toLocaleTimeString()
    };

    this.currentClusterSubject.next(syncData);
  }

  /**
   * Get current cluster data
   */
  getCurrentCluster(): ClusterSyncData {
    return this.currentClusterSubject.value;
  }

  /**
   * Filter clusters by GPS availability
   */
  getClustersWithGPS(clusters: RANCellData[]): RANCellData[] {
    return clusters.filter(cluster => 
      cluster.latitude !== undefined && 
      cluster.longitude !== undefined && 
      cluster.latitude !== null && 
      cluster.longitude !== null
    );
  }

  /**
   * Filter clusters without GPS
   */
  getClustersWithoutGPS(clusters: RANCellData[]): RANCellData[] {
    return clusters.filter(cluster => 
      cluster.latitude === undefined || 
      cluster.longitude === undefined || 
      cluster.latitude === null || 
      cluster.longitude === null
    );
  }

  /**
   * Get clusters by category
   */
  getClustersByCategory(clusters: RANCellData[], categoryId: number): RANCellData[] {
    return clusters.filter(cluster => cluster.cluster_id === categoryId);
  }
}
