import { ChangeDetectorRef, Component, DestroyRef, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { catchError, EMPTY, Subject, switchMap } from 'rxjs';
import { MunicipioService } from '../../core/services/municipio.service';
import { Convocatoria, Municipio } from '../../core/models/municipio.model';

@Component({
  selector: 'app-convocatorias',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  template: `
    <div class="p-6">
      <h1 class="text-headline-lg-mobile text-on-surface sm:text-headline-md">
        Convocatorias BDNS
      </h1>
      <p class="mt-1 text-body-md text-on-surface-variant">
        Catálogo de subvenciones y ayudas públicas.
      </p>
      <section class="card my-5 rounded-xl p-5 sm:p-6">
        <h2 class="mb-4 border-b border-surface-container pb-3 text-headline-sm font-semibold">
          Filtros
        </h2>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-3 md:items-end">
          <label class="block text-body-md font-semibold text-on-surface">
            Categoría
            <input
              class="mt-1 w-full rounded-lg border border-outline-variant bg-white px-3 py-2 text-body-md font-normal text-on-surface focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              [(ngModel)]="categoria"
              (change)="load()"
              placeholder="Ej. vivienda"
            />
          </label>
          <label class="block text-body-md font-semibold text-on-surface">
            Municipio
            <select
              class="mt-1 w-full rounded-lg border border-outline-variant bg-white px-3 py-2 text-body-md font-normal text-on-surface focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              [(ngModel)]="municipio"
              (change)="load()"
            >
              <option value="">Todos</option>
              <option *ngFor="let m of municipios" [value]="m.codigo_ine">{{ m.nombre }}</option>
            </select>
          </label>
          <label class="flex items-center gap-2 py-2 text-body-md text-on-surface">
            <input
              type="checkbox"
              class="h-4 w-4 accent-primary"
              [(ngModel)]="incluirCerradas"
              (change)="load()"
            />
            Incluir convocatorias cerradas
          </label>
        </div>
      </section>
      <p
        *ngIf="municipiosError"
        class="mb-4 rounded-lg bg-error-container px-4 py-3 text-body-md text-on-error-container"
        role="alert"
      >
        {{ municipiosError }}
      </p>
      <div
        *ngIf="loading"
        role="status"
        class="mb-4 flex w-fit max-w-full items-center gap-3 rounded-lg bg-surface-container-low px-4 py-3 text-body-md text-on-surface-variant"
      >
        <span
          aria-hidden="true"
          class="h-4 w-4 shrink-0 rounded-full border-2 border-outline-variant border-t-primary motion-safe:animate-spin"
        ></span>
        <span>Cargando convocatorias...</span>
      </div>
      <p
        *ngIf="error"
        class="mb-4 rounded-lg bg-error-container px-4 py-3 text-body-md text-on-error-container"
        role="alert"
      >
        {{ error }}
      </p>
      <p
        *ngIf="!loading && !error && !convocatorias.length"
        class="rounded-lg bg-surface-container-low px-4 py-3 text-body-md text-on-surface-variant"
      >
        No hay convocatorias para estos filtros.
      </p>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <article *ngFor="let c of convocatorias" class="card flex flex-col rounded-xl p-5 sm:p-6">
          <div class="mb-4 border-b border-surface-container pb-3">
            <div class="mb-2 flex flex-wrap items-center gap-2 text-body-sm">
              <span class="font-semibold text-on-surface-variant">BDNS {{ c.codigo_bdns }}</span>
              <span
                class="rounded-full px-2 py-1 text-label-sm font-semibold"
                [ngClass]="
                  c.abierta
                    ? 'bg-green-100 text-green-900'
                    : 'bg-surface-container text-on-surface-variant'
                "
                >{{ c.abierta ? 'Abierta' : 'Cerrada' }}</span
              >
            </div>
            <h2 class="text-headline-sm font-semibold text-on-surface">{{ c.descripcion }}</h2>
          </div>
          <p class="text-body-md font-semibold text-on-surface">{{ c.organo_convocante }}</p>
          <p class="mt-1 text-body-sm text-on-surface-variant">
            {{ c.finalidad || 'Sin categoría' }}
          </p>
          <dl class="mt-4 grid grid-cols-1 gap-3 text-body-md sm:grid-cols-2">
            <div class="rounded-lg bg-surface-container-low p-3">
              <dt class="text-on-surface-variant">Presupuesto</dt>
              <dd class="font-semibold text-on-surface">
                {{ c.presupuesto_total | number: '1.0-0' }} €
              </dd>
            </div>
            <div class="rounded-lg bg-surface-container-low p-3">
              <dt class="text-on-surface-variant">Fin de solicitud</dt>
              <dd class="font-semibold text-on-surface">
                {{
                  c.fin_solicitud
                    ? (c.fin_solicitud | date: 'dd/MM/yyyy')
                    : 'Sin fecha de cierre publicada'
                }}
              </dd>
            </div>
          </dl>
          <p *ngIf="c.tipo_beneficiario" class="mt-3 text-body-sm text-on-surface-variant">
            Destinatarios: {{ c.tipo_beneficiario }}
          </p>
          <p *ngIf="c.regla_asignacion" class="mt-2 text-body-sm text-on-surface-variant">
            Criterio: {{ etiquetaRegla(c.regla_asignacion) }}
          </p>
          <a
            *ngIf="c.url_bases"
            [href]="c.url_bases"
            target="_blank"
            rel="noopener noreferrer"
            class="mt-4 inline-block text-body-md font-semibold text-primary underline"
            >Ver bases oficiales</a
          >
        </article>
      </div>
    </div>
  `,
})
export class ConvocatoriasComponent implements OnInit {
  convocatorias: Convocatoria[] = [];
  municipios: Municipio[] = [];
  categoria = '';
  municipio = '';
  incluirCerradas = false;
  loading = false;
  error: string | null = null;
  municipiosError: string | null = null;
  private readonly destroyRef = inject(DestroyRef);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly requests = new Subject<void>();

  constructor(
    private municipioService: MunicipioService,
    private route: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    this.requests
      .pipe(
        switchMap(() => {
          this.loading = true;
          this.error = null;
          this.cdr.markForCheck();
          return this.municipioService
            .getConvocatorias({
              codigo_ine: this.municipio,
              categoria: this.categoria,
              solo_abiertas: !this.incluirCerradas,
            })
            .pipe(
              catchError((err) => {
                console.error('Error al cargar convocatorias:', err);
                this.error = 'No se pudieron cargar las convocatorias.';
                this.loading = false;
                this.cdr.markForCheck();
                return EMPTY;
              }),
            );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((data) => {
        this.convocatorias = data;
        this.loading = false;
        this.cdr.markForCheck();
      });
    this.municipioService
      .getMunicipios()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.municipios = data.slice().sort((a, b) => a.nombre.localeCompare(b.nombre));
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('Error al cargar municipios:', err);
          this.municipiosError = 'No se pudo cargar el selector de municipios.';
          this.cdr.markForCheck();
        },
      });
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.municipio = params.get('municipio') ?? '';
      this.load();
    });
  }

  load(): void {
    this.requests.next();
  }
  etiquetaRegla(regla: string): string {
    const etiquetas: Record<string, string> = {
      organo_local: 'Ayuda local',
      umbral_poblacion: 'Por tamaño de población',
      region_completa: 'Ayuda regional',
    };
    return etiquetas[regla] ?? regla;
  }
}
