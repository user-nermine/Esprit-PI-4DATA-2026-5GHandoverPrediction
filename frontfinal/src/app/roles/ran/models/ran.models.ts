export interface Cell {
  id: string;
  gnbId: string;
  cellName: string;
  pci: number;
  earfcn: number;
  bandwidth: number;
  txPower: number;
  status: 'ACTIVE' | 'INACTIVE' | 'MAINTENANCE';
  sector: number;
  tac: number;
  latitude: number;
  longitude: number;
}

export interface HandoverParams {
  id: string;
  cellId: string;
  cellName: string;
  a3Offset: number;
  hysteresis: number;
  ttt: number;
  handoverAlgorithm: 'A3' | 'A4' | 'A5';
  lastModified: Date;
  modifiedBy: string;
}

export interface NeighborCell {
  id: string;
  sourceCellId: string;
  sourceCellName: string;
  targetCellId: string;
  targetCellName: string;
  targetPci: number;
  targetEarfcn: number;
  noHo: boolean;
  noRemove: boolean;
  relationStatus: 'ACTIVE' | 'INACTIVE';
}

export interface HandoverEvent {
  id: string;
  timestamp: Date;
  sourceCell: string;
  targetCell: string;
  ueId: string;
  eventType: 'HANDOVER_SUCCESS' | 'HANDOVER_FAILURE' | 'PING_PONG' | 'TOO_LATE' | 'TOO_EARLY';
  rsrp: number;
  rsrq: number;
  sinr: number;
}

export interface RanSummary {
  totalCells: number;
  activeCells: number;
  inactiveCells: number;
  maintenanceCells: number;
  handoverSuccessRate: number;
  avgA3Offset: number;
  recentEvents: HandoverEvent[];
}