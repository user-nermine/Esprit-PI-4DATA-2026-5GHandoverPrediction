import { Injectable } from '@angular/core';
import { BehaviorSubject, interval } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class SimpleRealDataService {
  
  private kpisSubject = new BehaviorSubject<any[]>([]);
  kpis$ = this.kpisSubject.asObservable();

  constructor() {
    this.startUpdates();
  }

  private startUpdates(): void {
    interval(3000).subscribe(() => {
      this.kpisSubject.next([]);
    });
  }
}
