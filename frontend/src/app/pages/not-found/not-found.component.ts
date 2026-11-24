import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="w-full h-screen flex flex-col items-center justify-center gap-space-lg">
      <div class="text-center">
        <h1 class="font-display-lg text-display-lg text-primary mb-space-md">404</h1>
        <h2 class="font-headline-lg text-headline-lg text-on-surface mb-space-sm">Página no encontrada</h2>
        <p class="font-body-md text-body-md text-on-surface-variant mb-space-lg">
          La página que estás buscando no existe.
        </p>
        
        <a 
          routerLink="/dashboard"
          class="inline-flex items-center gap-space-xs px-space-md py-2 rounded-lg bg-primary text-on-primary hover:bg-primary-container transition-colors font-body-sm font-semibold">
          Volver al inicio
        </a>
      </div>
    </div>
  `,
  styles: []
})
export class NotFoundComponent {}
