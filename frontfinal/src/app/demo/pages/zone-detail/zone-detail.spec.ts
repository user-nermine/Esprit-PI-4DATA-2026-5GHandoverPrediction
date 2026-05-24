import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ZoneDetail } from './zone-detail.component';

describe('ZoneDetail', () => {
  let component: ZoneDetail;
  let fixture: ComponentFixture<ZoneDetail>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ZoneDetail]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ZoneDetail);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
