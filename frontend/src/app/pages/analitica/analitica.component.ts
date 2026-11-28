import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  DestroyRef,
  ElementRef,
  inject,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { catchError, forkJoin, of } from 'rxjs';
import Chart from 'chart.js/auto';
import { MunicipioService } from '../../core/services/municipio.service';
import { Demografia, Municipio } from '../../core/models/municipio.model';

const PALETTE = ['#25834c', '#005eb8', '#d18b16', '#c83e3e', '#6f42c1', '#0f766e'];

/**
 * Visualización 2 (Propuesta Sección 6.4):
 * Dashboard Analítico Temporal y Multivariable con Chart.js.
 * Permite seleccionar uno o varios municipios rurales y comparar su evolución
 * poblacional (2015-2025) frente a cobertura de fibra, distancia a urgencias y ayudas abiertas.
 */
@Component({
  selector: 'app-analitica',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="min-h-screen bg-gradient-to-br from-surface-50 to-surface-100 p-6">
      <div class="mb-6 border-b-2 border-surface-container pb-4">
        <h1 class="text-headline-lg-mobile text-primary font-heading-bold sm:text-headline-md">
          Dashboard Analítico Temporal y Multivariable
        </h1>
        <p class="mt-1 text-body-md text-on-surface-variant">
          Compara la evolución poblacional (2015-2025) frente a cobertura de fibra óptica,
          distancia a urgencias y ayudas públicas abiertas.
        </p>
      </div>

      <!-- Selector multi-municipio -->
      <section class="card mb-6 rounded-xl p-5 sm:p-6">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-surface-container pb-3">
          <div>
            <h2 class="text-headline-sm font-semibold text-on-surface">
              Selección de municipios ({{ selectedCodes.length }} seleccionados, máx. 6)
            </h2>
            <p class="text-body-sm text-on-surface-variant">
              Marca uno o varios municipios rurales para compararlos en las gráficas.
            </p>
          </div>
          <input
            type="search"
            [(ngModel)]="searchTerm"
            placeholder="Filtrar municipio..."
            aria-label="Filtrar municipio en comparador"
            class="w-full rounded-lg border border-outline-variant bg-white px-3 py-2 text-body-sm text-on-surface focus:border-primary focus:outline-none sm:w-64"
          />
        </div>

        <p *ngIf="listError" class="rounded-lg bg-error-container px-4 py-3 text-body-md text-on-error-container" role="alert">
          {{ listError }}
        </p>

        <div class="flex max-h-44 flex-wrap gap-2 overflow-y-auto py-1">
          <button
            *ngFor="let m of filteredMunicipios"
            type="button"
            (click)="toggleMunicipio(m.codigo_ine)"
            [attr.aria-pressed]="isSelected(m.codigo_ine)"
            class="rounded-full border px-3 py-1.5 text-body-sm font-medium transition"
            [ngClass]="
              isSelected(m.codigo_ine)
                ? 'border-primary bg-primary text-white'
                : 'border-outline-variant bg-white text-on-surface hover:bg-surface-container-low'
            "
          >
            {{ m.nombre }}
            <span *ngIf="m.hidratado" class="ml-1 opacity-75">· {{ m.poblacion_actual ?? '—' }} hab.</span>
          </button>
        </div>
      </section>

      <div
        *ngIf="loadingCharts"
        role="status"
        class="mb-4 flex w-fit items-center gap-3 rounded-lg bg-surface-container-low px-4 py-3 text-body-md text-on-surface-variant"
      >
        <span
          aria-hidden="true"
          class="h-4 w-4 shrink-0 rounded-full border-2 border-outline-variant border-t-primary motion-safe:animate-spin"
        ></span>
        <span>Cargando series demográficas y métricas...</span>
      </div>

      <p
        *ngIf="chartError"
        class="mb-4 rounded-lg bg-error-container px-4 py-3 text-body-md text-on-error-container"
        role="alert"
      >
        {{ chartError }}
      </p>

      <p
        *ngIf="!loadingCharts && !series.length && !chartError"
        class="rounded-lg bg-surface-container-low px-4 py-3 text-body-md text-on-surface-variant"
      >
        Selecciona al menos un municipio para visualizar las gráficas comparativas.
      </p>

      <!-- Gráficas Chart.js -->
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2" [class.hidden]="!series.length">
        <section class="card rounded-xl p-5 sm:p-6">
          <h2 class="mb-1 text-headline-sm font-semibold text-on-surface">
            Evolución Poblacional (2015-2025)
          </h2>
          <p class="mb-4 text-body-sm text-on-surface-variant">
            Habitantes empadronados por año según la API Tempus del INE (Tabla 2881).
          </p>
          <div class="relative h-80 w-full">
            <canvas #evolucionCanvas aria-label="Gráfico de evolución poblacional"></canvas>
          </div>
        </section>

        <section class="card rounded-xl p-5 sm:p-6">
          <h2 class="mb-1 text-headline-sm font-semibold text-on-surface">
            Correlación Multivariable: Conectividad, Urgencias y Ayudas
          </h2>
          <p class="mb-4 text-body-sm text-on-surface-variant">
            Variación poblacional 10 años (%) y cobertura de fibra (%) frente a distancia a urgencias (km) y ayudas abiertas.
          </p>
          <div class="relative h-80 w-full">
            <canvas #multivariableCanvas aria-label="Gráfico multivariable de correlaciones"></canvas>
          </div>
        </section>
      </div>

      <!-- Tabla comparativa resumen -->
      <section *ngIf="series.length" class="card mt-6 rounded-xl p-5 sm:p-6">
        <h2 class="mb-4 border-b border-surface-container pb-3 text-headline-sm font-semibold text-on-surface">
          Resumen Comparativo (Consulta 3)
        </h2>
        <div class="overflow-x-auto">
          <table class="table-base min-w-[40rem]">
            <thead>
              <tr>
                <th scope="col">Municipio</th>
                <th scope="col">Población inicial</th>
                <th scope="col">Población actual</th>
                <th scope="col">Variación 10 años</th>
                <th scope="col">Fibra óptica</th>
                <th scope="col">Distancia urgencias</th>
                <th scope="col">Ayudas abiertas</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let s of series">
                <td>
                  <a class="font-semibold text-primary underline" [routerLink]="['/municipio', s.codigo_ine]">
                    {{ s.nombre }}
                  </a>
                </td>
                <td>{{ s.poblacion_inicial_10a ?? '—' }}</td>
                <td>{{ s.poblacion_actual }}</td>
                <td>{{ s.variacion_10a_pct === null ? 'Sin datos' : s.variacion_10a_pct + '%' }}</td>
                <td>{{ s.cobertura_fibra_pct === null ? '—' : s.cobertura_fibra_pct + '%' }}</td>
                <td>{{ s.distancia_urgencias_km === null ? '—' : (s.distancia_urgencias_km | number: '1.1-1') + ' km' }}</td>
                <td>{{ s.num_ayudas_abiertas ?? 0 }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `,
})
export class AnaliticaComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('evolucionCanvas') evolucionCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('multivariableCanvas') multivariableCanvas?: ElementRef<HTMLCanvasElement>;

  municipios: Municipio[] = [];
  selectedCodes: string[] = [];
  series: Demografia[] = [];
  searchTerm = '';
  loadingCharts = false;
  listError: string | null = null;
  chartError: string | null = null;

  private evolucionChart?: Chart;
  private multivariableChart?: Chart;
  private viewReady = false;
  private readonly destroyRef = inject(DestroyRef);
  private readonly cdr = inject(ChangeDetectorRef);

  constructor(
    private municipioService: MunicipioService,
    private route: ActivatedRoute,
  ) {}

  get filteredMunicipios(): Municipio[] {
    const term = this.searchTerm.trim().toLowerCase();
    return this.municipios.filter((m) => !term || m.nombre.toLowerCase().includes(term));
  }

  ngOnInit(): void {
    const queryParam = this.route.snapshot.queryParamMap.get('municipios');
    const requestedCodes = queryParam
      ? queryParam
          .split(',')
          .map((c) => c.trim())
          .filter(Boolean)
      : [];

    this.municipioService
      .getMunicipios()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (list) => {
          this.municipios = list.slice().sort((a, b) => a.nombre.localeCompare(b.nombre));
          if (requestedCodes.length) {
            this.selectedCodes = requestedCodes.slice(0, 6);
          } else {
            const hydrated = this.municipios.filter((m) => m.hidratado).slice(0, 3);
            const fallback = hydrated.length ? hydrated : this.municipios.slice(0, 3);
            this.selectedCodes = fallback.map((m) => m.codigo_ine);
          }
          this.cdr.markForCheck();
          this.loadSelectedSeries();
        },
        error: (err) => {
          console.error('Error al cargar municipios para analítica:', err);
          this.listError = 'No se pudo cargar el listado de municipios.';
          this.cdr.markForCheck();
        },
      });
  }

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.renderCharts();
  }

  ngOnDestroy(): void {
    this.destroyCharts();
  }

  isSelected(codigoIne: string): boolean {
    return this.selectedCodes.includes(codigoIne);
  }

  toggleMunicipio(codigoIne: string): void {
    if (this.isSelected(codigoIne)) {
      this.selectedCodes = this.selectedCodes.filter((c) => c !== codigoIne);
    } else if (this.selectedCodes.length < 6) {
      this.selectedCodes = [...this.selectedCodes, codigoIne];
    }
    this.loadSelectedSeries();
  }

  loadSelectedSeries(): void {
    if (!this.selectedCodes.length) {
      this.series = [];
      this.chartError = null;
      this.destroyCharts();
      this.cdr.markForCheck();
      return;
    }

    this.loadingCharts = true;
    this.chartError = null;
    this.cdr.markForCheck();

    const calls = this.selectedCodes.map((code) =>
      this.municipioService.getDemografia(code).pipe(
        catchError((err) => {
          console.error(`Error al cargar demografía de ${code}:`, err);
          return of(null);
        }),
      ),
    );

    forkJoin(calls)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (results) => {
          this.series = results.filter((r): r is Demografia => r !== null);
          if (!this.series.length) {
            this.chartError = 'No se pudieron cargar las series demográficas seleccionadas.';
          }
          this.loadingCharts = false;
          this.cdr.markForCheck();
          this.renderCharts();
        },
        error: () => {
          this.chartError = 'No se pudieron cargar las series demográficas seleccionadas.';
          this.loadingCharts = false;
          this.cdr.markForCheck();
        },
      });
  }

  private destroyCharts(): void {
    this.evolucionChart?.destroy();
    this.evolucionChart = undefined;
    this.multivariableChart?.destroy();
    this.multivariableChart = undefined;
  }

  private renderCharts(): void {
    if (!this.viewReady || !this.series.length) return;
    this.destroyCharts();

    const evoCtx = this.evolucionCanvas?.nativeElement.getContext('2d');
    if (evoCtx) {
      const years = Array.from(
        new Set(this.series.flatMap((s) => s.serie_anual.map((p) => p.anio))),
      ).sort((a, b) => a - b);

      this.evolucionChart = new Chart(evoCtx, {
        type: 'line',
        data: {
          labels: years.map(String),
          datasets: this.series.map((s, idx) => {
            const byYear = new Map(s.serie_anual.map((p) => [p.anio, p.poblacion]));
            const color = PALETTE[idx % PALETTE.length];
            return {
              label: s.nombre,
              data: years.map((y) => byYear.get(y) ?? null),
              borderColor: color,
              backgroundColor: color,
              tension: 0.25,
              spanGaps: true,
            };
          }),
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'bottom' } },
          scales: {
            y: { title: { display: true, text: 'Habitantes' } },
            x: { title: { display: true, text: 'Año' } },
          },
        },
      });
    }

    const multiCtx = this.multivariableCanvas?.nativeElement.getContext('2d');
    if (multiCtx) {
      const labels = this.series.map((s) => s.nombre);
      this.multivariableChart = new Chart(multiCtx, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            {
              label: 'Cobertura fibra (%)',
              data: this.series.map((s) => s.cobertura_fibra_pct ?? 0),
              backgroundColor: '#25834c',
              yAxisID: 'yPct',
            },
            {
              label: 'Variación población 10a (%)',
              data: this.series.map((s) => s.variacion_10a_pct ?? 0),
              backgroundColor: '#d18b16',
              yAxisID: 'yPct',
            },
            {
              label: 'Distancia urgencias (km)',
              data: this.series.map((s) => s.distancia_urgencias_km ?? 0),
              backgroundColor: '#005eb8',
              yAxisID: 'yAux',
            },
            {
              label: 'Ayudas abiertas',
              data: this.series.map((s) => s.num_ayudas_abiertas ?? 0),
              backgroundColor: '#6f42c1',
              yAxisID: 'yAux',
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'bottom' } },
          scales: {
            yPct: {
              type: 'linear',
              position: 'left',
              title: { display: true, text: 'Porcentaje (%)' },
            },
            yAux: {
              type: 'linear',
              position: 'right',
              grid: { drawOnChartArea: false },
              title: { display: true, text: 'Km / Nº ayudas' },
            },
          },
        },
      });
    }
  }
}
