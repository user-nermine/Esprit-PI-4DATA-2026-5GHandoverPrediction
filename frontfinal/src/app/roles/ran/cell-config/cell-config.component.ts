import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { RanEngineerService } from '../services/ran-engineer.service';
import { Cell } from '../models/ran.models';

@Component({
  selector: 'app-cell-config',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './cell-config.component.html',
  styleUrls: ['./cell-config.component.scss']
})
export class CellConfigComponent implements OnInit {

  cells: Cell[] = [];
  loading = true;
  showModal = false;
  isEditMode = false;
  saving = false;

  formData: Partial<Cell> = {};

  statusOptions = ['ACTIVE', 'INACTIVE', 'MAINTENANCE'] as const;
  bandwidthOptions = [5, 10, 15, 20, 40, 80, 100];

  constructor(private ranService: RanEngineerService) {}

  ngOnInit(): void {
    this.loadCells();
  }

  loadCells(): void {
    this.loading = true;
    this.ranService.getCells().subscribe({
      next: (data) => { this.cells = data; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  openAddModal(): void {
    this.isEditMode = false;
    this.formData = {
      status: 'ACTIVE',
      bandwidth: 100,
      sector: 1,
      txPower: 43
    };
    this.showModal = true;
  }

  openEditModal(cell: Cell): void {
    this.isEditMode = true;
    this.formData = { ...cell };
    this.showModal = true;
  }

  closeModal(): void {
    this.showModal = false;
    this.formData = {};
  }

  saveCell(): void {
    this.saving = true;
    if (this.isEditMode && this.formData.id) {
      this.ranService.updateCell(this.formData.id, this.formData).subscribe({
        next: () => { this.saving = false; this.closeModal(); this.loadCells(); }
      });
    } else {
      this.ranService.addCell(this.formData as Omit<Cell, 'id'>).subscribe({
        next: () => { this.saving = false; this.closeModal(); this.loadCells(); }
      });
    }
  }

  deleteCell(id: string): void {
    if (confirm('Are you sure you want to delete this cell?')) {
      this.ranService.deleteCell(id).subscribe(() => this.loadCells());
    }
  }

  getStatusClass(status: string): string {
    const map: Record<string, string> = {
      'ACTIVE':      'badge bg-success',
      'INACTIVE':    'badge bg-danger',
      'MAINTENANCE': 'badge bg-warning text-dark'
    };
    return map[status] ?? 'badge bg-secondary';
  }
}