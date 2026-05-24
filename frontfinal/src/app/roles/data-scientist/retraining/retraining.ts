import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule],
  selector: 'app-retraining',
  templateUrl: './retraining.html',
  styleUrls: ['./retraining.scss']
})
export class RetrainingComponent {
  activeTab = 'features';

  triggerMode = 'Manual';
  targetDso   = 'DSO1 — HO Prediction (TabNet)';
  datasetSize = 'Last 30 days (48,320 samples)';
  modelArch   = 'TabNet (current best)';
  rationale   = '';

  triggerRetraining(): void {
    alert(`Retraining triggered!\nMode: ${this.triggerMode}\nDSO: ${this.targetDso}\nModel: ${this.modelArch}`);
  }
}
