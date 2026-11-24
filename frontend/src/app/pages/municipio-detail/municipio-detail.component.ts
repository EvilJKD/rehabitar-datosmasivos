import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MunicipioService } from '../../core/services/municipio.service';
import { Municipio, DemografiaPunto } from '../../core/models/municipio.model';

@Component({
  selector: 'app-municipio-detail',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div *ngIf="municipio" class="w-full px-margin-desktop py-space-lg flex flex-col gap-space-lg">
      <!-- Breadcrumb & Header -->
      <div class="flex flex-col gap-space-md">
        <a routerLink="/dashboard" class="text-body-sm text-primary hover:underline">← Volver al dashboard</a>
        
        <div class="flex items-end justify-between gap-space-md">
          <div class="flex flex-col gap-space-xs max-w-3xl">
            <h1 class="font-display-lg text-display-lg text-primary">{{ municipio.nombre }}</h1>
            <p class="font-body-md text-body-md text-on-surface-variant">
              Código INE: {{ municipio.codigo_ine }} | {{ municipio.comarca }} | {{ municipio.provincia }}
            </p>
          </div>

          <div [ngClass]="getStatusBadgeClass(municipio.wlc.semaforo)" 
               class="inline-flex items-center gap-space-xs px-space-md py-space-sm rounded-full font-label-sm text-label-sm font-semibold">
            <span class="w-2.5 h-2.5 rounded-full" [ngClass]="getStatusDotClass(municipio.wlc.semaforo)"></span>
            {{ municipio.wlc.semaforo }}
          </div>
        </div>
      </div>

      <!-- Main Grid (3 Columns) -->
      <div class="grid grid-cols-1 xl:grid-cols-3 gap-gutter-desktop">
        <!-- Left Column: WLC Breakdown -->
        <div class="xl:col-span-2">
          <!-- WLC Score Card -->
          <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-lg mb-gutter-desktop">
            <div>
              <h2 class="font-headline-md text-headline-md text-primary mb-space-md">Índice de Viabilidad (WLC)</h2>
              
              <div class="flex items-baseline gap-space-md mb-space-lg">
                <span class="font-display-lg text-display-lg text-primary">{{ municipio.wlc.indice_wlc | number: '1.2-2' }}</span>
                <span class="font-body-md text-body-md text-on-surface-variant">/ 100 puntos</span>
              </div>

              <p class="font-body-sm text-body-sm text-outline">{{ municipio.wlc.etiqueta_viabilidad }}</p>
            </div>

            <!-- Score Breakdown -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-space-md border-t border-outline-variant/30 pt-space-lg">
              <div class="flex flex-col gap-space-xs">
                <div class="flex items-center justify-between">
                  <span class="font-body-sm text-on-surface-variant">Acceso por carretera</span>
                  <span class="font-metric-md text-metric-md text-primary">{{ municipio.wlc.score_acceso_carretera | number: '1.1-1' }}</span>
                </div>
                <div class="w-full bg-surface-container rounded-full h-2">
                  <div class="bg-primary rounded-full h-2" [style.width.%]="municipio.wlc.score_acceso_carretera"></div>
                </div>
              </div>

              <div class="flex flex-col gap-space-xs">
                <div class="flex items-center justify-between">
                  <span class="font-body-sm text-on-surface-variant">Proximidad sanitaria</span>
                  <span class="font-metric-md text-metric-md text-primary">{{ municipio.wlc.score_proximidad_sanitaria | number: '1.1-1' }}</span>
                </div>
                <div class="w-full bg-surface-container rounded-full h-2">
                  <div class="bg-secondary rounded-full h-2" [style.width.%]="municipio.wlc.score_proximidad_sanitaria"></div>
                </div>
              </div>

              <div class="flex flex-col gap-space-xs">
                <div class="flex items-center justify-between">
                  <span class="font-body-sm text-on-surface-variant">Conectividad digital</span>
                  <span class="font-metric-md text-metric-md text-primary">{{ municipio.wlc.score_conectividad_digital | number: '1.1-1' }}</span>
                </div>
                <div class="w-full bg-surface-container rounded-full h-2">
                  <div class="bg-primary-container rounded-full h-2" [style.width.%]="municipio.wlc.score_conectividad_digital"></div>
                </div>
              </div>

              <div class="flex flex-col gap-space-xs">
                <div class="flex items-center justify-between">
                  <span class="font-body-sm text-on-surface-variant">Acceso a recursos hídricos</span>
                  <span class="font-metric-md text-metric-md text-primary">{{ municipio.wlc.score_acceso_hidrico | number: '1.1-1' }}</span>
                </div>
                <div class="w-full bg-surface-container rounded-full h-2">
                  <div class="bg-tertiary-container rounded-full h-2" [style.width.%]="municipio.wlc.score_acceso_hidrico"></div>
                </div>
              </div>

              <div class="flex flex-col gap-space-xs md:col-span-2">
                <div class="flex items-center justify-between">
                  <span class="font-body-sm text-on-surface-variant">Inercia demográfica (10 años)</span>
                  <span class="font-metric-md text-metric-md text-primary">{{ municipio.wlc.score_inercia_demografica | number: '1.1-1' }}</span>
                </div>
                <div class="w-full bg-surface-container rounded-full h-2">
                  <div class="bg-tertiary rounded-full h-2" [style.width.%]="municipio.wlc.score_inercia_demografica"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Demographics Card -->
          <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-md">
            <h2 class="font-headline-md text-headline-md text-primary">Serie Demográfica (2015-2025)</h2>
            
            <div *ngIf="demografia" class="flex flex-col gap-space-md">
              <div class="grid grid-cols-2 md:grid-cols-4 gap-space-md">
                <div class="bg-surface-container rounded-lg p-space-md">
                  <span class="font-label-sm text-label-sm text-outline uppercase">Población Inicial</span>
                  <span class="font-metric-md text-metric-md text-primary block mt-space-xs">{{ demografia.poblacion_inicial_10a | number }}</span>
                </div>
                <div class="bg-surface-container rounded-lg p-space-md">
                  <span class="font-label-sm text-label-sm text-outline uppercase">Población Actual</span>
                  <span class="font-metric-md text-metric-md text-primary block mt-space-xs">{{ demografia.poblacion_actual | number }}</span>
                </div>
                <div class="bg-surface-container rounded-lg p-space-md">
                  <span class="font-label-sm text-label-sm text-outline uppercase">Variación 10 años</span>
                  <span class="font-metric-md text-metric-md" [ngClass]="demografia.variacion_10a_pct >= 0 ? 'text-secondary' : 'text-error'" block mt-space-xs>
                    {{ demografia.variacion_10a_pct | number: '1.1-1' }}%
                  </span>
                </div>
                <div class="bg-surface-container rounded-lg p-space-md">
                  <span class="font-label-sm text-label-sm text-outline uppercase">Cobertura Fibra</span>
                  <span class="font-metric-md text-metric-md text-primary block mt-space-xs">{{ demografia.cobertura_fibra_pct | number: '1.1-1' }}%</span>
                </div>
              </div>

              <div class="bg-surface rounded-lg h-64 flex items-center justify-center text-on-surface-variant">
                <div class="text-center">
                  <span class="material-symbols-outlined text-[48px] opacity-50">bar_chart</span>
                  <p class="font-body-sm mt-space-sm">Gráfico Chart.js (integración pendiente)</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Sidebar Info -->
        <div class="flex flex-col gap-gutter-desktop">
          <!-- Infraestructura Card -->
          <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-md">
            <h3 class="font-headline-sm text-headline-sm text-primary">Infraestructura</h3>
            
            <div class="flex flex-col gap-space-md text-body-sm">
              <div class="pb-space-sm border-b border-outline-variant/30">
                <span class="text-on-surface-variant">Cobertura fibra óptica</span>
                <span class="font-metric-md text-metric-md text-primary block mt-space-xs">{{ municipio.cobertura_fibra_pct }}%</span>
              </div>
              
              <div>
                <span class="text-on-surface-variant">Número de ayudas abiertas</span>
                <span class="font-metric-md text-metric-md text-primary block mt-space-xs">{{ municipio.num_ayudas_abiertas }}</span>
              </div>
            </div>
          </div>

          <!-- Urgencias Card -->
          <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-md">
            <h3 class="font-headline-sm text-headline-sm text-primary">Accesibilidad Sanitaria</h3>
            
            <div class="flex flex-col gap-space-md text-body-sm">
              <div class="pb-space-sm border-b border-outline-variant/30">
                <span class="text-on-surface-variant block">Proximidad a servicios sanitarios 24h</span>
                <span class="font-metric-md text-metric-md text-primary block mt-space-xs">{{ municipio.wlc.score_proximidad_sanitaria | number: '1.1-1' }} puntos</span>
              </div>
            </div>
          </div>

          <!-- Ayudas Card -->
          <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-md">
            <h3 class="font-headline-sm text-headline-sm text-primary">Ayudas Activas</h3>
            <span class="font-metric-md text-metric-md text-primary">{{ municipio.num_ayudas_abiertas }}</span>
            <p class="font-body-sm text-on-surface-variant">convocatorias aplicables</p>
            
            <a 
              routerLink="/convocatorias"
              [queryParams]="{ municipio: municipio.codigo_ine }"
              class="mt-space-md px-space-md py-2 rounded-lg bg-primary text-on-primary hover:bg-primary-container transition-colors font-body-sm font-semibold text-center">
              Ver convocatorias
            </a>
          </div>
        </div>
      </div>
    </div>

    <div *ngIf="!municipio && !loading" class="flex items-center justify-center h-screen">
      <p class="text-on-surface-variant">Municipio no encontrado</p>
    </div>
  `,
  styles: []
})
export class MunicipioDetailComponent implements OnInit {
  municipio: Municipio | null = null;
  demografia: any = null;
  loading = true;

  constructor(
    private route: ActivatedRoute,
    private municipioService: MunicipioService
  ) {}

  ngOnInit() {
    this.route.params.subscribe(params => {
      const codigoIne = params['codigo_ine'];
      if (codigoIne) {
        this.loadMunicipioDetail(codigoIne);
      }
    });
  }

  loadMunicipioDetail(codigoIne: string) {
    this.municipioService.getMunicipioDetail(codigoIne).subscribe({
      next: (data) => {
        this.municipio = data;
        this.loadDemografia(codigoIne);
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading municipio:', error);
        this.loading = false;
      }
    });
  }

  loadDemografia(codigoIne: string) {
    this.municipioService.getDemografia(codigoIne).subscribe({
      next: (data) => {
        this.demografia = data;
      },
      error: (error) => console.error('Error loading demografia:', error)
    });
  }

  getStatusBadgeClass(status: string): string {
    const classes: Record<string, string> = {
      'VERDE': 'bg-secondary-container text-on-secondary-container',
      'AMBAR': 'bg-amber-100 text-amber-900',
      'ROJO': 'bg-error-container text-on-error-container',
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
