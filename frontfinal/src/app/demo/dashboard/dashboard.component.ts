import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgApexchartsModule } from 'ng-apexcharts';
import { SharedModule } from 'src/app/theme/shared/shared.module';
import * as L from 'leaflet';
import { Chart, registerables } from 'chart.js';
import { RouterModule } from '@angular/router';
import { DonNextApiService } from '../../services/shared-api.service';
import { Subscription } from 'rxjs';
Chart.register(...registerables);

@Component({
  imports: [CommonModule, NgApexchartsModule, SharedModule, RouterModule],
  selector: 'app-dashboard',
  standalone: true,
  
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit, OnDestroy {

  private apiSubscription: Subscription = new Subscription();

  private refreshInterval: any;
  private mapInterval: any;
  private ueAnimInterval: any;

  map!: L.Map;
  private markers: any[] = [];
  private ueMarkers: any[] = [];
  private connectionLines: any[] = [];

  // ───────── KPI ───────── (Garder le même format mais avec données du backend)
  kpiCards = [
    { id: 'gnbs',       title: 'Active gNBs',      value: '142',      sub: '↑ 141 healthy',  subClass: 'text-success', valueClass: '',            data: [138,139,140,141,142,142,141,142,142,142], color: '#22c55e' },
    { id: 'alarms',     title: 'Active Alarms',     value: '7',        sub: '2 critical',     subClass: 'text-danger',  valueClass: 'text-danger', data: [3,4,3,5,6,7,7,8,7,7],                    color: '#ef4444' },
    { id: 'ho',         title: 'HO Success (now)',  value: '96.1%',    sub: 'Last 5 min',     subClass: 'text-muted',   valueClass: '',            data: [97,96,95,96,98,97,96,95,96,96],           color: '#4680ff' },
    { id: 'throughput', title: 'Throughput',        value: '2.4 Gbps', sub: '↑ Normal range', subClass: 'text-success', valueClass: '',            data: [2.1,2.2,2.3,2.3,2.4,2.4,2.3,2.4,2.4,2.4],color: '#22c55e' },
    { id: 'ues',        title: 'UEs Connected',     value: '8,742',    sub: 'Across network', subClass: 'text-muted',   valueClass: '',            data: [8600,8650,8700,8710,8720,8730,8740,8742,8742,8742], color: '#4680ff' }
  ];

  // ───────── ALARMS ───────── (Garder le même format mais avec données du backend)
  alarms = [
    { priority: 'P1', message: 'gNB-004 HO failure spike', time: '2m ago'  },
    { priority: 'P1', message: 'RSRP below threshold',     time: '8m ago'  },
    { priority: 'P2', message: 'Ping-pong anomaly',        time: '14m ago' },
    { priority: 'P2', message: 'Model drift alert',        time: '1h ago'  },
    { priority: 'P3', message: 'gNB restored',             time: '2h ago'  }
  ];

  // ───────── TABLE ───────── (Garder le même format mais avec données du backend)
  cells = [
    { id: 'gNB-001', zone: 'Zone A', status: 'Healthy',  ho: '98.2%', ues: 312, th: '180 Mbps', alarms: 0 },
    { id: 'gNB-002', zone: 'Zone B', status: 'Warning',  ho: '94.1%', ues: 428, th: '142 Mbps', alarms: 1 },
    { id: 'gNB-003', zone: 'Zone A', status: 'Healthy',  ho: '97.0%', ues: 285, th: '165 Mbps', alarms: 0 },
    { id: 'gNB-004', zone: 'Zone C', status: 'Critical', ho: '88.5%', ues: 201, th:  '88 Mbps', alarms: 2 }
  ];

  // ───────── ALERTES PAR ZONE ───────── (Données dynamiques du backend)
  alertZones: any[] = [];

  get totalAlerts(): number {
    return this.alertZones.reduce((sum, z) => sum + z.alerts.length, 0);
  }

  // ───────── ZONES ───────── (Garder les mêmes zones pour la carte)
  private readonly zones = [
    { lat: 51.520, lng: 7.460, value: 201, status: 'critical', label: 'gNB-004', ho: '88.5%', alarms: 2 },
    { lat: 51.510, lng: 7.500, value: 428, status: 'critical', label: 'gNB-002', ho: '94.1%', alarms: 1 },
    { lat: 51.500, lng: 7.430, value: 285, status: 'warning',  label: 'gNB-007', ho: '94.0%', alarms: 1 },
    { lat: 51.490, lng: 7.480, value: 367, status: 'warning',  label: 'gNB-005', ho: '95.5%', alarms: 1 },
    { lat: 51.530, lng: 7.420, value: 312, status: 'healthy', label: 'gNB-001', ho: '98.2%', alarms: 0 },
    { lat: 51.540, lng: 7.470, value: 285, status: 'healthy', label: 'gNB-003', ho: '97.0%', alarms: 0 },
    { lat: 51.520, lng: 7.440, value: 198, status: 'healthy', label: 'gNB-006', ho: '96.8%', alarms: 0 },
    { lat: 51.500, lng: 7.460, value: 342, status: 'warning',  label: 'gNB-008', ho: '93.2%', alarms: 1 }
  ];

  // ───────── CONNEXIONS ─────────
  private readonly connections: [[number, number], [number, number]][] = [
    [[51.520, 7.460], [51.540, 7.470]],
    [[51.520, 7.460], [51.520, 7.440]],
    [[51.520, 7.440], [51.530, 7.420]],
    [[51.520, 7.440], [51.500, 7.460]],
    [[51.500, 7.460], [51.490, 7.480]],
    [[51.500, 7.460], [51.500, 7.430]],
    [[51.510, 7.500], [51.490, 7.480]],
    [[51.510, 7.500], [51.540, 7.470]]
  ];

  // ───────── CHART HO ─────────
  hoChartSeries = [{ name: 'HO Success %', data: [97,96,95,96,98,97,96,95,97,97,88,95,96,97] }];
  hoChartOptions = { type: 'area', height: 220, toolbar: { show: false } };
  hoXaxis = { categories: ['0m','6m','12m','18m','24m','30m','36m','42m','48m','54m'] };
  hoYaxis = { min: 85, max: 100 };
  hoStroke = { curve: 'smooth' };
  hoFill   = { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.05 } };
  hoColors = ['#4680ff'];
  hoGrid   = { borderColor: '#e9ecef', strokeDashArray: 4 };
  hoTooltip = { y: { formatter: (val: number) => val.toFixed(1) + '%' } };
  hoAnnotations = {
    yaxis: [{ y: 95, borderColor: '#dc3545', strokeDashArray: 5,
      label: { text: 'Threshold', style: { color: '#fff', background: '#dc3545' } }
    }]
  };

  // ───────── CONSTRUCTOR ─────────
  constructor(private apiService: DonNextApiService, private cdr: ChangeDetectorRef) {}

  // ───────── INIT ─────────
  ngOnInit() {
    console.log('🚀 DashboardComponent initialized - Connecting to real backend data...');
    
    // Connect to real backend data only
    this.subscribeToAPIData();
    setTimeout(() => { this.initMap(); }, 0);
    setTimeout(() => { this.drawSparklines(); }, 300);
  }

  ngOnDestroy() {
    this.apiSubscription.unsubscribe();
    if (this.refreshInterval) clearInterval(this.refreshInterval);
    if (this.mapInterval)     clearInterval(this.mapInterval);
    if (this.ueAnimInterval)  clearInterval(this.ueAnimInterval);
    if (this.map)             this.map.remove();
  }

  // ───────── CONNEXION AU BACKEND ───────── (Garder le même format)
  private subscribeToAPIData() {
    console.log('📡 Subscribing to real-time backend data streams...');
    
    // S'abonner aux KPIs réels du backend - garder le même format
    const kpiSub = this.apiService.kpiData$.subscribe(kpis => {
      if (kpis) {
        // Mettre à jour seulement les valeurs, garder le même format
        this.kpiCards[0].value = kpis.gnbs.current.toString();
        this.kpiCards[0].sub = `↑ ${kpis.gnbs.healthy} healthy today`;
        this.kpiCards[1].value = kpis.alarms.active.toString();
        this.kpiCards[1].sub = `${kpis.alarms.critical} critical`;
        this.kpiCards[2].value = `${kpis.hoSuccess.current.toFixed(1)}%`;
        this.kpiCards[3].value = `${kpis.throughput.current.toFixed(1)} Gbps`;
        this.kpiCards[4].value = kpis.uesConnected.current.toLocaleString();
        
        console.log('📊 KPIs updated from backend - same format');
      } else {
        console.warn('⚠️ No KPI data from backend - using default values');
      }
    });

    // S'abonner aux cellules réelles du backend - garder le même format
    const cellsSub = this.apiService.cells$.subscribe(cells => {
      if (cells.length > 0) {
        // Mettre à jour seulement les 4 premières cellules pour garder le même format
        for (let i = 0; i < Math.min(4, cells.length); i++) {
          this.cells[i].id = cells[i].id;
          this.cells[i].zone = cells[i].zone;
          this.cells[i].status = cells[i].status;
          this.cells[i].ho = cells[i].ho;
          this.cells[i].ues = cells[i].ues;
          this.cells[i].th = cells[i].th;
          this.cells[i].alarms = cells[i].alarms;
        }
        
        console.log('📱 Cells updated from backend - same format');
      } else {
        console.warn('⚠️ No cell data from backend - using default values');
      }
    });

    // S'abonner aux alertes réelles du backend - grouper par zone
    const alertsSub = this.apiService.alerts$.subscribe(alerts => {
      if (alerts.length > 0) {
        // Mettre à jour les alertes simples
        for (let i = 0; i < Math.min(5, alerts.length); i++) {
          this.alarms[i].priority = alerts[i].priority;
          this.alarms[i].message = alerts[i].message;
          this.alarms[i].time = alerts[i].time;
        }
        
        // Grouper les alertes par zone avec les vraies données du backend
        this.alertZones = this.groupAlertsByZoneFromBackend(alerts);
        
        console.log('🚨 REAL alerts from backend grouped by zone');
        console.log('📍 Zones:', this.alertZones.length, 'alert zones created');
        console.log('🎯 alertZones array:', this.alertZones);
        this.alertZones.forEach((zone, index) => {
          console.log(`  Zone ${index}: ${zone.zone} - ${zone.alerts.length} alerts - status: ${zone.status}`);
          console.log(`    Alerts:`, zone.alerts);
        });
        
        // Forcer la détection des changements Angular
        this.cdr.detectChanges();
        console.log('🔄 Angular change detection forced');
        
        setTimeout(() => {
          console.log('🔄 Forcing Angular change detection...');
          console.log('📊 Final alertZones length:', this.alertZones.length);
          this.cdr.detectChanges();
        }, 100);
      } else {
        console.warn('⚠️ No alert data from backend - waiting for real alerts');
      }
    });

    this.apiSubscription.add(kpiSub);
    this.apiSubscription.add(cellsSub);
    this.apiSubscription.add(alertsSub);
  }

  // ───────── GROUP ALERTS BY ZONE FROM BACKEND ─────────
  private groupAlertsByZoneFromBackend(alerts: any[]): any[] {
    const zones: {[key: string]: any[]} = {};
    
    console.log('🔍 Grouping REAL backend alerts by zone:', alerts.length, 'alerts');
    
    // Grouper les alertes par zone en utilisant les coordonnées GPS réelles
    alerts.forEach(alert => {
      const zone = this.getAlertZoneFromCoordinates(alert);
      if (!zones[zone]) {
        zones[zone] = [];
      }
      zones[zone].push({
        gnb: alert.gnb,
        priority: alert.priority === 'P1' ? 1 : alert.priority === 'P2' ? 2 : 3,
        message: alert.message,
        time: alert.time
      });
    });
    
    // Convertir au format attendu par le template
    const result = Object.keys(zones).map(zoneName => {
      const zoneAlerts = zones[zoneName];
      const severity = this.getZoneSeverityFromAlerts(zoneAlerts);
      
      return {
        zone: zoneName,
        status: severity,
        alerts: zoneAlerts
      };
    });
    
    console.log('📍 REAL alert zones created from backend data:', result.length, 'zones');
    return result;
  }

  // ───────── DÉTERMINER LA ZONE D'UNE ALERTE (basée sur le cluster) ─────────
  private getAlertZoneFromCoordinates(alert: any): string {
    // Utiliser le gNB/cluster ID comme zone
    return alert.gnb || alert.cluster_id || 'Unknown';
  }

  // ───────── DÉTERMINER LA ZONE D'UNE CELLULE (basée sur le cluster) ─────────
  private getCellZoneFromCoordinates(cell: any): string {
    // Utiliser l'ID du cluster comme zone
    return cell.id || cell.cluster_id || 'Unknown';
  }

  // ───────── DETERMINE ZONE SEVERITY FROM ALERTS ─────────
  private getZoneSeverityFromAlerts(alerts: any[]): string {
    if (alerts.some(a => a.priority === 1)) return 'critical';
    if (alerts.some(a => a.priority === 2)) return 'warning';
    return 'healthy';
  }

  // ───────── KPI UPDATE ─────────
  private refreshData() {
    const delta = (Math.random() - 0.5) * 0.5;
    const current = parseFloat(this.kpiCards[2].value);
    this.kpiCards[2].value = Math.max(93, Math.min(99, current + delta)).toFixed(1) + '%';
  }

  // ───────── SPARKLINES ─────────
  drawSparklines() {
    this.kpiCards.forEach(kpi => {
      const canvas = document.getElementById('spark-' + kpi.id) as HTMLCanvasElement;
      if (!canvas) return;
      new Chart(canvas, {
        type: 'line',
        data: {
          labels: kpi.data.map(() => ''),
          datasets: [{
            data: kpi.data,
            borderColor: kpi.color,
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.4,
            fill: true,
            backgroundColor: kpi.color + '22'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 800 },
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
          scales: { x: { display: false }, y: { display: false } }
        }
      });
    });
  }

  // ───────── MAP INIT ─────────
  initMap() {
    this.map = L.map('map', { zoomControl: true }).setView([51.513, 7.463], 11);
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: '&copy; Esri'
    }).addTo(this.map);
    this.drawConnections();
    this.drawZones();
    this.startUeAnimation();
    this.startMapLiveUpdates();
  }

  // ───────── CONNEXIONS ─────────
  drawConnections() {
    this.connectionLines.forEach(l => this.map.removeLayer(l));
    this.connectionLines = [];
    this.connections.forEach(line => {
      const pl = L.polyline(line, {
        color: '#3b82f6', weight: 1.5, dashArray: '8, 6', opacity: 0.6
      }).addTo(this.map);
      this.connectionLines.push(pl);
    });
  }

  // ───────── ZONES / MARKERS ─────────
  drawZones() {
    this.markers.forEach(m => this.map.removeLayer(m));
    this.markers = [];

    const colors: any = {
      healthy:  { fill: '#22c55e' },
      warning:  { fill: '#f59e0b' },
      critical: { fill: '#ef4444' }
    };

    this.zones.forEach(zone => {
      const c = colors[zone.status];

      const circle = L.circle([zone.lat, zone.lng], {
        radius: 1500, color: c.fill, fillColor: c.fill, fillOpacity: 0.15, weight: 2.5
      }).addTo(this.map);

      const halo = L.circle([zone.lat, zone.lng], {
        radius: 1600, color: c.fill, fillColor: 'transparent',
        fillOpacity: 0, weight: 1, dashArray: '5, 5', opacity: 0.5
      }).addTo(this.map);

      const alertIcon = zone.status !== 'healthy' ? `<div class="marker-alert">!</div>` : '';

      const icon = L.divIcon({
        className: '',
        iconSize: [54, 54],
        iconAnchor: [27, 27],
        html: `<div class="gnb-marker ${zone.status}">
                 <span class="gnb-value">${zone.value}</span>
                 ${alertIcon}
               </div>`
      });

      const marker = L.marker([zone.lat, zone.lng], { icon }).addTo(this.map);
      marker.bindTooltip(
        `<b>${zone.label}</b><br>
         UEs connectés : <b>${zone.value}</b><br>
         HO Success : <b>${zone.ho}</b><br>
         Alarms : <b>${zone.alarms}</b><br>
         Status : <b>${zone.status}</b>`,
        { className: 'noc-tooltip', direction: 'top', offset: [0, -28] }
      );

      this.markers.push(halo, circle, marker);
    });
  }

  // ───────── UE ANIMATION ─────────
  startUeAnimation() {
    const uePositions: [number, number][] = [
      [51.521, 7.461], [51.515, 7.468], [51.508, 7.488],
      [51.502, 7.445], [51.496, 7.472], [51.527, 7.433],
      [51.535, 7.468], [51.518, 7.448], [51.503, 7.462]
    ];
    uePositions.forEach(p => {
      const ue = L.circleMarker(p, {
        radius: 4, color: '#60a5fa', fillColor: '#93c5fd', fillOpacity: 1, weight: 1.5
      }).addTo(this.map);
      this.ueMarkers.push(ue);
    });
    this.ueAnimInterval = setInterval(() => {
      this.ueMarkers.forEach((ue, i) => {
        const base = uePositions[i];
        ue.setLatLng([base[0] + (Math.random() - 0.5) * 0.003, base[1] + (Math.random() - 0.5) * 0.003]);
      });
    }, 1500);
  }

  
  // ───────── LIVE UPDATE ─────────
  startMapLiveUpdates() {
    this.mapInterval = setInterval(() => {
      this.zones.forEach((zone: any) => {
        const r = Math.random();
        if (zone.status === 'healthy' && r < 0.05)       zone.status = 'warning';
        else if (zone.status === 'warning' && r < 0.15)  zone.status = 'healthy';
        else if (zone.status === 'critical' && r < 0.08) zone.status = 'warning';
      });
      this.drawZones();
    }, 5000);
  }
}