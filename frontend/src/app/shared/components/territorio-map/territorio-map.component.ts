import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-territorio-map',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-md relative overflow-hidden">
      <!-- Map Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-space-md pb-space-sm">
        <div>
          <div class="flex items-center gap-space-xs">
            <span class="w-2.5 h-2.5 rounded-full bg-primary-container"></span>
            <h2 class="font-headline-md text-headline-md text-primary">Mapa de Riesgo Territorial (WLC)</h2>
          </div>
          <p class="font-body-sm text-body-sm text-outline">Modelo de ponderación espacial multicriterio basado en demografía, tiempos de viaje a salud e infraestructuras.</p>
        </div>

        <!-- Filter Tabs -->
        <div class="inline-flex p-1 bg-surface-container rounded-lg self-start sm:self-auto text-on-surface-variant">
          <button 
            (click)="setFilter('all')"
            [ngClass]="filter === 'all' ? 'px-space-md py-1 rounded-md text-body-sm font-semibold transition-all bg-surface-container-lowest text-primary shadow-sm' : 'px-space-md py-1 rounded-md text-body-sm font-medium transition-all text-on-surface-variant hover:text-primary'">
            Todo
          </button>
          <button 
            (click)="setFilter('high')"
            [ngClass]="filter === 'high' ? 'px-space-md py-1 rounded-md text-body-sm font-semibold transition-all bg-surface-container-lowest text-primary shadow-sm' : 'px-space-md py-1 rounded-md text-body-sm font-medium transition-all text-on-surface-variant hover:text-primary'">
            Riesgo Alto
          </button>
          <button 
            (click)="setFilter('urgent')"
            [ngClass]="filter === 'urgent' ? 'px-space-md py-1 rounded-md text-body-sm font-semibold transition-all bg-surface-container-lowest text-primary shadow-sm' : 'px-space-md py-1 rounded-md text-body-sm font-medium transition-all text-on-surface-variant hover:text-primary'">
            Urgencias &gt;30min
          </button>
        </div>
      </div>

      <!-- Map Container -->
      <div class="relative w-full h-[520px] bg-surface rounded-xl overflow-hidden flex items-center justify-center p-space-md select-none group">
        <!-- Grid Background -->
        <svg class="absolute inset-0 w-full h-full pointer-events-none opacity-40" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern height="48" id="carto-grid" patternunits="userSpaceOnUse" width="48">
              <path d="M 48 0 L 0 0 0 48" fill="none" stroke="#d8dbd6" stroke-width="0.75"></path>
              <circle cx="0" cy="0" fill="#c2c8c2" r="1.5"></circle>
            </pattern>
          </defs>
          <rect fill="url(#carto-grid)" height="100%" width="100%"></rect>
        </svg>

        <!-- Topography Lines -->
        <svg class="absolute inset-0 w-full h-full pointer-events-none opacity-30" fill="none" viewBox="0 0 800 520">
          <path d="M-50,150 C120,110 240,190 380,120 C500,60 620,140 850,90" stroke="#737974" stroke-dasharray="3 3" stroke-width="0.8"></path>
          <path d="M-30,280 C150,220 280,310 420,240 C560,180 690,260 850,210" stroke="#737974" stroke-dasharray="4 4" stroke-width="0.8"></path>
          <path d="M0,420 C180,380 320,450 490,390 C620,340 710,400 850,370" stroke="#737974" stroke-dasharray="3 3" stroke-width="0.8"></path>
        </svg>

        <!-- Map Placeholder -->
        <div class="relative z-10 flex flex-col items-center justify-center gap-space-md">
          <span class="material-symbols-outlined text-outline text-[48px] opacity-50">map</span>
          <div class="text-center">
            <p class="font-body-md text-body-md text-outline">Mapa interactivo (Leaflet)</p>
            <p class="font-body-sm text-body-sm text-on-surface-variant">Configurar con GeoJSON de municipios</p>
          </div>
        </div>
      </div>

      <!-- Legend -->
      <div class="flex flex-wrap items-center gap-space-md pt-space-sm border-t border-outline-variant/30 text-on-surface-variant">
        <div class="flex items-center gap-space-xs">
          <span class="w-3 h-3 rounded-sm" style="background-color: #72977b;"></span>
          <span class="font-body-sm">Favorable >70 pts</span>
        </div>
        <div class="flex items-center gap-space-xs">
          <span class="w-3 h-3 rounded-sm" style="background-color: #d9ae65;"></span>
          <span class="font-body-sm">Vulnerable 45-70 pts</span>
        </div>
        <div class="flex items-center gap-space-xs">
          <span class="w-3 h-3 rounded-sm" style="background-color: #c97973;"></span>
          <span class="font-body-sm">Alto riesgo <45 pts</span>
        </div>
        <div class="flex items-center gap-space-xs">
          <span class="w-3 h-3 rounded-sm" style="background-color: #9a9d98;"></span>
          <span class="font-body-sm">Pendiente</span>
        </div>
        <div class="ml-auto text-body-sm">
          <span class="text-outline">📍 Haz clic sobre cualquier municipio para inspeccionar su indicador</span>
        </div>
      </div>
    </div>
  `,
  styles: []
})
export class TerritorioMapComponent implements OnInit {
  filter: 'all' | 'high' | 'urgent' = 'all';

  ngOnInit() {
    // Inicializar mapa con Leaflet
  }

  setFilter(newFilter: 'all' | 'high' | 'urgent') {
    this.filter = newFilter;
    // Aplicar filtro al mapa
  }
}
