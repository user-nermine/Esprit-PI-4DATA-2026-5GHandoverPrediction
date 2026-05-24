import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from 'src/environments/environment';

interface AuditEntry {
  id: number;
  userName: string;
  userRole: string;
  action: string;
  target: string;
  timestamp: string;
  status: string;
}

@Component({
  selector: 'app-audit-log',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './audit-log.html',
  styleUrl: './audit-log.scss'
})
export class AuditLog implements OnInit {
  searchTerm = '';
  filterRole = '';
  logs: AuditEntry[] = [];
  loading = signal(false);
  error = signal('');

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadLogs();
  }

  loadLogs() {
    this.loading.set(true);
    this.http.get<AuditEntry[]>(`${environment.apiUrl}/audit-logs`).subscribe({
      next: (data) => {
        this.logs = data;
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load audit logs.');
        this.loading.set(false);
      }
    });
  }

  filteredLogs(): AuditEntry[] {
    return this.logs.filter(log => {
      const matchSearch =
        log.userName?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        log.action?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        log.target?.toLowerCase().includes(this.searchTerm.toLowerCase());
      const matchRole = this.filterRole ? log.userRole === this.filterRole : true;
      return matchSearch && matchRole;
    });
  }

  getStatusBadge(status: string): string {
    return status === 'Success' ? 'bg-success' : 'bg-danger';
  }

  getActionBadge(action: string): string {
    if (action?.includes('Delete') || action?.includes('DELETE')) return 'bg-danger';
    if (action?.includes('Suspend') || action?.includes('TOGGLE')) return 'bg-warning';
    if (action?.includes('Create') || action?.includes('CREATE')) return 'bg-success';
    if (action?.includes('Failed') || action?.includes('FAILED')) return 'bg-danger';
    return 'bg-info';
  }
}