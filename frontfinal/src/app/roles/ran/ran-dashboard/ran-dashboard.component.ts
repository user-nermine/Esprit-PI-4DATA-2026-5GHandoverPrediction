import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { RanEngineerService } from '../services/ran-engineer.service';
import { RanSummary, HandoverEvent } from '../models/ran.models';

@Component({
  selector: 'app-ran-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './ran-dashboard.component.html',
  styleUrls: ['./ran-dashboard.component.scss']
})
export class RanDashboardComponent implements OnInit {

  summary: RanSummary | null = null;
  loading = true;

  constructor(private ranService: RanEngineerService) {}

  ngOnInit(): void {
    this.ranService.getRanSummary().subscribe({
      next: (data) => { this.summary = data; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  getEventBadgeClass(eventType: HandoverEvent['eventType']): string {
    const map: Record<string, string> = {
      'HANDOVER_SUCCESS': 'badge bg-success',
      'HANDOVER_FAILURE': 'badge bg-danger',
      'PING_PONG':        'badge bg-warning text-dark',
      'TOO_EARLY':        'badge bg-info text-dark',
      'TOO_LATE':         'badge bg-secondary'
    };
    return map[eventType] ?? 'badge bg-secondary';
  }
}