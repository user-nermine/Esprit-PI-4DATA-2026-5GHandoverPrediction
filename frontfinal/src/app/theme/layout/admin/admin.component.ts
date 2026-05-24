// angular import
import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';

// project import
import { NavBarComponent } from './nav-bar/nav-bar.component';
import { NavigationComponent } from './navigation/navigation.component';
import { ConfigurationComponent } from 'src/app/theme/layout/admin/configuration/configuration.component';
import { BreadcrumbsComponent } from '../../shared/components/breadcrumbs/breadcrumbs.component';
import { Footer } from './footer/footer';
import { AdminViewBannerComponent } from './admin-view-banner/admin-view-banner.component';

@Component({
  selector: 'app-admin',
  imports: [NavBarComponent, NavigationComponent, RouterModule, CommonModule, ConfigurationComponent, BreadcrumbsComponent, Footer, AdminViewBannerComponent],
  templateUrl: './admin.component.html',
  styleUrls: ['./admin.component.scss']
})
export class AdminComponent {
  // public props
  navCollapsed: boolean = false;
  navCollapsedMob: boolean = false;
  windowWidth: number;

  constructor() {
    this.windowWidth = window.innerWidth;
  }

  navMobClick() {
    const nav = document.querySelector('app-navigation.pcoded-navbar');
    if (this.navCollapsedMob && !nav?.classList.contains('mob-open')) {
      this.navCollapsedMob = !this.navCollapsedMob;
      setTimeout(() => { this.navCollapsedMob = !this.navCollapsedMob; }, 100);
    } else {
      this.navCollapsedMob = !this.navCollapsedMob;
    }
  }

  handleKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Escape') { this.closeMenu(); }
  }

  closeMenu() {
    document.querySelector('app-navigation.pcoded-navbar')?.classList.remove('mob-open');
  }
}
