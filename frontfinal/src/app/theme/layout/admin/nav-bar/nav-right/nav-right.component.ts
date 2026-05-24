import { Component, inject, OnInit } from '@angular/core';
import { NgbDropdownConfig } from '@ng-bootstrap/ng-bootstrap';
import { Router, RouterModule } from '@angular/router';
import { SharedModule } from 'src/app/theme/shared/shared.module';
import { AuthService } from 'src/app/demo/users/services/auth.service';

@Component({
  selector: 'app-nav-right',
  standalone: true,
  imports: [SharedModule, RouterModule],
  templateUrl: './nav-right.component.html',
  styleUrls: ['./nav-right.component.scss'],
  providers: [NgbDropdownConfig]
})
export class NavRightComponent implements OnInit {
  private authService = inject(AuthService);
  private router = inject(Router);

  currentUser: { email: string; fullName: string; role: string } | null = null;
  constructor() {
    const config = inject(NgbDropdownConfig);
    config.placement = 'bottom-right';
  }

  ngOnInit() {
    this.currentUser = this.authService.getCurrentUser();
  }

  get isGuideOpen(): boolean {
    return this.router.url === '/guide';
  }

  toggleGuide(): void {
    if (this.isGuideOpen) {
      this.router.navigateByUrl('/home');
    } else {
      this.router.navigateByUrl('/guide');
    }
  }

  logout() {
    this.authService.logout();
  }
}