import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MunicipioService } from '../../../core/services/municipio.service';
import { Municipio } from '../../../core/models/municipio.model';

@Component({
  selector: 'app-rango-municipal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-md">
      <!-- Header -->
      <div class="pb-space-sm border-b border-outline-variant/30">
        <h3 class="font-headline-md text-headline-md text-primary">Ranking Municipal WLC</h3>
        <p class="font-body-sm text-body-sm text-outline">Puntuación 0-100</p>
      </div>

      <!-- Search/Filter -->
      <div class="flex flex-col gap-space-md">
        <input 
          type="text" 
          placeholder="Buscar municipio..."
          class="w-full px-space-md py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          (input)="onSearch($event)">

        <!-- Filter Dropdown -->
        <select class="w-full px-space-md py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20">
          <option value="">Todos</option>
          <option value="verde">Verde (Favorable)</option>
          <option value="ambar">Ámbar (Vulnerable)</option>
          <option value="rojo">Rojo (Alto Riesgo)</option>
        </select>
      </div>

      <!-- Table -->
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-outline-variant text-label-sm font-label-sm text-outline uppercase tracking-wider">
              <th class="text-left px-space-sm py-2 font-semibold">Municipio</th>
              <th class="text-right px-space-sm py-2 font-semibold">Estado</th>
              <th class="text-right px-space-sm py-2 font-semibold">WLC</th>
              <th class="text-right px-space-sm py-2 font-semibold">Acción</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let municipio of municipios" class="border-b border-outline-variant/50 hover:bg-surface-container-low transition-colors h-11">
              <td class="px-space-sm py-2 font-body-sm text-on-surface">
                <div class="flex flex-col">
                  <span class="font-semibold">{{ municipio.nombre }}</span>
                  <span class="text-on-surface-variant text-[11px]">{{ municipio.codigo_ine }}</span>
                </div>
              </td>
              <td class="text-right px-space-sm py-2">
                <span 
                  class="inline-flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-semibold"
                  [ngClass]="getStatusBadgeClass(municipio.wlc.semaforo)">
                  <span class="w-1.5 h-1.5 rounded-full" [ngClass]="getStatusDotClass(municipio.wlc.semaforo)"></span>
                  {{ municipio.wlc.semaforo }}
                </span>
              </td>
              <td class="text-right px-space-sm py-2">
                <span class="font-metric-md text-metric-md text-primary font-feature-settings">{{ municipio.wlc.indice_wlc | number: '1.1-1' }}</span>
              </td>
              <td class="text-right px-space-sm py-2">
                <a 
                  href="#"
                  class="inline-flex items-center justify-center w-8 h-8 rounded-lg border border-outline-variant hover:bg-surface-container-low text-on-surface-variant hover:text-primary transition-colors">
                  <span class="material-symbols-outlined text-[18px]">arrow_outward</span>
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between pt-space-sm border-t border-outline-variant/30 text-body-sm text-on-surface-variant">
        <span>Mostrando {{ municipios.length }} municipios</span>
        <div class="flex gap-space-xs">
          <button class="px-2 py-1 rounded-lg border border-outline-variant hover:bg-surface-container-low transition-colors">
            <span class="material-symbols-outlined text-[18px]">chevron_left</span>
          </button>
          <button class="px-2 py-1 rounded-lg border border-outline-variant hover:bg-surface-container-low transition-colors">
            <span class="material-symbols-outlined text-[18px]">chevron_right</span>
          </button>
        </div>
      </div>
    </div>
  `,
  styles: []
})
export class RangoMunicipalComponent implements OnInit {
  @Input() municipios: Municipio[] = [];
  searchTerm = '';

  constructor(private municipioService: MunicipioService) {}

  ngOnInit() {
    if (this.municipios.length === 0) {
      this.loadMunicipios();
    } else {
      this.sortMunicipios();
    }
  }

  loadMunicipios() {
    this.municipioService.getMunicipios().subscribe({
      next: (data) => {
        this.municipios = data;
        this.sortMunicipios();
      },
      error: (error) => console.error('Error loading municipios:', error)
    });
  }

  sortMunicipios() {
    this.municipios = this.municipios.sort((a, b) => (b.wlc?.indice_wlc || 0) - (a.wlc?.indice_wlc || 0));
  }

  onSearch(event: Event) {
    const input = event.target as HTMLInputElement;
    this.searchTerm = input.value.toLowerCase();
  }

  getStatusBadgeClass(status: string): string {
    const classes: Record<string, string> = {
      'VERDE': 'bg-secondary-container/70 text-on-secondary-container',
      'AMBAR': 'bg-amber-100 text-amber-900',
      'ROJO': 'bg-error-container/70 text-on-error-container',
      'PENDIENTE': 'bg-surface-container text-on-surface-variant'
    };
    return classes[status] || classes['PENDIENTE'];
  }

  getStatusDotClass(status: string): string {
    const classes: Record<string, string> = {
      'VERDE': 'bg-secondary',
      'AMBAR': 'bg-amber-600',
      'ROJO': 'bg-error',
      'PENDIENTE': 'bg-outline'
    };
    return classes[status] || classes['PENDIENTE'];
  }
}
