import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { Convocatoria, Municipio } from '../../core/models/municipio.model';
import { ConvocatoriasComponent } from './convocatorias.component';

describe('ConvocatoriasComponent', () => {
  const municipio: Municipio = {
    codigo_ine: '28027',
    nombre: 'Buitrago',
    provincia: 'Madrid',
    comarca: 'Sierra Norte',
    latitud: 0,
    longitud: 0,
    hidratado: true,
    poblacion_actual: 100,
    variacion_10a_pct: null,
    cobertura_fibra_pct: null,
    num_ayudas_abiertas: 1,
    wlc: null,
  };
  const convocatoria: Convocatoria = {
    codigo_bdns: '123',
    descripcion: 'Ayuda para vivienda',
    organo_nivel1: '',
    organo_nivel2: null,
    organo_nivel3: null,
    organo_convocante: 'Comunidad de Madrid',
    fecha_recepcion: '2025-01-01',
    inicio_solicitud: null,
    fin_solicitud: null,
    abierta: true,
    presupuesto_total: 1000,
    tipo_beneficiario: 'Personas',
    finalidad: null,
    poblacion_max_objetivo: null,
    url_bases: 'https://example.com/bases',
    regla_asignacion: 'region_completa',
  };
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: { queryParamMap: of(convertToParamMap({ municipio: '28027' })) },
        },
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    vi.restoreAllMocks();
  });

  it('updates the loader, filters and cards when asynchronous responses arrive', async () => {
    const fixture = TestBed.createComponent(ConvocatoriasComponent);
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;
    expect(page.querySelector('[role="status"]')?.textContent).toContain('Cargando convocatorias');

    http.expectOne((req) => req.url === '/api/municipios').flush([municipio]);
    const initialRequest = http.expectOne((req) => req.url === '/api/convocatorias');
    expect(initialRequest.request.params.get('codigo_ine')).toBe('28027');
    expect(initialRequest.request.params.get('solo_abiertas')).toBe('true');
    initialRequest.flush([convocatoria]);
    await fixture.whenStable();

    expect(page.querySelector('[role="status"]')).toBeNull();
    expect(page.querySelector('select')?.value).toBe('28027');
    expect(page.querySelector('article')?.textContent).toContain('Ayuda para vivienda');
    expect(page.querySelector('article')?.textContent).toContain('Abierta');
    expect(page.querySelector('article')?.textContent).toContain('Sin fecha de cierre publicada');
    expect(page.querySelector('article a')?.getAttribute('href')).toBe(convocatoria.url_bases);

    const checkbox = page.querySelector<HTMLInputElement>('input[type="checkbox"]');
    expect(checkbox).not.toBeNull();
    checkbox!.click();
    await fixture.whenStable();
    expect(page.querySelector('[role="status"]')).not.toBeNull();
    const filteredRequest = http.expectOne((req) => req.url === '/api/convocatorias');
    expect(filteredRequest.request.params.get('solo_abiertas')).toBe('false');
    filteredRequest.flush([{ ...convocatoria, abierta: false }]);
    await fixture.whenStable();
    expect(page.querySelector('[role="status"]')).toBeNull();
    expect(page.querySelector('article')?.textContent).toContain('Cerrada');
  });

  it('renders request errors and clears the loader', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const fixture = TestBed.createComponent(ConvocatoriasComponent);
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;

    http
      .expectOne((req) => req.url === '/api/municipios')
      .flush('error', { status: 500, statusText: 'Server Error' });
    http
      .expectOne((req) => req.url === '/api/convocatorias')
      .flush('error', { status: 500, statusText: 'Server Error' });
    await fixture.whenStable();

    expect(page.querySelector('[role="status"]')).toBeNull();
    expect(page.textContent).toContain('No se pudo cargar el selector de municipios.');
    expect(page.textContent).toContain('No se pudieron cargar las convocatorias.');
  });
});
