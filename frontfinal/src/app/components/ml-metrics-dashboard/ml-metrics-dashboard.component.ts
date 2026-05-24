import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-ml-metrics-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="ml-metrics-dashboard">
      <div class="dashboard-header">
        <h3>🤖 ML Models Performance</h3>
        <div class="status-indicator active">
          <span class="pulse"></span>
          Active
        </div>
      </div>

      <div class="models-grid">
        <!-- DSO1 - Handover Binaire -->
        <div class="model-card good">
          <div class="model-header">
            <span class="model-name">DSO1 - Handover</span>
            <span class="model-badge binary">Binary</span>
          </div>
          <div class="metrics-grid">
            <div class="metric">
              <span class="metric-label">F1 Score</span>
              <span class="metric-value">89.2%</span>
            </div>
            <div class="metric">
              <span class="metric-label">Accuracy</span>
              <span class="metric-value">87.8%</span>
            </div>
            <div class="metric">
              <span class="metric-label">AUC-ROC</span>
              <span class="metric-value">0.942</span>
            </div>
            <div class="metric">
              <span class="metric-label">Precision</span>
              <span class="metric-value">90.6%</span>
            </div>
          </div>
          <div class="best-model">Best: XGBoost</div>
        </div>

        <!-- DSO2 - RSRP Drop -->
        <div class="model-card good">
          <div class="model-header">
            <span class="model-name">DSO2 - RSRP Drop</span>
            <span class="model-badge multiclass">Multiclass</span>
          </div>
          <div class="metrics-grid">
            <div class="metric">
              <span class="metric-label">F1 Score</span>
              <span class="metric-value">91.5%</span>
            </div>
            <div class="metric">
              <span class="metric-label">Accuracy</span>
              <span class="metric-value">89.7%</span>
            </div>
            <div class="metric">
              <span class="metric-label">Precision</span>
              <span class="metric-value">93.3%</span>
            </div>
            <div class="metric">
              <span class="metric-label">Recall</span>
              <span class="metric-value">94.2%</span>
            </div>
          </div>
          <div class="best-model">Best: LightGBM</div>
        </div>

        <!-- DSO3 - Next Cell -->
        <div class="model-card good">
          <div class="model-header">
            <span class="model-name">DSO3 - Next Cell</span>
            <span class="model-badge multiclass">Multiclass</span>
          </div>
          <div class="metrics-grid">
            <div class="metric">
              <span class="metric-label">Top-1 Acc.</span>
              <span class="metric-value">78.5%</span>
            </div>
            <div class="metric">
              <span class="metric-label">Top-3 Acc.</span>
              <span class="metric-value">97.3%</span>
            </div>
            <div class="metric">
              <span class="metric-label">Precision</span>
              <span class="metric-value">76.2%</span>
            </div>
            <div class="metric">
              <span class="metric-label">Recall</span>
              <span class="metric-value">80.8%</span>
            </div>
          </div>
          <div class="best-model">Best: XGBoost</div>
        </div>

        <!-- DSO4 - HO Type -->
        <div class="model-card good">
          <div class="model-header">
            <span class="model-name">DSO4 - HO Type</span>
            <span class="model-badge multiclass">Multiclass</span>
          </div>
          <div class="metrics-grid">
            <div class="metric">
              <span class="metric-label">F1 Score</span>
              <span class="metric-value">71.5%</span>
            </div>
            <div class="metric">
              <span class="metric-label">Accuracy</span>
              <span class="metric-value">69.8%</span>
            </div>
            <div class="metric">
              <span class="metric-label">Precision</span>
              <span class="metric-value">73.2%</span>
            </div>
            <div class="metric">
              <span class="metric-label">Recall</span>
              <span class="metric-value">70.5%</span>
            </div>
          </div>
          <div class="best-model">Best: RandomForest</div>
        </div>
      </div>

      <div class="dashboard-footer">
        <div class="summary">
          <span class="summary-item">
            <strong>4</strong> Models Active
          </span>
          <span class="summary-item">
            <strong>85.7%</strong> Avg Performance
          </span>
          <span class="summary-item">
            <strong>Real-time</strong> Processing
          </span>
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./ml-metrics-dashboard.component.scss']
})
export class MlMetricsDashboardComponent implements OnInit {

  constructor() { }

  ngOnInit(): void {
    // Initialisation avec données statiques
  }
}
