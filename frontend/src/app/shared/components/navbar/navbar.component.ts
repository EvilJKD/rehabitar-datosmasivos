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
        <nav class="hidden xl:flex items-center gap-space-xs" [ngClass]="{'bg-surface-container-low text-primary-container font-semibold rounded-lg': true}">
          <a 
            routerLink="/dashboard" 
            routerLinkActive="active"
            [routerLinkActiveOptions]="{ exact: true }"
            class="px-space-md py-space-sm transition-colors rounded-lg"
            [ngClass]="isActive('/dashboard') ? 'bg-surface-container-low text-primary-container font-semibold' : 'font-body-md text-body-md text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface'">
            Inicio
          </a>
          <a 
            href="#"
            class="px-space-md py-space-sm rounded-lg font-body-md text-body-md text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors">
            Mapa territorial
          </a>
          <a 
            href="#"
            class="px-space-md py-space-sm rounded-lg font-body-md text-body-md text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors">
            Municipios
          </a>
          <a 
            href="#"
            class="px-space-md py-space-sm rounded-lg font-body-md text-body-md text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors">
            Accesibilidad sanitaria
          </a>
          <a 
            routerLink="/convocatorias"
            routerLinkActive="active"
            class="px-space-md py-space-sm rounded-lg font-body-md text-body-md text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors"
            [ngClass]="isActive('/convocatorias') ? 'bg-surface-container-low text-primary-container font-semibold' : ''">
            Convocatorias
          </a>
        </nav>

        <!-- Right Section -->
        <div class="flex items-center gap-space-md shrink-0">
          <!-- Status Badge -->
          <div class="hidden sm:flex items-center gap-space-xs px-space-sm py-1 rounded-full bg-surface-container text-on-surface-variant">
            <span class="w-2 h-2 rounded-full bg-secondary"></span>
            <span class="font-label-sm text-label-sm font-medium">En línea • Actualizado hoy</span>
          </div>

          <!-- WLC Config Button -->
          <a 
            href="#"
            class="inline-flex items-center gap-space-xs px-space-md py-space-sm rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface hover:bg-surface-container-low hover:text-primary transition-colors text-body-sm font-body-sm font-medium">
            <span class="material-symbols-outlined text-[18px]">tune</span>
            <span class="hidden lg:inline">Configuración WLC</span>
          </a>

          <!-- User Avatar -->
          <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
            <span class="material-symbols-outlined text-on-primary text-[18px]">person</span>
          </div>
        </div>
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
