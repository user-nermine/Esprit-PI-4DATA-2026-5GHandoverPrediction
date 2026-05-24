import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { RanEngineerService } from '../services/ran-engineer.service';
import { HandoverParams } from '../models/ran.models';

@Component({
  selector: 'app-handover-params',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './handover-params.component.html',
  styleUrls: ['./handover-params.component.scss']
})
export class HandoverParamsComponent implements OnInit {

  params: HandoverParams[] = [];
  loading = true;
  showModal = false;
  isEditMode = false;
  saving = false;

  formData: Partial<HandoverParams> = {};

  tttOptions = [0, 40, 64, 80, 100, 128, 160, 256, 320, 480, 512, 640];
  algorithmOptions = ['A3', 'A4', 'A5'] as const;

  constructor(private ranService: RanEngineerService) {}

  ngOnInit(): void {
    this.loadParams();
  }

  loadParams(): void {
    this.loading = true;
    this.ranService.getHandoverParams().subscribe({
      next: (data) => { this.params = data; this.loading = false; }
    });
  }

  openAddModal(): void {
    this.isEditMode = false;
    this.formData = {
      a3Offset: 3, hysteresis: 1, ttt: 160,
      handoverAlgorithm: 'A3',
      modifiedBy: 'ran.engineer@telecom.tn'
    };
    this.showModal = true;
  }

  openEditModal(p: HandoverParams): void {
    this.isEditMode = true;
    this.formData = { ...p };
    this.showModal = true;
  }

  closeModal(): void {
    this.showModal = false;
    this.formData = {};
  }

  saveParams(): void {
    this.saving = true;
    if (this.isEditMode && this.formData.id) {
      this.ranService.updateHandoverParams(this.formData.id, this.formData).subscribe({
        next: () => { this.saving = false; this.closeModal(); this.loadParams(); }
      });
    } else {
      this.ranService.addHandoverParams(
        this.formData as Omit<HandoverParams, 'id'>
      ).subscribe({
        next: () => { this.saving = false; this.closeModal(); this.loadParams(); }
      });
    }
  }

  deleteParams(id: string): void {
    if (confirm('Delete these handover parameters?')) {
      this.ranService.deleteHandoverParams(id).subscribe(() => this.loadParams());
    }
  }
}