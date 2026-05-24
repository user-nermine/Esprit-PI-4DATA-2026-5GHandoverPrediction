import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, NavigationEnd, RouterModule } from '@angular/router';
import { Subscription, filter } from 'rxjs';
import { AuthService } from 'src/app/demo/users/services/auth.service';

interface RoleInfo { label: string; icon: string; color: string; }

@Component({
  selector: 'app-admin-view-banner',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div *ngIf="visible" style="
      margin-bottom: 1rem;
      background: linear-gradient(135deg, rgba(30,64,175,0.06), rgba(124,58,237,0.06));
      border: 1px solid rgba(30,64,175,0.2);
      border-radius: 14px;
      padding: 0.75rem 1.25rem;
      display: flex; align-items: center; justify-content: space-between;
      backdrop-filter: blur(10px);
      box-shadow: 0 4px 20px rgba(30,64,175,0.08);
      position: relative; overflow: hidden;">

      <!-- Gradient top bar -->
      <div style="position:absolute; top:0; left:0; right:0; height:3px;
                  background: linear-gradient(90deg, #1e40af, #7c3aed, #ec4899);"></div>

      <div style="display:flex; align-items:center; gap:0.75rem;">
        <div style="width:34px; height:34px; border-radius:9px;
                    background: linear-gradient(135deg, #1e40af, #7c3aed);
                    display:flex; align-items:center; justify-content:center; flex-shrink:0;">
          <i class="feather icon-eye" style="color:#fff; font-size:15px;"></i>
        </div>
        <div>
          <div style="font-size:0.78rem; font-weight:700; color:#1e40af; margin-bottom:1px;">
            Admin View Mode
          </div>
          <div style="font-size:0.72rem; color:#64748b;">
            Viewing <strong style="color:#0f172a;">{{ roleInfo?.label }}</strong> interface
            &nbsp;·&nbsp; Read Only — no modifications allowed
          </div>
        </div>
      </div>

      <div style="display:flex; align-items:center; gap:0.5rem; flex-shrink:0;">
        <span style="font-size:0.68rem; font-weight:600; padding:0.25rem 0.75rem;
                     border-radius:20px; background:rgba(239,68,68,0.1);
                     border:1px solid rgba(239,68,68,0.2); color:#dc2626;">
          <i class="feather icon-lock" style="font-size:10px; margin-right:3px;"></i>
          Read Only
        </span>
        <a routerLink="/admin" style="font-size:0.68rem; font-weight:600; padding:0.25rem 0.75rem;
                     border-radius:20px; background:linear-gradient(135deg,#1e40af,#7c3aed);
                     color:#fff; text-decoration:none; cursor:pointer;">
          ← Back to Admin
        </a>
      </div>
    </div>
  `
})
export class AdminViewBannerComponent implements OnInit, OnDestroy {

  visible = false;
  roleInfo: RoleInfo | null = null;

  private readonly roleMap: Record<string, RoleInfo> = {
    'data-scientist':        { label: 'Data Scientist',       icon: 'icon-pie-chart',   color: '#d97706' },
    'ran-engineer':          { label: 'RAN Engineer',          icon: 'icon-radio',        color: '#16a34a' },
    'noc':                   { label: 'NOC Engineer',          icon: 'icon-monitor',      color: '#2563eb' },
    'core-engineer':         { label: 'Core Engineer',         icon: 'icon-trending-up',  color: '#7c3aed' },
  };

  private sub!: Subscription;

  constructor(private router: Router, private authService: AuthService) {}

  ngOnInit(): void {
    this.check(this.router.url);
    this.sub = this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe((e: NavigationEnd) => this.check(e.urlAfterRedirects));
  }

  ngOnDestroy(): void { this.sub?.unsubscribe(); }

  private check(url: string): void {
    const user = this.authService.getCurrentUser();
    if (user?.role !== 'SYSTEM_ADMIN') { this.visible = false; return; }

    const isAdminRoute = url.startsWith('/admin') || url === '/guide';
    if (isAdminRoute) { this.visible = false; return; }

    this.visible = true;
    this.roleInfo = null;
    for (const key of Object.keys(this.roleMap)) {
      if (url.includes(key)) { this.roleInfo = this.roleMap[key]; break; }
    }
  }
}
