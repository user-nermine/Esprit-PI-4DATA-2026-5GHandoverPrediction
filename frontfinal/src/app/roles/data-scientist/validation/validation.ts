import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule],
  selector: 'app-validation',
  templateUrl: './validation.html',
  styleUrls: ['./validation.scss']
})
export class ValidationComponent {
  decisionNote = '';

  models = ['HO Prediction', 'Signal Degradation', 'Next Best Cell', 'Handover Type'];
  selectedModel = 'HO Prediction';

  approve(): void {
    alert('TabNet v1.0 approved for Canary Deployment (10% traffic).');
  }

  reject(): void {
    alert('Model rejected. Optimization request sent to ML team.');
  }

  runAbTest(): void {
    alert('A/B Test launched: XGBoost v2.3 vs TabNet v1.0 (50/50 split).');
  }
}
