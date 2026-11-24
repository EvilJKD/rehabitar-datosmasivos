import { AfterViewInit, Component, ElementRef, Input, OnChanges, OnDestroy, ViewChild } from '@angular/core';
import * as L from 'leaflet';
import { RutaSanitaria } from '../../../core/models/municipio.model';

@Component({
  selector: 'app-ruta-sanitaria',
  standalone: true,
  template: '<div #map class="w-full h-64 rounded-lg mt-3" aria-label="Ruta hasta el centro sanitario"></div>'
})
export class RutaSanitariaComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input({ required: true }) ruta!: RutaSanitaria;
  @ViewChild('map') mapElement!: ElementRef<HTMLElement>;
  private map?: L.Map;

  ngAfterViewInit(): void { this.render(); }
  ngOnChanges(): void { if (this.map) this.render(); }
  ngOnDestroy(): void { this.map?.remove(); }

  private render(): void {
    this.map?.remove();
    const points: L.LatLngTuple[] = this.ruta.geometria_ruta
      .filter(p => p.length >= 2 && Number.isFinite(p[0]) && Number.isFinite(p[1]))
      .map(p => [p[0], p[1]]);
    this.map = L.map(this.mapElement.nativeElement).setView([this.ruta.latitud, this.ruta.longitud], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors', maxZoom: 19
    }).addTo(this.map);
    L.circleMarker([this.ruta.latitud, this.ruta.longitud], { color: '#005eb8' }).addTo(this.map);
    if (points.length > 1) {
      const line = L.polyline(points, { color: '#005eb8' }).addTo(this.map);
      this.map.fitBounds(line.getBounds(), { padding: [20, 20], maxZoom: 14 });
    }
  }

}
