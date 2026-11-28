import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { NavbarComponent } from './navbar.component';

@Component({ template: '' })
class TestPageComponent {}

describe('NavbarComponent', () => {
  it('links the Rehabitar title and Sierra Norte subtitle to the dashboard', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'dashboard', component: TestPageComponent },
          { path: 'convocatorias', component: TestPageComponent },
        ]),
      ],
    });
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/convocatorias');
    const fixture = TestBed.createComponent(NavbarComponent);
    await fixture.whenStable();

    const brand = (fixture.nativeElement as HTMLElement).querySelector<HTMLAnchorElement>(
      'header > div > a',
    );
    expect(brand?.textContent).toContain('Rehabitar');
    expect(brand?.textContent).toContain('Sierra Norte');
    expect(brand?.getAttribute('href')).toBe('/dashboard');
    brand?.click();
    await fixture.whenStable();
    expect(router.url).toBe('/dashboard');
  });
});
