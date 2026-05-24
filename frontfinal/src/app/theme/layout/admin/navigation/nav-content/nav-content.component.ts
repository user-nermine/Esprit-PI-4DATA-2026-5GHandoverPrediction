import { Component, inject, output } from '@angular/core';
import { Location } from '@angular/common';
import { environment } from 'src/environments/environment';
import { RoleBasedNavigationService } from '../role-based-navigation';
import { SharedModule } from 'src/app/theme/shared/shared.module';
import { NavGroupComponent } from './nav-group/nav-group.component';

@Component({
  selector: 'app-nav-content',
  imports: [SharedModule, NavGroupComponent],
  templateUrl: './nav-content.component.html',
  styleUrls: ['./nav-content.component.scss']
})
export class NavContentComponent {
  private location = inject(Location);
  private roleBasedNavigationService = inject(RoleBasedNavigationService);

  title = 'Demo application for version numbering';
  currentApplicationVersion = environment.appVersion;
  navigations: any[] = [];
  wrapperWidth: number;
  windowWidth = window.innerWidth;
  navCollapsedMob = output();

  constructor() {
    this.navigations = this.roleBasedNavigationService.getNavigationItems();
  }

  fireOutClick() {
    let current_url = this.location.path();
    if (this.location['_baseHref']) {
      current_url = this.location['_baseHref'] + this.location.path();
    }
    const navElement = document.querySelector('.pcoded-navbar') as HTMLElement;
    if (navElement) {
      navElement.style.display = 'none';
    }
    setTimeout(() => {
      this.location.back();
    }, 100);
  }

  navCollapse() {
    if (this.windowWidth < 992) {
      this.navCollapsedMob.emit();
    }
  }

  onResize(event: any) {
    this.windowWidth = event.target.innerWidth;
  }
}
