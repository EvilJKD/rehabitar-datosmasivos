import { ChangeDetectorRef, Component, DestroyRef, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { catchError, EMPTY, switchMap } from 'rxjs';
import { MunicipioService } from '../../core/services/municipio.service';
import { Demografia, MunicipioDetail } from '../../core/models/municipio.model';
import { RutaSanitariaComponent } from '../../shared/components/ruta-sanitaria/ruta-sanitaria.component';
import { SemaforoLabelPipe } from '../../shared/pipes/semaforo-label.pipe';

@Component({
  selector: 'app-municipio-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, RutaSanitariaComponent, SemaforoLabelPipe],
  template: `
    <div class="p-6">
      <a routerLink="/dashboard" class="text-primary underline">← Volver al dashboard</a>
      <div
        *ngIf="loading"
        role="status"
        class="mt-4 flex w-fit max-w-full items-center gap-3 rounded-lg bg-surface-container-low px-4 py-3 text-body-md text-on-surface-variant"
      >
        <span
          aria-hidden="true"
          class="h-4 w-4 shrink-0 rounded-full border-2 border-outline-variant border-t-primary motion-safe:animate-spin"
        ></span>
        <span>Obteniendo datos oficiales y calculando ruta...</span>
      </div>
      <p *ngIf="error" class="text-error-700 mt-4" role="alert">{{ error }}</p>
      <ng-container *ngIf="municipio as m">
        <div class="my-5 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 class="text-headline-lg-mobile text-on-surface sm:text-headline-md">
              {{ m.nombre }}
            </h1>
            <p class="mt-1 text-body-md text-on-surface-variant">
              <span class="font-semibold">INE {{ m.codigo_ine }}</span> · {{ m.comarca }} ·
              {{ m.provincia }}
            </p>
            <p
              class="mt-3 inline-flex max-w-full flex-wrap items-center gap-x-2 gap-y-1 rounded-lg bg-surface-container-low px-3 py-2"
            >
              <span
                class="text-label-sm font-semibold uppercase tracking-wide text-on-surface-variant"
                >Origen de datos</span
              >
              <span class="break-all text-body-sm font-medium text-on-surface">{{
                m.origen_datos
              }}</span>
            </p>
          </div>
          <button class="btn-primary" (click)="refresh()" [disabled]="loading">
            Actualizar datos ahora
          </button>
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <section class="card rounded-xl p-5 sm:p-6">
            <h2 class="mb-4 border-b border-surface-container pb-3 text-headline-sm font-semibold">
              Viabilidad
            </h2>
            <ng-container *ngIf="m.wlc as w; else noWlc">
              <div class="mb-4 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span class="text-2xl font-semibold text-primary"
                  >{{ w.indice_wlc | number: '1.1-1' }}
                  <span class="text-body-sm font-normal text-on-surface-variant">/ 100</span></span
                >
                <span class="text-body-sm font-semibold text-on-surface"
                  >{{ w.semaforo | semaforoLabel }} · {{ w.etiqueta_viabilidad }}</span
                >
              </div>
              <ul
                class="grid grid-cols-1 gap-2 text-body-md text-on-surface-variant sm:grid-cols-2 sm:gap-x-6"
              >
                <li class="flex justify-between gap-4">
                  <span>Carretera</span
                  ><span class="font-semibold text-on-surface">{{
                    w.score_acceso_carretera | number: '1.1-1'
                  }}</span>
                </li>
                <li class="flex justify-between gap-4">
                  <span>Sanidad</span
                  ><span class="font-semibold text-on-surface">{{
                    w.score_proximidad_sanitaria | number: '1.1-1'
                  }}</span>
                </li>
                <li class="flex justify-between gap-4">
                  <span>Conectividad</span
                  ><span class="font-semibold text-on-surface">{{
                    w.score_conectividad_digital | number: '1.1-1'
                  }}</span>
                </li>
                <li class="flex justify-between gap-4">
                  <span>Agua</span
                  ><span class="font-semibold text-on-surface">{{
                    w.score_acceso_hidrico | number: '1.1-1'
                  }}</span>
                </li>
                <li class="flex justify-between gap-4">
                  <span>Demografía</span
                  ><span class="font-semibold text-on-surface">{{
                    w.score_inercia_demografica | number: '1.1-1'
                  }}</span>
                </li>
              </ul>
            </ng-container>
            <ng-template #noWlc
              ><p class="text-body-md text-on-surface-variant">
                Sin datos de viabilidad.
              </p></ng-template
            >
          </section>
          <section class="card rounded-xl p-5 sm:p-6">
            <h2 class="mb-4 border-b border-surface-container pb-3 text-headline-sm font-semibold">
              Infraestructura
            </h2>
            <ng-container *ngIf="m.infraestructura as infra; else noInfra">
              <dl class="grid grid-cols-2 gap-3 text-body-md">
                <div class="rounded-lg bg-surface-container-low p-3">
                  <dt class="text-on-surface-variant">Fibra</dt>
                  <dd class="font-semibold">{{ infra.cobertura_fibra_pct }}%</dd>
                </div>
                <div class="rounded-lg bg-surface-container-low p-3">
                  <dt class="text-on-surface-variant">Móvil</dt>
                  <dd class="font-semibold">{{ infra.cobertura_movil_pct }}%</dd>
                </div>
                <div class="rounded-lg bg-surface-container-low p-3">
                  <dt class="text-on-surface-variant">Carretera</dt>
                  <dd class="font-semibold">{{ infra.distancia_carretera_km }} km</dd>
                </div>
                <div class="rounded-lg bg-surface-container-low p-3">
                  <dt class="text-on-surface-variant">Agua</dt>
                  <dd class="font-semibold">{{ infra.distancia_recurso_hidrico_km }} km</dd>
                </div>
              </dl>
              <p class="mt-3 text-body-sm text-on-surface-variant">
                Actualizado: {{ infra.fecha_actualizacion }}
              </p>
            </ng-container>
            <ng-template #noInfra
              ><p class="text-body-md text-on-surface-variant">
                Sin datos de infraestructura.
              </p></ng-template
            >
          </section>
          <section class="card rounded-xl p-5 sm:p-6">
            <h2 class="mb-4 border-b border-surface-container pb-3 text-headline-sm font-semibold">
              Urgencias más cercanas
            </h2>
            <ng-container *ngIf="m.urgencias_mas_cercana as urg; else noUrg">
              <p class="text-body-md font-semibold text-on-surface">
                {{ urg.nombre }} · {{ urg.tipo }} ·
                {{ urg.tiene_urgencias ? 'Con urgencias' : 'Sin urgencias' }}
              </p>
              <p class="mt-2 text-body-md text-on-surface-variant">
                {{ urg.direccion || 'Dirección no disponible' }} ·
                {{ urg.horario || 'Horario no disponible' }} ·
                {{ urg.telefono || 'Teléfono no disponible' }}
              </p>
              <p class="mt-2 text-body-md text-on-surface-variant">
                Distancia por carretera: {{ urg.distancia_carretera_km ?? 'No disponible' }} km ·
                Tiempo: {{ urg.tiempo_estimado_min ?? 'No disponible' }} min
              </p>
              <p class="mt-2 text-body-sm text-on-surface-variant">
                Fuente: {{ urg.fuente_ruta || 'No disponible' }}
              </p>
              <app-ruta-sanitaria [ruta]="urg" />
            </ng-container>
            <ng-template #noUrg
              ><p class="text-body-md text-on-surface-variant">
                Sin centro sanitario disponible.
              </p></ng-template
            >
          </section>
          <section class="card rounded-xl p-5 sm:p-6">
            <h2 class="mb-4 border-b border-surface-container pb-3 text-headline-sm font-semibold">
              Ayudas disponibles ({{ m.convocatorias.length }})
            </h2>
            <ul class="space-y-3 text-body-md text-on-surface-variant">
              <li *ngFor="let conv of m.convocatorias">
                {{ conv.descripcion }}
                <a
                  *ngIf="conv.url_bases"
                  [href]="conv.url_bases"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-primary underline"
                  >Ver bases</a
                >
              </li>
            </ul>
            <a
              class="mt-4 inline-block text-body-md font-semibold text-primary underline"
              routerLink="/convocatorias"
              [queryParams]="{ municipio: m.codigo_ine }"
              >Ver convocatorias</a
            >
          </section>
        </div>
        <section class="card mt-4 rounded-xl p-5 sm:p-6">
          <h2 class="mb-4 border-b border-surface-container pb-3 text-headline-sm font-semibold">
            Demografía
          </h2>
          <p class="text-body-md text-on-surface-variant">
            Inercia: {{ m.inercia_demografica }} · Preserva masa crítica:
            {{ m.preserva_masa_critica ? 'Sí' : 'No' }}
          </p>
          <p *ngIf="demografiaError" class="mt-2 text-body-md text-error" role="alert">
            {{ demografiaError }}
          </p>
          <ng-container *ngIf="demografia as d">
            <p class="mt-2 text-body-md text-on-surface-variant">
              Población inicial: {{ d.poblacion_inicial_10a ?? 'Sin datos' }} · Actual:
              {{ d.poblacion_actual }} · Variación:
              {{ d.variacion_10a_pct === null ? 'Sin datos' : d.variacion_10a_pct + '%' }}
            </p>
            <div class="mt-4 overflow-x-auto rounded-lg border border-surface-container">
              <table class="w-full min-w-[34rem] text-left text-body-sm">
                <thead>
                  <tr class="bg-surface-container-low">
                    <th scope="col" class="px-3 py-2 font-semibold">Año</th>
                    <th scope="col" class="px-3 py-2 font-semibold">Población</th>
                    <th scope="col" class="px-3 py-2 font-semibold">Mayores de 65</th>
                    <th scope="col" class="px-3 py-2 font-semibold">Menores de 15</th>
                    <th scope="col" class="px-3 py-2 font-semibold">Envejecimiento</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    *ngFor="let p of d.serie_anual"
                    class="border-t border-surface-container text-on-surface-variant"
                  >
                    <td class="px-3 py-2">{{ p.anio }}</td>
                    <td class="px-3 py-2">{{ p.poblacion }}</td>
                    <td class="px-3 py-2">{{ p.poblacion_mayor_65 ?? '—' }}</td>
                    <td class="px-3 py-2">{{ p.poblacion_menor_15 ?? '—' }}</td>
                    <td class="px-3 py-2">{{ p.tasa_envejecimiento ?? '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p *ngIf="!d.serie_anual.length" class="mt-3 text-body-md text-on-surface-variant">
              Sin serie histórica disponible.
            </p>
          </ng-container>
        </section>
      </ng-container>
    </div>
  `,
})
export class MunicipioDetailComponent implements OnInit {
  municipio: MunicipioDetail | null = null;
  demografia: Demografia | null = null;
  loading = true;
  error: string | null = null;
  demografiaError: string | null = null;
  private readonly destroyRef = inject(DestroyRef);
  private readonly cdr = inject(ChangeDetectorRef);

  constructor(
    private route: ActivatedRoute,
    private municipioService: MunicipioService,
  ) {}

  ngOnInit(): void {
    this.route.paramMap
      .pipe(
        switchMap((params) => {
          this.loading = true;
          this.error = null;
          this.municipio = null;
          this.demografia = null;
          this.demografiaError = null;
          this.cdr.markForCheck();
          return this.municipioService.getMunicipioDetail(params.get('codigo_ine')!).pipe(
            catchError((err) => {
              console.error('Error al cargar municipio:', err);
              this.error = 'No se pudo cargar el municipio.';
              this.loading = false;
              this.cdr.markForCheck();
              return EMPTY;
            }),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (m) => {
          this.municipio = m;
          this.loading = false;
          this.cdr.markForCheck();
          this.loadDemografia(m.codigo_ine);
        },
      });
  }

  refresh(): void {
    if (!this.municipio) return;
    const codigo = this.municipio.codigo_ine;
    this.loading = true;
    this.error = null;
    this.cdr.markForCheck();
    this.municipioService
      .triggerMunicipioIngestion(codigo)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (m) => {
          if (this.route.snapshot.paramMap.get('codigo_ine') !== codigo) return;
          this.municipio = m;
          this.loading = false;
          this.cdr.markForCheck();
          this.loadDemografia(m.codigo_ine);
        },
        error: (err) => {
          console.error('Error al actualizar municipio:', err);
          if (this.route.snapshot.paramMap.get('codigo_ine') === codigo) {
            this.error = 'No se pudieron actualizar los datos.';
            this.loading = false;
            this.cdr.markForCheck();
          }
        },
      });
  }

  private loadDemografia(codigo: string): void {
    this.demografia = null;
    this.demografiaError = null;
    this.cdr.markForCheck();
    this.municipioService
      .getDemografia(codigo)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          if (this.municipio?.codigo_ine === codigo) {
            this.demografia = data;
            this.cdr.markForCheck();
          }
        },
        error: (err) => {
          console.error('Error al cargar demografía:', err);
          if (this.municipio?.codigo_ine === codigo) {
            this.demografiaError = 'No se pudo cargar la serie demográfica.';
            this.cdr.markForCheck();
          }
        },
      });
  }
}
