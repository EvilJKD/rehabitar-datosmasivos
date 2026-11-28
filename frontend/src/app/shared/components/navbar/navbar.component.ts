import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <header
      class="fixed top-0 left-0 right-0 w-full z-[1100] bg-surface-container-lowest border-b border-outline-variant/60 shadow-[0_1px_8px_rgba(0,0,0,0.02)]"
    >
      <div
        class="h-16 w-full px-margin-desktop flex items-center justify-between px-3 py-2 gap-gutter-desktop"
      >
        <a routerLink="/dashboard" class="flex flex-col shrink-0  ml-2">
          <span class="font-headline-sm text-headline-md text-on-surface leading-tight"
            >Rehabitar</span
          >
          <span
            class="font-label-sm text-label-sm text-outline tracking-wider uppercase leading-none"
            >Sierra Norte</span
          >
        </a>

        <!-- Navigation -->
        <nav class="flex items-center gap-xs" aria-label="Navegación principal">
          <a
            routerLink="/dashboard"
            routerLinkActive="bg-surface-container-low text-primary-container font-semibold"
            [routerLinkActiveOptions]="{ exact: true }"
            class="px-md py-sm transition-colors rounded-lg font-body-md text-body-md text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
          >
            Municipios
          </a>
          <a
            routerLink="/analitica"
            routerLinkActive="bg-surface-container-low text-primary-container font-semibold"
            class="px-md py-sm transition-colors rounded-lg font-body-md text-body-md text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
          >
            Analítica
          </a>
          <a
            routerLink="/convocatorias"
            routerLinkActive="bg-surface-container-low text-primary-container font-semibold"
            class="px-md py-sm rounded-lg font-body-md text-body-md text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors"
          >
            Convocatorias
          </a>
        </nav>
      </div>
    </header>
  `,
  styles: [],
})
export class NavbarComponent {
  private readonly router = inject(Router);

  isActive(route: string): boolean {
    const current = this.router.url.split('?')[0];
    return current === route || current.endsWith(route);
  }
}
