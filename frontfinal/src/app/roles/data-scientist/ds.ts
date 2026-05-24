import { Injectable } from '@angular/core';

export interface ModelRecord {
  name: string; version: string; stage: 'Production'|'Staging'|'Archived';
  auc: number; f1: number; recall: number; trainedDate: string;
}

export interface RunRecord {
  runId: string; model: string; params: string;
  auc: number; f1: number; duration: string;
  status: 'Production'|'Staging'|'Completed'|'Archived';
}

@Injectable({ providedIn: 'root' })
export class DsService {

  getModels(): ModelRecord[] {
    return [
      { name:'XGBoost HO Classifier', version:'v2.3', stage:'Production',
        auc:0.943, f1:0.921, recall:0.902, trainedDate:'Apr 12' },
      { name:'LSTM Sequence Model',   version:'v1.2', stage:'Staging',
        auc:0.951, f1:0.934, recall:0.916, trainedDate:'Apr 18' },
      { name:'Random Forest Baseline',version:'v1.0', stage:'Archived',
        auc:0.892, f1:0.878, recall:0.856, trainedDate:'Mar 28' },
    ];
  }

  getRuns(): RunRecord[] {
    return [
      { runId:'run_08f2a', model:'LSTM v1.2', params:'lr=0.001, epochs=50',
        auc:0.951, f1:0.934, duration:'2h 14m', status:'Staging' },
      { runId:'run_07c1b', model:'LSTM v1.1', params:'lr=0.001, epochs=40',
        auc:0.942, f1:0.918, duration:'1h 52m', status:'Completed' },
      { runId:'run_06d4e', model:'XGB v2.3',  params:'n_est=500, depth=6',
        auc:0.943, f1:0.921, duration:'18m',    status:'Production' },
      { runId:'run_05a3c', model:'XGB v2.2',  params:'n_est=400, depth=5',
        auc:0.928, f1:0.906, duration:'14m',    status:'Archived' },
    ];
  }

  getDriftScores() {
    return [
      { label:'Feature Drift Score', value:72, color:'#F59E0B' },
      { label:'Label Drift Score',   value:45, color:'#10B981' },
      { label:'PSI (RSRP)',          value:82, color:'#EF4444' },
      { label:'PSI (SINR)',          value:38, color:'#10B981' },
    ];
  }
}