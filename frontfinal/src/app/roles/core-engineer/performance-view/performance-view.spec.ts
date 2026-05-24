import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PerformanceView } from './performance-view';

describe('PerformanceView', () => {
  let component: PerformanceView;
  let fixture: ComponentFixture<PerformanceView>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PerformanceView]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PerformanceView);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
