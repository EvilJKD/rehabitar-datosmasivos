import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { AnaliticaComponent } from './analitica.component';
import { MunicipioService } from '../../core/services/municipio.service';
import { Demografia, Municipio } from '../../core/models/municipio.model';

describe('AnaliticaComponent', () => {
  const municipios: Municipio[] = [
    {
      codigo_ine: '28078',
      nombre: 'Madarcos',
      provincia: 'Madrid',
      comarca: 'Sierra Norte',
      latitud: 41.0487,
      longitud: -3.5828,
      hidratado: true,
      poblacion_actual: 69,
      variacion_10a_pct: 35.29,
      cobertura_fibra_pct: 100,
      num_ayudas_abiertas: 2,
      wlc: null,
    },
    {
      codigo_ine: '28027',
      nombre: 'Buitrago del Lozoya',
      provincia: 'Madrid',
      comarca: 'Sierra Norte',
      latitud: 40.9931,
      longitud: -3.6384,
      hidratado: true,
      poblacion_actual: 1990,
      variacion_10a_pct: 4.5,
      cobertura_fibra_pct: 95,
      num_ayudas_abiertas: 3,
      wlc: null,
    },
  ];

  const demoByCode: Record<string, Demografia> = {
    '28078': {
      codigo_ine: '28078',
      nombre: 'Madarcos',
      poblacion_inicial_10a: 51,
      poblacion_actual: 69,
      variacion_10a_pct: 35.29,
      cobertura_fibra_pct: 100,
      distancia_urgencias_km: 7.7,
      num_ayudas_abiertas: 2,
      serie_anual: [
        { anio: 2015, poblacion: 51, poblacion_mayor_65: null, poblacion_menor_15: null, tasa_envejecimiento: null },
        { anio: 2025, poblacion: 69, poblacion_mayor_65: null, poblacion_menor_15: null, tasa_envejecimiento: null },
      ],
    },
    '28027': {
      codigo_ine: '28027',
      nombre: 'Buitrago del Lozoya',
      poblacion_inicial_10a: 1904,
      poblacion_actual: 1990,
      variacion_10a_pct: 4.5,
      cobertura_fibra_pct: 95,
      distancia_urgencias_km: 0.2,
      num_ayudas_abiertas: 3,
      serie_anual: [
        { anio: 2015, poblacion: 1904, poblacion_mayor_65: null, poblacion_menor_15: null, tasa_envejecimiento: null },
        { anio: 2025, poblacion: 1990, poblacion_mayor_65: null, poblacion_menor_15: null, tasa_envejecimiento: null },
      ],
    },
  };

  it('preselecciona municipios hidratados, carga sus series y permite alternar seleccion', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        {
          provide: MunicipioService,
          useValue: {
            getMunicipios: () => of(municipios),
            getDemografia: (code: string) => of(demoByCode[code]),
          },
        },
      ],
    });

    const fixture = TestBed.createComponent(AnaliticaComponent);
    fixture.detectChanges();
    await fixture.whenStable();

    const comp = fixture.componentInstance;
    expect(comp.selectedCodes).toEqual(['28027', '28078']);
    expect(comp.series.length).toBe(2);
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Madarcos');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Buitrago del Lozoya');

    comp.toggleMunicipio('28027');
    fixture.detectChanges();
    expect(comp.selectedCodes).toEqual(['28078']);
    expect(comp.series.length).toBe(1);
    fixture.destroy();
  });
});
