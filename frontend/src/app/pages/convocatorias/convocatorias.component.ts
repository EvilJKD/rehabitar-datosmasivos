import { Component, DestroyRef, inject, OnInit } from '@angular/core';
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
      <h1 class="text-xl font-bold">Convocatorias BDNS</h1>
      <p>Catálogo de subvenciones y ayudas públicas.</p>
      <div class="card p-4 my-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        <label
          >Categoría
          <input
            class="border rounded p-2 w-full"
            [(ngModel)]="categoria"
            (change)="load()"
            placeholder="Ej. vivienda"
        /></label>
        <label
          >Municipio
          <select class="border rounded p-2 w-full" [(ngModel)]="municipio" (change)="load()">
            <option value="">Todos</option>
            <option *ngFor="let m of municipios" [value]="m.codigo_ine">{{ m.nombre }}</option>
          </select></label
        >
        <label
          ><input type="checkbox" [(ngModel)]="incluirCerradas" (change)="load()" /> Incluir
          convocatorias cerradas</label
        >
      </div>
      <p *ngIf="municipiosError" class="text-error-700" role="alert">{{ municipiosError }}</p>
      <p *ngIf="loading">Cargando convocatorias...</p>
      <p *ngIf="error" class="text-error-700" role="alert">{{ error }}</p>
      <p *ngIf="!loading && !error && !convocatorias.length">
        No hay convocatorias para estos filtros.
      </p>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <article *ngFor="let c of convocatorias" class="card p-4">
          <h2 class="text-xl font-bold">{{ c.descripcion }}</h2>
          <p>{{ c.codigo_bdns }} · {{ c.abierta ? 'Abierta' : 'Cerrada' }}</p>
          <p>{{ c.organo_convocante }} · {{ c.finalidad || 'Sin categoría' }}</p>
          <p>Presupuesto: {{ c.presupuesto_total | number: '1.0-0' }} €</p>
          <p>
            Fin:
            {{
              c.fin_solicitud
                ? (c.fin_solicitud | date: 'dd/MM/yyyy')
                : 'Sin fecha de cierre publicada'
            }}
          </p>
          <p *ngIf="c.tipo_beneficiario">Destinatarios: {{ c.tipo_beneficiario }}</p>
          <p *ngIf="c.regla_asignacion">Criterio: {{ etiquetaRegla(c.regla_asignacion) }}</p>
          <a
            *ngIf="c.url_bases"
            [href]="c.url_bases"
            target="_blank"
            rel="noopener noreferrer"
            class="text-primary underline"
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
                return EMPTY;
              }),
            );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((data) => {
        this.convocatorias = data;
        this.loading = false;
      });
    this.municipioService
      .getMunicipios()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.municipios = data.slice().sort((a, b) => a.nombre.localeCompare(b.nombre));
        },
        error: (err) => {
          console.error('Error al cargar municipios:', err);
          this.municipiosError = 'No se pudo cargar el selector de municipios.';
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
