import { Component } from '@angular/core';
import { ChartData, ChartOptions } from 'chart.js';
import { CommonModule }  from '@angular/common';
import { CardComponent } from 'src/app/theme/shared/components/card/card.component';
import { BaseChartDirective } from 'ng2-charts'; 
@Component({
  imports: [
    CommonModule,
    CardComponent,
    BaseChartDirective
  ],
  selector: 'app-deployment',
  templateUrl: './deployment.html'
})
export class DeploymentComponent {

  // Canary state
  canaryPercent = 10;   // starts at 10%
  stage         = 1;    // 1 of 3

  steps = [
    { label:'10% Traffic', sub:'Validating' },
    { label:'50% Traffic', sub:'Pending' },
    { label:'100% Traffic',sub:'Full rollout' },
  ];

  timeline = [
    { icon:'✓', color:'#10B981', title:'Canary started — 10% traffic',
      time:'Apr 20, 09:00', desc:'LSTM v1.2 deployed to 10% traffic slice' },
    { icon:'✓', color:'#10B981', title:'Validation approved',
      time:'Apr 19, 15:30', desc:'All metrics passed. AUC 0.951, F1 0.934' },
    { icon:'●', color:'#3B82F6', title:'Retraining completed',
      time:'Apr 18, 22:00', desc:'LSTM v1.2 trained on 92,140 samples' },
  ];

  canaryChartData: ChartData<'bar'> = {
    labels: ['AUC-ROC','F1-Score','Recall','Precision'],
    datasets: [
      { label:'XGB v2.3 (Prod)',     data:[0.943,0.921,0.902,0.941],
        backgroundColor:'#3B82F6', borderRadius: 4 },
      { label:'LSTM v1.2 (Canary)',  data:[0.949,0.929,0.913,0.948],
        backgroundColor:'#10B981', borderRadius: 4 },
    ]
  };
  canaryChartOptions: ChartOptions<'bar'> = {
    responsive: true,
    scales: { y: { min: 0.88, max: 1.0 } },
    plugins: { legend: { display: true, position: 'bottom' } }
  };

  promote() {
    if (this.stage === 1) { this.canaryPercent = 50; this.stage = 2; }
    else if (this.stage === 2) { this.canaryPercent = 100; this.stage = 3; }
    // TODO: POST /api/deployment/canary/promote  { traffic: this.canaryPercent }
  }

  rollback() {
    if (confirm('Rollback to XGBoost v2.3?')) {
      this.canaryPercent = 0;
      this.stage = 0;
      // TODO: POST /api/deployment/rollback
      alert('Rollback initiated. XGB v2.3 restored to 100% traffic.');
    }
  }
}