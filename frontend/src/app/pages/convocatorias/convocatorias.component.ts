import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MunicipioService } from '../../core/services/municipio.service';
import { Convocatoria } from '../../core/models/municipio.model';

@Component({
  selector: 'app-convocatorias',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  template: `
    <div class="w-full px-margin-desktop py-space-lg flex flex-col gap-space-lg">
      <!-- Header -->
      <div class="flex flex-col gap-space-xs max-w-3xl">
        <h1 class="font-display-lg text-display-lg text-primary tracking-tight">Convocatorias BDNS</h1>
        <p class="font-body-md text-body-md text-on-surface-variant">
          Catálogo de subvenciones y ayudas públicas para municipios de la Sierra Norte.
        </p>
      </div>

      <!-- Filters -->
      <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-space-md">
          <!-- Buscar -->
          <div class="flex flex-col gap-space-xs">
            <label class="font-label-md text-label-md text-on-surface">Buscar</label>
            <input 
              type="text"
              placeholder="Nombre de convocatoria..."
              class="px-space-md py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface placeholder:text-on-surface-variant focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              (input)="onSearchChange($event)">
          </div>

          <!-- Municipio (si aplica) -->
          <div class="flex flex-col gap-space-xs">
            <label class="font-label-md text-label-md text-on-surface">Filtrar por municipio</label>
            <select 
              class="px-space-md py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              (change)="onMunicipioChange($event)">
              <option value="">Todos</option>
              <option *ngFor="let mun of municipios" [value]="mun.codigo_ine">
                {{ mun.nombre }}
              </option>
            </select>
          </div>

          <!-- Estatus -->
          <div class="flex flex-col gap-space-xs">
            <label class="font-label-md text-label-md text-on-surface">Estatus</label>
            <select 
              class="px-space-md py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              (change)="onStatusChange($event)">
              <option value="">Todos</option>
              <option value="abierta">Abiertas</option>
              <option value="cerrada">Cerradas</option>
            </select>
          </div>
        </div>

        <!-- Resultados -->
        <div class="mt-space-md pt-space-md border-t border-outline-variant/30 text-body-sm text-on-surface-variant">
          Mostrando {{ filteredConvocatorias.length }} de {{ convocatorias.length }} convocatorias
        </div>
      </div>

      <!-- Results Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-gutter-desktop">
        <div 
          *ngFor="let conv of filteredConvocatorias"
          class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-md hover:shadow-md transition-shadow">
          
          <!-- Header -->
          <div class="flex items-start justify-between gap-space-md pb-space-sm border-b border-outline-variant/30">
            <div class="flex-1">
              <h3 class="font-headline-sm text-headline-sm text-primary line-clamp-2">{{ conv.descripcion }}</h3>
              <div class="flex items-center gap-space-xs mt-space-xs">
                <span class="font-label-sm text-label-sm text-outline uppercase tracking-wider">{{ conv.codigo_bdns }}</span>
              </div>
            </div>
            
            <!-- Status Badge -->
            <span 
              [ngClass]="conv.abierta ? 'bg-secondary-container text-on-secondary-container' : 'bg-surface-container text-on-surface-variant'"
              class="inline-flex items-center gap-space-xs px-2 py-1 rounded-full font-label-sm text-label-sm font-semibold whitespace-nowrap shrink-0">
              <span class="w-1.5 h-1.5 rounded-full" [ngClass]="conv.abierta ? 'bg-secondary' : 'bg-outline'"></span>
              {{ conv.abierta ? 'Abierta' : 'Cerrada' }}
            </span>
          </div>

          <!-- Organismo -->
          <div class="flex flex-col gap-space-xs">
            <span class="font-label-sm text-label-sm text-outline uppercase tracking-wider">Convocante</span>
            <div class="flex flex-col gap-space-xs text-body-sm">
              <span class="text-on-surface font-semibold">{{ conv.organo_convocante }}</span>
              <span class="text-on-surface-variant text-[12px]">{{ conv.organo_nivel1 }}</span>
            </div>
          </div>

          <!-- Detalles Grid -->
          <div class="grid grid-cols-2 gap-space-md bg-surface-container rounded-lg p-space-md text-body-sm">
            <div>
              <span class="text-on-surface-variant text-[12px] block mb-space-xs">Presupuesto Total</span>
              <span class="font-metric-md text-metric-md text-primary">{{ conv.presupuesto_total | number: '1.0-0' }}€</span>
            </div>
            
            <div>
              <span class="text-on-surface-variant text-[12px] block mb-space-xs">Fin de Solicitud</span>
              <span class="font-semibold text-on-surface">{{ conv.fin_solicitud | date: 'dd/MM/yyyy' }}</span>
            </div>

            <div class="col-span-2" *ngIf="conv.tipo_beneficiario">
              <span class="text-on-surface-variant text-[12px] block mb-space-xs">Tipo de Beneficiario</span>
              <span class="text-on-surface">{{ conv.tipo_beneficiario }}</span>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex gap-space-sm pt-space-sm border-t border-outline-variant/30">
            <a 
              *ngIf="conv.url_bases"
              [href]="conv.url_bases"
              target="_blank"
              class="flex-1 px-space-md py-2 rounded-lg border border-primary bg-primary/5 text-primary hover:bg-primary/10 transition-colors font-body-sm font-semibold text-center">
              Ver bases
            </a>
            <button 
              class="flex-1 px-space-md py-2 rounded-lg bg-primary text-on-primary hover:bg-primary-container transition-colors font-body-sm font-semibold">
              Solicitar
            </button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div *ngIf="filteredConvocatorias.length === 0 && convocatorias.length > 0" class="flex flex-col items-center justify-center py-space-xl text-center">
        <span class="material-symbols-outlined text-[48px] text-outline opacity-50 mb-space-md">search_off</span>
        <h3 class="font-headline-md text-headline-md text-on-surface mb-space-sm">No hay convocatorias</h3>
        <p class="font-body-md text-body-md text-on-surface-variant max-w-md">
          No se encontraron convocatorias que coincidan con tus filtros. Intenta con otros criterios.
        </p>
      </div>
    </div>
  `,
  styles: []
})
export class ConvocatoriasComponent implements OnInit {
  convocatorias: Convocatoria[] = [];
  filteredConvocatorias: Convocatoria[] = [];
  municipios: any[] = [];
  
  filters = {
    search: '',
    municipio: '',
    status: ''
  };

  constructor(
    private municipioService: MunicipioService,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {
    this.loadConvocatorias();
    this.loadMunicipios();

    // Cargar filtro de municipio desde query params si existe
    this.route.queryParams.subscribe(params => {
      if (params['municipio']) {
        this.filters.municipio = params['municipio'];
        this.applyFilters();
      }
    });
  }

  loadConvocatorias() {
    this.municipioService.getConvocatorias().subscribe({
      next: (data) => {
        this.convocatorias = data;
        this.applyFilters();
      },
      error: (error) => console.error('Error loading convocatorias:', error)
    });
  }

  loadMunicipios() {
    this.municipioService.getMunicipios().subscribe({
      next: (data) => {
        this.municipios = data.sort((a, b) => a.nombre.localeCompare(b.nombre));
      },
      error: (error) => console.error('Error loading municipios:', error)
    });
  }

  onSearchChange(event: Event) {
    const input = event.target as HTMLInputElement;
    this.filters.search = input.value.toLowerCase();
    this.applyFilters();
  }

  onMunicipioChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    this.filters.municipio = select.value;
    this.applyFilters();
  }

  onStatusChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    this.filters.status = select.value;
    this.applyFilters();
  }

  applyFilters() {
    this.filteredConvocatorias = this.convocatorias.filter(conv => {
      // Filtro de búsqueda
      if (this.filters.search && 
          !conv.descripcion.toLowerCase().includes(this.filters.search) &&
          !conv.codigo_bdns.includes(this.filters.search)) {
        return false;
      }

      // Filtro de estatus
      if (this.filters.status === 'abierta' && !conv.abierta) {
        return false;
      }
      if (this.filters.status === 'cerrada' && conv.abierta) {
        return false;
      }

      return true;
    });
  }
}
