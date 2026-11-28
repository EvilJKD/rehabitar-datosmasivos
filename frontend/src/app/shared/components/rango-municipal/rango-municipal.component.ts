import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Municipio, Semaforo } from '../../../core/models/municipio.model';
import { SemaforoLabelPipe } from '../../pipes/semaforo-label.pipe';

@Component({
  selector: 'app-rango-municipal',
  standalone: true,
  imports: [CommonModule, RouterModule, SemaforoLabelPipe],
  template: `
    <div class="p-lg">
      <input
        type="search"
        placeholder="Buscar municipio..."
        aria-label="Buscar municipio"
        class="w-full border rounded-lg p-2 mb-4"
        (input)="onSearch($event)"
      />
      <select
        class="w-full border rounded-lg p-2 mb-4"
        aria-label="Filtrar por estado"
        (change)="onStatus($event)"
      >
        <option value="">Todos</option>
        <option value="VERDE">{{ 'VERDE' | semaforoLabel }}</option>
        <option value="AMBAR">{{ 'AMBAR' | semaforoLabel }}</option>
        <option value="ROJO">{{ 'ROJO' | semaforoLabel }}</option>
        <option value="PENDIENTE">{{ 'PENDIENTE' | semaforoLabel }}</option>
      </select>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr>
              <th scope="col" class="pr-3 text-left">Municipio</th>
              <th scope="col" class="px-3">Estado</th>
              <th scope="col" class="pl-3">WLC</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let municipio of filteredMunicipios" class="border-b">
              <td class="py-2 pr-3">
                <a
                  class="text-primary underline"
                  [routerLink]="['/municipio', municipio.codigo_ine]"
                  >{{ municipio.nombre }}</a
                >
              </td>
              <td class="px-3 text-center">
                <span
                  class="text-[11px]"
                  [ngClass]="statusClasses[municipio.wlc?.semaforo ?? 'PENDIENTE']"
                  >{{ municipio.wlc?.semaforo | semaforoLabel }}</span
                >
              </td>
              <td class="pl-3 text-center">
                {{ municipio.wlc ? (municipio.wlc.indice_wlc | number: '1.1-1') : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="mt-4 text-sm">Mostrando {{ filteredMunicipios.length }} municipios</p>
    </div>
  `,
})
export class RangoMunicipalComponent {
  @Input() municipios: Municipio[] = [];
  readonly statusClasses: Record<Semaforo, string> = {
    VERDE: 'badge-verde',
    AMBAR: 'badge-ambar',
    ROJO: 'badge-rojo',
    PENDIENTE: 'badge-pendiente',
  };
  searchTerm = '';
  status = '';

  get filteredMunicipios(): Municipio[] {
    return this.municipios
      .filter(
        (m) =>
          m.nombre.toLowerCase().includes(this.searchTerm) &&
          (!this.status || (m.wlc?.semaforo ?? 'PENDIENTE') === this.status),
      )
      .slice()
      .sort((a, b) => (b.wlc?.indice_wlc ?? -1) - (a.wlc?.indice_wlc ?? -1));
  }

  onSearch(event: Event): void {
    this.searchTerm = (event.target as HTMLInputElement).value.toLowerCase();
  }
  onStatus(event: Event): void {
    this.status = (event.target as HTMLSelectElement).value;
  }
}
