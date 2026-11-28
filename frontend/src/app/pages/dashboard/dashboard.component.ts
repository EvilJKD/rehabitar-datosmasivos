import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { FiltrosMunicipios, MunicipioService, Pesos } from '../../core/services/municipio.service';
import { Municipio, KPISummary, Health } from '../../core/models/municipio.model';
import { KpiCardComponent } from '../../shared/components/kpi-card/kpi-card.component';
import { TerritorioMapComponent } from '../../shared/components/territorio-map/territorio-map.component';
import { RangoMunicipalComponent } from '../../shared/components/rango-municipal/rango-municipal.component';
import { SemaforoLabelPipe } from '../../shared/pipes/semaforo-label.pipe';

/**
 * DashboardComponent - Main landing page
 * Displays 5 KPI cards, territorial WLC map, and municipality ranking
 * 
 * Layout:
 * - Desktop (xl): 2 rows
 *   - Row 1: 5 KPI cards (100% width)
 *   - Row 2: Map (66%) + Ranking table (34%)
 * - Tablet (lg): Stacked vertically
 * - Mobile: Full-width cards
 */
@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    KpiCardComponent,
    TerritorioMapComponent,
    RangoMunicipalComponent,
    SemaforoLabelPipe
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DashboardComponent implements OnInit, OnDestroy {
  kpiData: KPISummary | null = null;
  municipios: Municipio[] = [];
  isLoading = true;
  error: string | null = null;
  health: Health | null = null;
  healthError = false;
  activeFilter: 'all' | 'wlc_fibra' | 'ayudas' = 'all';
  showWeights = false;
  customWeightsActive = false;
  weights: Required<Pick<Pesos, 'w_carretera' | 'w_sanidad' | 'w_conectividad' | 'w_hidrico' | 'w_demografia'>> = {
    w_carretera: 0.25,
    w_sanidad: 0.2,
    w_conectividad: 0.2,
    w_hidrico: 0.15,
    w_demografia: 0.2,
  };

  private destroy$ = new Subject<void>();

  constructor(private municipioService: MunicipioService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.loadDashboardData();
    this.municipioService.healthCheck().pipe(takeUntil(this.destroy$)).subscribe({
      next: health => { this.health = health; this.cdr.markForCheck(); },
      error: err => { console.error('Error de estado del sistema:', err); this.healthError = true; this.cdr.markForCheck(); }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Load all dashboard data:
   * - Fetch municipios list
   * - Calculate KPIs from WLC scores
   * - Trigger map and ranking updates
   */
  loadDashboardData(filters: FiltrosMunicipios = {}): void {
    this.isLoading = true;
    this.error = null;
    const effectiveFilters: FiltrosMunicipios = this.customWeightsActive
      ? { ...filters, ...this.weights }
      : filters;

    this.municipioService
      .getMunicipios(effectiveFilters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (municipios: Municipio[]) => {
          this.municipios = municipios;
          this.kpiData = this.calculateKPIs(municipios);
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('Error loading dashboard:', err);
          this.error = 'No se pudieron cargar los datos del dashboard';
          this.isLoading = false;
          this.cdr.markForCheck();
        }
      });
  }

  setFilter(filter: 'all' | 'wlc_fibra' | 'ayudas'): void {
    this.activeFilter = filter;
    this.cdr.markForCheck();
  }

  applyWeights(): void {
    this.customWeightsActive = true;
    this.loadDashboardData(this.getActiveFilterParams());
  }

  resetWeights(): void {
    this.weights = {
      w_carretera: 0.25,
      w_sanidad: 0.2,
      w_conectividad: 0.2,
      w_hidrico: 0.15,
      w_demografia: 0.2,
    };
    this.customWeightsActive = false;
    this.loadDashboardData(this.getActiveFilterParams());
  }

  private getActiveFilterParams(): FiltrosMunicipios {
    if (this.activeFilter === 'wlc_fibra') return { min_wlc: 75, requiere_fibra: true };
    if (this.activeFilter === 'ayudas') return { con_ayuda_abierta: true };
    return {};
  }

  private calculateKPIs(municipios: Municipio[]): KPISummary {
    const summary: KPISummary = {
      total_analizados: municipios.length,
      riesgo_alto: 0,
      riesgo_medio: 0,
      favorable: 0,
      pendientes: 0
    };

    municipios.forEach((municipio) => {
      switch (municipio.wlc?.semaforo ?? 'PENDIENTE') {
        case 'ROJO': summary.riesgo_alto++; break;
        case 'AMBAR': summary.riesgo_medio++; break;
        case 'VERDE': summary.favorable++; break;
        case 'PENDIENTE': summary.pendientes++; break;
      }
    });

    return summary;
  }
}
