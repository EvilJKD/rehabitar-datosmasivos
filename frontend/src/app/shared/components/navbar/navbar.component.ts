import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <header class="fixed top-0 left-0 right-0 w-full z-50 bg-surface-container-lowest border-b border-outline-variant/60 shadow-[0_1px_8px_rgba(0,0,0,0.02)]">
      <div class="h-16 w-full px-margin-desktop flex items-center justify-between gap-gutter-desktop">
        <!-- Logo -->
        <div class="flex items-center gap-space-md shrink-0">
          <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
            <span class="text-on-primary font-bold">SN</span>
          </div>
          <div class="flex flex-col">
            <span class="font-headline-sm text-headline-sm text-on-surface leading-tight">Sierra Norte</span>
            <span class="font-label-sm text-label-sm text-outline tracking-wider uppercase leading-none">Inteligencia Territorial</span>
          </div>
        </div>

        <!-- Navigation -->
        <nav class="flex items-center gap-space-xs">
          <a 
            routerLink="/dashboard" 
            routerLinkActive="active"
            [routerLinkActiveOptions]="{ exact: true }"
            class="px-space-md py-space-sm transition-colors rounded-lg"
            [ngClass]="isActive('/dashboard') ? 'bg-surface-container-low text-primary-container font-semibold' : 'font-body-md text-body-md text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface'">
            Inicio
          </a>
          <a 
            routerLink="/convocatorias"
            routerLinkActive="active"
            class="px-space-md py-space-sm rounded-lg font-body-md text-body-md text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors"
            [ngClass]="isActive('/convocatorias') ? 'bg-surface-container-low text-primary-container font-semibold' : ''">
            Convocatorias
          </a>
        </nav>

      </div>
    </header>
  `,
  styles: []
})
export class NavbarComponent {
  isActive(route: string): boolean {
    return window.location.pathname === route || window.location.pathname.endsWith(route);
  }
}
