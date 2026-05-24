import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';

@Component({
  standalone: true,
  imports: [CommonModule],
  selector: 'app-dso-detail',
  templateUrl: './dso-detail.component.html',
  styleUrls: ['./dso-detail.component.scss']
})
export class DsoDetailComponent implements OnInit {
  dsoId: string = '';
  dsoName: string = '';

  private dsoNames: Record<string, string> = {
    'dso1': 'HO Prediction',
    'dso2': 'Signal Degradation',
    'dso3': 'Next Best Cell',
    'dso4': 'Handover Type'
  };

  constructor(private route: ActivatedRoute, private router: Router) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      this.dsoId = params.get('dsoId') || '';
      this.dsoName = this.dsoNames[this.dsoId] || 'DSO Details';
    });
  }

  goBack(): void {
    this.router.navigate(['/data-scientist/ml-lifecycle']);
  }

  exportReport(): void {
    this.router.navigate(['/data-scientist/reporting']);
  }

}
