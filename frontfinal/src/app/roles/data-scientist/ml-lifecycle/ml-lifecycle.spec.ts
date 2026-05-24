import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MlLifecycle } from './ml-lifecycle';

describe('MlLifecycle', () => {
  let component: MlLifecycle;
  let fixture: ComponentFixture<MlLifecycle>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MlLifecycle]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MlLifecycle);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
