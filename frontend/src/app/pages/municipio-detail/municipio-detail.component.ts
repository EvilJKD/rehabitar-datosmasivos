import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { catchError, EMPTY, switchMap } from 'rxjs';
import { MunicipioService } from '../../core/services/municipio.service';
import { Demografia, MunicipioDetail } from '../../core/models/municipio.model';
import { RutaSanitariaComponent } from '../../shared/components/ruta-sanitaria/ruta-sanitaria.component';

@Component({
  selector: 'app-municipio-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, RutaSanitariaComponent],
  template: `
    <div class="p-6">
      <a routerLink="/dashboard" class="text-primary underline">← Volver al dashboard</a>
      <p *ngIf="loading" class="mt-4">Obteniendo datos oficiales y calculando ruta...</p>
      <p *ngIf="error" class="text-error-700 mt-4" role="alert">{{ error }}</p>
      <ng-container *ngIf="municipio as m">
        <div class="flex flex-wrap justify-between gap-4 my-4">
          <div><h1 class="text-3xl font-bold">{{ m.nombre }}</h1><p>{{ m.codigo_ine }} · {{ m.comarca }} · {{ m.provincia }}</p></div>
          <button class="btn-primary" (click)="refresh()" [disabled]="loading">Actualizar datos ahora</button>
        </div>
        <p>Origen: {{ m.origen_datos }}</p>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <section class="card p-4">
            <h2 class="text-xl font-bold">Viabilidad</h2>
            <ng-container *ngIf="m.wlc as w; else noWlc">
              <p>{{ w.semaforo }} · {{ w.indice_wlc | number:'1.1-1' }} / 100 · {{ w.etiqueta_viabilidad }}</p>
              <ul><li>Carretera: {{ w.score_acceso_carretera | number:'1.1-1' }}</li>
                <li>Sanidad: {{ w.score_proximidad_sanitaria | number:'1.1-1' }}</li>
                <li>Conectividad: {{ w.score_conectividad_digital | number:'1.1-1' }}</li>
                <li>Agua: {{ w.score_acceso_hidrico | number:'1.1-1' }}</li>
                <li>Demografía: {{ w.score_inercia_demografica | number:'1.1-1' }}</li></ul>
            </ng-container>
            <ng-template #noWlc>Sin datos de viabilidad.</ng-template>
          </section>
          <section class="card p-4">
            <h2 class="text-xl font-bold">Infraestructura</h2>
            <ng-container *ngIf="m.infraestructura as infra; else noInfra">
              <p>Fibra: {{ infra.cobertura_fibra_pct }}% · Móvil: {{ infra.cobertura_movil_pct }}%</p>
              <p>Carretera: {{ infra.distancia_carretera_km }} km · Agua: {{ infra.distancia_recurso_hidrico_km }} km</p>
              <p>Actualizado: {{ infra.fecha_actualizacion }}</p>
            </ng-container>
            <ng-template #noInfra>Sin datos de infraestructura.</ng-template>
          </section>
          <section class="card p-4">
            <h2 class="text-xl font-bold">Urgencias más cercanas</h2>
            <ng-container *ngIf="m.urgencias_mas_cercana as urg; else noUrg">
              <p>{{ urg.nombre }} · {{ urg.tipo }} · {{ urg.tiene_urgencias ? 'Con urgencias' : 'Sin urgencias' }}</p>
              <p>{{ urg.direccion || 'Dirección no disponible' }} · {{ urg.horario || 'Horario no disponible' }} · {{ urg.telefono || 'Teléfono no disponible' }}</p>
              <p>Distancia por carretera: {{ urg.distancia_carretera_km ?? 'No disponible' }} km · Tiempo: {{ urg.tiempo_estimado_min ?? 'No disponible' }} min</p>
              <p>Fuente: {{ urg.fuente_ruta || 'No disponible' }}</p>
              <app-ruta-sanitaria [ruta]="urg" />
            </ng-container>
            <ng-template #noUrg>Sin centro sanitario disponible.</ng-template>
          </section>
          <section class="card p-4">
            <h2 class="text-xl font-bold">Ayudas disponibles ({{ m.convocatorias.length }})</h2>
            <ul><li *ngFor="let conv of m.convocatorias">{{ conv.descripcion }} <a *ngIf="conv.url_bases" [href]="conv.url_bases" target="_blank" rel="noopener noreferrer" class="underline">Ver bases</a></li></ul>
            <a class="text-primary underline" routerLink="/convocatorias" [queryParams]="{ municipio: m.codigo_ine }">Ver convocatorias</a>
          </section>
        </div>
        <section class="card p-4 mt-4">
          <h2 class="text-xl font-bold">Demografía</h2>
          <p>Inercia: {{ m.inercia_demografica }} · Preserva masa crítica: {{ m.preserva_masa_critica ? 'Sí' : 'No' }}</p>
          <p *ngIf="demografiaError" class="text-error-700" role="alert">{{ demografiaError }}</p>
          <ng-container *ngIf="demografia as d">
            <p>Población inicial: {{ d.poblacion_inicial_10a ?? 'Sin datos' }} · Actual: {{ d.poblacion_actual }} · Variación: {{ d.variacion_10a_pct === null ? 'Sin datos' : d.variacion_10a_pct + '%' }}</p>
            <table class="w-full text-left mt-3"><thead><tr><th>Año</th><th>Población</th><th>Mayores de 65</th><th>Menores de 15</th><th>Envejecimiento</th></tr></thead>
              <tbody><tr *ngFor="let p of d.serie_anual"><td>{{ p.anio }}</td><td>{{ p.poblacion }}</td><td>{{ p.poblacion_mayor_65 ?? '—' }}</td><td>{{ p.poblacion_menor_15 ?? '—' }}</td><td>{{ p.tasa_envejecimiento ?? '—' }}</td></tr></tbody>
            </table>
            <p *ngIf="!d.serie_anual.length">Sin serie histórica disponible.</p>
          </ng-container>
        </section>
      </ng-container>
    </div>
  `
})
export class MunicipioDetailComponent implements OnInit {
  municipio: MunicipioDetail | null = null;
  demografia: Demografia | null = null;
  loading = true;
  error: string | null = null;
  demografiaError: string | null = null;
  private readonly destroyRef = inject(DestroyRef);

  constructor(private route: ActivatedRoute, private municipioService: MunicipioService) {}

  ngOnInit(): void {
    this.route.paramMap.pipe(
      switchMap(params => {
        this.loading = true;
        this.error = null;
        this.municipio = null;
        this.demografia = null;
        this.demografiaError = null;
        return this.municipioService.getMunicipioDetail(params.get('codigo_ine')!).pipe(
          catchError(err => {
            console.error('Error al cargar municipio:', err);
            this.error = 'No se pudo cargar el municipio.';
            this.loading = false;
            return EMPTY;
          })
        );
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: m => { this.municipio = m; this.loading = false; this.loadDemografia(m.codigo_ine); }
    });
  }

  refresh(): void {
    if (!this.municipio) return;
    const codigo = this.municipio.codigo_ine;
    this.loading = true;
    this.error = null;
    this.municipioService.triggerMunicipioIngestion(codigo).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: m => {
        if (this.route.snapshot.paramMap.get('codigo_ine') !== codigo) return;
        this.municipio = m; this.loading = false; this.loadDemografia(m.codigo_ine);
      },
      error: err => {
        console.error('Error al actualizar municipio:', err);
        if (this.route.snapshot.paramMap.get('codigo_ine') === codigo) {
          this.error = 'No se pudieron actualizar los datos.'; this.loading = false;
        }
      }
    });
  }

  private loadDemografia(codigo: string): void {
    this.demografia = null;
    this.demografiaError = null;
    this.municipioService.getDemografia(codigo).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: data => { if (this.municipio?.codigo_ine === codigo) this.demografia = data; },
      error: err => {
        console.error('Error al cargar demografía:', err);
        if (this.municipio?.codigo_ine === codigo) this.demografiaError = 'No se pudo cargar la serie demográfica.';
      }
    });
  }
}
