import { Component, OnInit, OnDestroy, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { MunicipioService } from '../../core/services/municipio.service';
import { Municipio, KPISummary } from '../../core/models/municipio.model';
import { KpiCardComponent } from '../../shared/components/kpi-card/kpi-card.component';
import { TerritorioMapComponent } from '../../shared/components/territorio-map/territorio-map.component';
import { RangoMunicipalComponent } from '../../shared/components/rango-municipal/rango-municipal.component';

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
    KpiCardComponent,
    TerritorioMapComponent,
    RangoMunicipalComponent
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

  private destroy$ = new Subject<void>();

  constructor(private municipioService: MunicipioService) {}

  ngOnInit(): void {
    this.loadDashboardData();
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
  private loadDashboardData(): void {
    this.isLoading = true;
    this.error = null;

    this.municipioService
      .getMunicipios()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (municipios: Municipio[]) => {
          this.municipios = municipios;
          this.kpiData = this.calculateKPIs(municipios);
          this.isLoading = false;
        },
        error: (err) => {
          console.error('Error loading dashboard:', err);
          this.error = 'No se pudieron cargar los datos del dashboard';
          this.isLoading = false;
        }
      });
  }

  /**
   * Calculate KPI summary from municipalities array
   * 
   * Logic:
   * - Total analyzed: Count all municipios
   * - Alto riesgo (ROJO): WLC < 0.4
   * - Riesgo medio (ÁMBAR): 0.4 <= WLC <= 0.65
   * - Favorable (VERDE): WLC > 0.65
   * - Pendiente: No WLC score (not hydrated)
   */
  private calculateKPIs(municipios: Municipio[]): KPISummary {
    const summary: KPISummary = {
      total_analizados: municipios.length,
      riesgo_alto: 0,
      riesgo_medio: 0,
      favorable: 0,
      pendientes: 0
    };

    municipios.forEach((municipio) => {
      if (!municipio.wlc || municipio.wlc.indice_wlc === null) {
        summary.pendientes++;
      } else {
        const wlc = municipio.wlc.indice_wlc;
        if (wlc < 0.4) {
          summary.riesgo_alto++;
        } else if (wlc <= 0.65) {
          summary.riesgo_medio++;
        } else {
          summary.favorable++;
        }
      }
    });

    return summary;
  }
}
