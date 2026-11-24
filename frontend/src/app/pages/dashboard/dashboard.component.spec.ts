import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { DashboardComponent } from './dashboard.component';
import { MunicipioService } from '../../core/services/municipio.service';
import { Municipio } from '../../core/models/municipio.model';

describe('DashboardComponent', () => {
  it('cuenta los estados devueltos por la API, incluidos pendientes sin WLC', () => {
    const municipios = [
      { wlc: { semaforo: 'ROJO', indice_wlc: 35 } },
      { wlc: { semaforo: 'AMBAR', indice_wlc: 60 } },
      { wlc: { semaforo: 'VERDE', indice_wlc: 80 } },
      { wlc: null }
    ] as Municipio[];
    TestBed.configureTestingModule({ providers: [
      { provide: MunicipioService, useValue: { getMunicipios: () => of(municipios), healthCheck: () => of({ status: 'ok' }) } }
    ] });
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.componentInstance.ngOnInit();
    expect(fixture.componentInstance.kpiData).toEqual({ total_analizados: 4, riesgo_alto: 1, riesgo_medio: 1, favorable: 1, pendientes: 1 });
    fixture.destroy();
  });
});
