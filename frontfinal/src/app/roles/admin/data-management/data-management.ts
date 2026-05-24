import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

interface Dataset {
  name: string;
  size: string;
  samples: string;
  access: string;
  accessColor: string;
  lastUpdated: string;
}

interface IntegrityCheck {
  name: string;
  result: string;
  status: string;
}

@Component({
  selector: 'app-data-management',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './data-management.html',
  styleUrl: './data-management.scss'
})
export class DataManagement {
  selectedDataset = 'HO Training Data (30d)';
  grantAccessTo = 'Data Scientist';
  permissionLevel = 'Read Only';

  datasets: Dataset[] = [
    { name: 'HO Training Data (30d)', size: '1.2 GB', samples: '48,320', access: 'DS, Admin', accessColor: 'bg-primary', lastUpdated: 'Apr 20' },
    { name: 'HO Training Data (60d)', size: '2.3 GB', samples: '92,140', access: 'DS, Admin', accessColor: 'bg-primary', lastUpdated: 'Apr 18' },
    { name: 'Anomaly Labels',         size: '145 MB', samples: '12,800', access: 'DS, Admin', accessColor: 'bg-primary', lastUpdated: 'Apr 15' },
    { name: 'Production Logs',        size: '890 MB', samples: '--',     access: 'All roles',  accessColor: 'bg-secondary', lastUpdated: 'Live' },
    { name: 'Model Files (pkl)',       size: '325 MB', samples: '--',     access: 'DS, Admin', accessColor: 'bg-primary', lastUpdated: 'Apr 20' },
  ];

  integrityChecks: IntegrityCheck[] = [
    { name: 'Missing value ratio',                    result: '< 0.1%',      status: 'pass' },
    { name: 'Duplicate records',                      result: '0 detected',  status: 'pass' },
    { name: 'RSRP range validity (-140 to -44 dBm)',  result: '100% valid',  status: 'pass' },
    { name: 'SINR range validity (-20 to +30 dB)',    result: '99.98% valid',status: 'warning' },
    { name: 'Label consistency',                      result: 'Verified',    status: 'pass' },
    { name: 'Schema validation',                      result: 'Passed',      status: 'pass' },
  ];

  updatePermissions() {
    alert(`Permissions updated!\nDataset: ${this.selectedDataset}\nAccess: ${this.grantAccessTo}\nLevel: ${this.permissionLevel}`);
  }
}