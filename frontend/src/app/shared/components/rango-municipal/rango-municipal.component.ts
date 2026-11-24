import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Municipio } from '../../../core/models/municipio.model';

@Component({
  selector: 'app-rango-municipal',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="p-space-lg">
      <input type="search" placeholder="Buscar municipio..." aria-label="Buscar municipio"
        class="w-full border rounded-lg p-2 mb-4" (input)="onSearch($event)">
      <select class="w-full border rounded-lg p-2 mb-4" aria-label="Filtrar por estado" (change)="onStatus($event)">
        <option value="">Todos</option><option value="VERDE">Verde</option>
        <option value="AMBAR">Ámbar</option><option value="ROJO">Rojo</option>
        <option value="PENDIENTE">Pendiente</option>
      </select>
      <table class="w-full text-sm">
        <thead><tr><th class="text-left">Municipio</th><th>Estado</th><th>WLC</th></tr></thead>
        <tbody>
          <tr *ngFor="let municipio of filteredMunicipios" class="border-b">
            <td class="py-2"><a class="text-primary underline" [routerLink]="['/municipio', municipio.codigo_ine]">{{ municipio.nombre }}</a></td>
            <td class="text-center">{{ municipio.wlc?.semaforo ?? 'PENDIENTE' }}</td>
            <td class="text-center">{{ municipio.wlc ? (municipio.wlc.indice_wlc | number:'1.1-1') : '—' }}</td>
          </tr>
        </tbody>
      </table>
      <p class="mt-4 text-sm">Mostrando {{ filteredMunicipios.length }} municipios</p>
    </div>
  `
})
export class RangoMunicipalComponent {
  @Input() municipios: Municipio[] = [];
  searchTerm = '';
  status = '';

  get filteredMunicipios(): Municipio[] {
    return this.municipios
      .filter(m => m.nombre.toLowerCase().includes(this.searchTerm) && (!this.status || (m.wlc?.semaforo ?? 'PENDIENTE') === this.status))
      .slice().sort((a, b) => (b.wlc?.indice_wlc ?? -1) - (a.wlc?.indice_wlc ?? -1));
  }

  onSearch(event: Event): void { this.searchTerm = (event.target as HTMLInputElement).value.toLowerCase(); }
  onStatus(event: Event): void { this.status = (event.target as HTMLSelectElement).value; }
}
