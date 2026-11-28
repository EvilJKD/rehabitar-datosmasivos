import { AfterViewInit, Component, DestroyRef, ElementRef, inject, Input, OnChanges, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import * as L from 'leaflet';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Municipio } from '../../../core/models/municipio.model';
import { MunicipioService } from '../../../core/services/municipio.service';
import { SemaforoLabelPipe } from '../../pipes/semaforo-label.pipe';

@Component({
  selector: 'app-territorio-map',
  standalone: true,
  imports: [CommonModule, SemaforoLabelPipe],
  template: `
    <div class="p-4">
      <label class="block mb-2"><input type="checkbox" (change)="toggleCentros($event)"> Mostrar centros sanitarios</label>
      <p *ngIf="centrosError" class="text-error" role="alert">{{ centrosError }}</p>
      <div #map class="w-full h-[520px] rounded-lg" aria-label="Mapa de municipios"></div>
      <div class="mt-4 border-t border-surface-container pt-3">
        <p class="text-label-md font-semibold text-on-surface">Viabilidad municipal</p>
        <ul
          aria-label="Leyenda del mapa"
          class="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-body-sm text-on-surface-variant"
        >
          <li class="inline-flex items-center gap-2">
            <span aria-hidden="true" class="h-2.5 w-2.5 shrink-0 rounded-full" [style.background-color]="markerColors.VERDE"></span>
            {{ 'VERDE' | semaforoLabel }}
          </li>
          <li class="inline-flex items-center gap-2">
            <span aria-hidden="true" class="h-2.5 w-2.5 shrink-0 rounded-full" [style.background-color]="markerColors.AMBAR"></span>
            {{ 'AMBAR' | semaforoLabel }}
          </li>
          <li class="inline-flex items-center gap-2">
            <span aria-hidden="true" class="h-2.5 w-2.5 shrink-0 rounded-full" [style.background-color]="markerColors.ROJO"></span>
            {{ 'ROJO' | semaforoLabel }}
          </li>
          <li class="inline-flex items-center gap-2">
            <span aria-hidden="true" class="h-2.5 w-2.5 shrink-0 rounded-full" [style.background-color]="markerColors.PENDIENTE"></span>
            {{ 'PENDIENTE' | semaforoLabel }}
          </li>
        </ul>
        <p class="mt-3 text-body-sm text-on-surface-variant">Selecciona un municipio para ver su ficha.</p>
      </div>
    </div>
  `
})
export class TerritorioMapComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() municipios: Municipio[] = [];
  @ViewChild('map') mapElement!: ElementRef<HTMLElement>;
  readonly markerColors = { VERDE: '#25834c', AMBAR: '#d18b16', ROJO: '#c83e3e', PENDIENTE: '#808080' };
  private map?: L.Map;
  private markers?: L.LayerGroup;
  private centros?: L.LayerGroup;
  private centrosSubscription?: import('rxjs').Subscription;
  private readonly destroyRef = inject(DestroyRef);
  centrosError: string | null = null;
  constructor(private router: Router, private service: MunicipioService) {}

  ngAfterViewInit(): void {
    this.map = L.map(this.mapElement.nativeElement).setView([41.0, -3.65], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors', maxZoom: 19
    }).addTo(this.map);
    this.markers = L.layerGroup().addTo(this.map);
    this.centros = L.layerGroup().addTo(this.map);
    this.renderMarkers();
  }

  ngOnChanges(): void { this.renderMarkers(); }
  ngOnDestroy(): void { this.map?.remove(); }

  toggleCentros(event: Event): void {
    this.centrosSubscription?.unsubscribe();
    this.centros?.clearLayers();
    this.centrosError = null;
    if (!(event.target as HTMLInputElement).checked) return;
    this.centrosSubscription = this.service.getCentrosSanitarios().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: centros => {
        for (const centro of centros) {
          const text = document.createElement('div');
          text.textContent = `${centro.nombre} · ${centro.tipo} · ${centro.horario ?? 'Horario no disponible'} · ${centro.telefono ?? 'Teléfono no disponible'}`;
          L.circleMarker([centro.latitud, centro.longitud], { radius: 5, color: centro.tiene_urgencias ? '#005eb8' : '#7395b8', fillOpacity: 0.9 })
            .bindPopup(text).addTo(this.centros!);
        }
      },
      error: err => { console.error('Error al cargar centros sanitarios:', err); this.centrosError = 'No se pudieron cargar los centros sanitarios.'; }
    });
  }

  private renderMarkers(): void {
    if (!this.markers) return;
    this.markers.clearLayers();
    for (const municipio of this.municipios) {
      const state = municipio.wlc?.semaforo ?? 'PENDIENTE';
      const label = document.createElement('span');
      label.textContent = municipio.nombre;
      L.circleMarker([municipio.latitud, municipio.longitud], { radius: 7, color: this.markerColors[state], fillOpacity: 0.8 })
        .bindTooltip(label)
        .on('click', () => this.router.navigate(['/municipio', municipio.codigo_ine]))
        .addTo(this.markers);
    }
  }
}
