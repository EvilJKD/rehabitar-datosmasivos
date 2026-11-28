import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Municipio, Semaforo, WLCBreakdown } from '../../../core/models/municipio.model';
import { RangoMunicipalComponent } from './rango-municipal.component';

describe('RangoMunicipalComponent', () => {
  it('muestra etiquetas de estado y conserva los códigos al filtrar', async () => {
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    const municipio = (nombre: string, semaforo: Semaforo | null): Municipio => {
      const wlc: WLCBreakdown | null = semaforo === null ? null : {
        semaforo,
        indice_wlc: 50,
        etiqueta_viabilidad: '',
        score_acceso_carretera: 0,
        score_proximidad_sanitaria: 0,
        score_conectividad_digital: 0,
        score_acceso_hidrico: 0,
        score_inercia_demografica: 0,
        pesos_aplicados: {},
      };
      return {
        codigo_ine: nombre,
        nombre,
        provincia: 'Madrid',
        comarca: 'Sierra Norte',
        latitud: 0,
        longitud: 0,
        hidratado: true,
        poblacion_actual: null,
        variacion_10a_pct: null,
        cobertura_fibra_pct: null,
        num_ayudas_abiertas: 0,
        wlc,
      };
    };

    const fixture = TestBed.createComponent(RangoMunicipalComponent);
    fixture.componentRef.setInput('municipios', [
      municipio('A', 'VERDE'),
      municipio('B', 'AMBAR'),
      municipio('C', 'ROJO'),
      municipio('D', 'PENDIENTE'),
      municipio('E', null),
    ]);
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;
    const states = () => Array.from(page.querySelectorAll('tbody tr')).map(
      (row) => row.querySelectorAll('td')[1].textContent?.trim(),
    );
    expect(states()).toEqual(['Seguro', 'Precaución', 'Peligro', 'Pendiente', 'Pendiente']);

    const select = page.querySelector('select')!;
    expect(Array.from(select.options).map((option) => option.textContent?.trim())).toEqual([
      'Todos', 'Seguro', 'Precaución', 'Peligro', 'Pendiente',
    ]);
    select.value = 'AMBAR';
    select.dispatchEvent(new Event('change'));
    await fixture.whenStable();
    expect(states()).toEqual(['Precaución']);
    expect(page.querySelector('tbody')?.textContent).toContain('B');

    select.value = 'PENDIENTE';
    select.dispatchEvent(new Event('change'));
    await fixture.whenStable();
    expect(states()).toEqual(['Pendiente', 'Pendiente']);
  });
});
