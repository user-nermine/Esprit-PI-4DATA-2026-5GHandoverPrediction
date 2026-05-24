import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { RanEngineerService } from '../services/ran-engineer.service';
import { NeighborCell, Cell } from '../models/ran.models';

@Component({
  selector: 'app-neighbor-cells',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './neighbor-cells.component.html',
  styleUrls: ['./neighbor-cells.component.scss']
})
export class NeighborCellsComponent implements OnInit {

  neighbors: NeighborCell[] = [];
  cells: Cell[] = [];
  loading = true;
  showModal = false;
  isEditMode = false;
  saving = false;

  formData: Partial<NeighborCell> = {};

  constructor(private ranService: RanEngineerService) {}

  ngOnInit(): void {
    this.loadAll();
  }

  loadAll(): void {
    this.loading = true;
    this.ranService.getCells().subscribe(cells => { this.cells = cells; });
    this.ranService.getNeighborCells().subscribe({
      next: (data) => { this.neighbors = data; this.loading = false; }
    });
  }

  openAddModal(): void {
    this.isEditMode = false;
    this.formData = { noHo: false, noRemove: false, relationStatus: 'ACTIVE' };
    this.showModal = true;
  }

  openEditModal(nb: NeighborCell): void {
    this.isEditMode = true;
    this.formData = { ...nb };
    this.showModal = true;
  }

  closeModal(): void {
    this.showModal = false;
    this.formData = {};
  }

  saveNeighbor(): void {
    this.saving = true;
    if (this.isEditMode && this.formData.id) {
      this.ranService.updateNeighborCell(this.formData.id, this.formData).subscribe({
        next: () => { this.saving = false; this.closeModal(); this.loadAll(); }
      });
    } else {
      this.ranService.addNeighborCell(
        this.formData as Omit<NeighborCell, 'id'>
      ).subscribe({
        next: () => { this.saving = false; this.closeModal(); this.loadAll(); }
      });
    }
  }

  deleteNeighbor(id: string): void {
    if (confirm('Delete this neighbor cell relation?')) {
      this.ranService.deleteNeighborCell(id).subscribe(() => this.loadAll());
    }
  }

  onSourceCellChange(cellName: string): void {
    const cell = this.cells.find(c => c.cellName === cellName);
    if (cell) {
      this.formData.sourceCellId = cell.id;
      this.formData.sourceCellName = cell.cellName;
    }
  }

  onTargetCellChange(cellName: string): void {
    const cell = this.cells.find(c => c.cellName === cellName);
    if (cell) {
      this.formData.targetCellId = cell.id;
      this.formData.targetCellName = cell.cellName;
      this.formData.targetPci = cell.pci;
      this.formData.targetEarfcn = cell.earfcn;
    }
  }
}