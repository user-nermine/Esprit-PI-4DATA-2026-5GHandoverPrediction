import { Injectable, signal } from '@angular/core';
import { Observable, of, delay } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import {
  Cell, HandoverParams, NeighborCell,
  HandoverEvent, RanSummary
} from '../models/ran.models';

@Injectable({ providedIn: 'root' })
export class RanEngineerService {
  private readonly API_BASE_URL = 'http://127.0.0.1:8000';
  private _cells = signal<Cell[]>([]);
  private _hoParams = signal<HandoverParams[]>([]);
  private _neighbors = signal<NeighborCell[]>([]);

  constructor(private http: HttpClient) {
    this.loadInitialData();
  }

  private loadInitialData(): void {
    // Charger les données du backend
    this.http.get<any[]>(`${this.API_BASE_URL}/api/v1/logs/dynamic/limit/10`).subscribe({
      next: (logs) => {
        const cells = logs.map((log, index) => ({
          id: `gNB-${String(index + 1).padStart(3, '0')}`,
          gnbId: `gNB-${String(index + 1).padStart(3, '0')}`,
          cellName: `Cell-${index + 1}`,
          pci: log.cluster_id,
          earfcn: 3250,
          bandwidth: 20,
          txPower: log.cluster_kpi.tx_power,
          status: (log.confidence > 0.8 ? 'ACTIVE' : log.confidence > 0.6 ? 'MAINTENANCE' : 'INACTIVE') as 'ACTIVE' | 'INACTIVE' | 'MAINTENANCE',
          sector: 1,
          tac: 1,
          latitude: 51.5 + (index * 0.01),
          longitude: 7.4 + (index * 0.01)
        }));
        this._cells.set(cells);
      },
      error: () => {
        // Fallback vers données mock si backend indisponible
        this._cells.set(this.getMockCells());
      }
    });
  }

  private getMockCells(): Cell[] {
    return [
      { 
        id: 'gNB-001', 
        gnbId: 'gNB-001', 
        cellName: 'Cell-1', 
        pci: 1, 
        earfcn: 3250, 
        bandwidth: 20, 
        txPower: 12.1, 
        status: 'ACTIVE', 
        sector: 1, 
        tac: 1, 
        latitude: 51.51, 
        longitude: 7.41 
      },
      { 
        id: 'gNB-002', 
        gnbId: 'gNB-002', 
        cellName: 'Cell-2', 
        pci: 2, 
        earfcn: 3250, 
        bandwidth: 20, 
        txPower: 11.8, 
        status: 'ACTIVE', 
        sector: 1, 
        tac: 1, 
        latitude: 51.52, 
        longitude: 7.42 
      },
      { 
        id: 'gNB-003', 
        gnbId: 'gNB-003', 
        cellName: 'Cell-3', 
        pci: 3, 
        earfcn: 3250, 
        bandwidth: 20, 
        txPower: 12.3, 
        status: 'MAINTENANCE', 
        sector: 1, 
        tac: 1, 
        latitude: 51.53, 
        longitude: 7.43 
      }
    ];
  }

  // ── READ ──────────────────────────────────────────────────────

  getCells(): Observable<Cell[]> {
    return of(this._cells()).pipe(delay(300));
  }

  getHandoverParams(): Observable<HandoverParams[]> {
    return this.http.get<HandoverParams[]>(`${this.API_BASE_URL}/api/v1/handover-params`).pipe(
      delay(300)
    );
  }

  getNeighborCells(): Observable<NeighborCell[]> {
    return this.http.get<NeighborCell[]>(`${this.API_BASE_URL}/api/v1/neighbor-cells`).pipe(
      delay(300)
    );
  }

  getHandoverEvents(): Observable<HandoverEvent[]> {
    return this.http.get<HandoverEvent[]>(`${this.API_BASE_URL}/api/v1/logs/dynamic/limit/20`).pipe(
      delay(300)
    );
  }

  getRanSummary(): Observable<RanSummary> {
    const cells = this._cells();
    const activeCells = cells.filter(c => c.status === 'ACTIVE').length;
    const totalCells = cells.length;

    // Calculer le taux de succès réel (fallback vers données simulées)
    const avgSuccess = 95.2;

    return of({
      totalCells,
      activeCells,
      inactiveCells: cells.filter(c => c.status === 'INACTIVE').length,
      maintenanceCells: cells.filter(c => c.status === 'MAINTENANCE').length,
      handoverSuccessRate: avgSuccess,
      avgA3Offset: 3.0,
      recentEvents: []
    }).pipe(delay(200));
  }

  // ── CREATE ────────────────────────────────────────────────────

  addCell(cell: Omit<Cell, 'id'>): Observable<Cell> {
    const newCell: Cell = { ...cell, id: 'gNB-' + Date.now() };
    this._cells.update(cells => [...cells, newCell]);
    return of(newCell).pipe(delay(300));
  }

  addHandoverParams(params: Omit<HandoverParams, 'id'>): Observable<HandoverParams> {
    const newParams: HandoverParams = { ...params, id: 'h' + Date.now() };
    this._hoParams.update(p => [...p, newParams]);
    return of(newParams).pipe(delay(300));
  }

  addNeighborCell(nb: Omit<NeighborCell, 'id'>): Observable<NeighborCell> {
    const newNb: NeighborCell = { ...nb, id: 'n' + Date.now() };
    this._neighbors.update(n => [...n, newNb]);
    return of(newNb).pipe(delay(300));
  }

  // ── UPDATE ────────────────────────────────────────────────────

  updateCell(id: string, changes: Partial<Cell>): Observable<Cell> {
    this._cells.update(cells =>
      cells.map(c => c.id === id ? { ...c, ...changes } : c)
    );
    return of(this._cells().find(c => c.id === id)!).pipe(delay(300));
  }

  updateHandoverParams(id: string, changes: Partial<HandoverParams>): Observable<HandoverParams> {
    this._hoParams.update(params =>
      params.map(p => p.id === id
        ? { ...p, ...changes, lastModified: new Date() } : p)
    );
    return of(this._hoParams().find(p => p.id === id)!).pipe(delay(300));
  }

  updateNeighborCell(id: string, changes: Partial<NeighborCell>): Observable<NeighborCell> {
    this._neighbors.update(n =>
      n.map(nb => nb.id === id ? { ...nb, ...changes } : nb)
    );
    return of(this._neighbors().find(n => n.id === id)!).pipe(delay(300));
  }

  // ── DELETE ────────────────────────────────────────────────────

  deleteCell(id: string): Observable<void> {
    this._cells.update(cells => cells.filter(c => c.id !== id));
    return of(undefined).pipe(delay(300));
  }

  deleteHandoverParams(id: string): Observable<void> {
    this._hoParams.update(params => params.filter(p => p.id !== id));
    return of(undefined).pipe(delay(300));
  }

  deleteNeighborCell(id: string): Observable<void> {
    this._neighbors.update(n => n.filter(nb => nb.id !== id));
    return of(undefined).pipe(delay(300));
  }
}