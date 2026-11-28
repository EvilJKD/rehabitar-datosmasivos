import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { Demografia, MunicipioDetail } from '../../core/models/municipio.model';
import { MunicipioDetailComponent } from './municipio-detail.component';

describe('MunicipioDetailComponent', () => {
  const municipio: MunicipioDetail = {
    codigo_ine: '28027',
    nombre: 'Buitrago',
    provincia: 'Madrid',
    comarca: 'Sierra Norte',
    latitud: 0,
    longitud: 0,
    hidratado: true,
    origen_datos: 'INE',
    poblacion_inicial_10a: null,
    poblacion_actual: 100,
    variacion_10a_pct: null,
    preserva_masa_critica: true,
    inercia_demografica: 'estable',
    infraestructura: null,
    wlc: null,
    urgencias_mas_cercana: null,
    convocatorias: [],
  };
  const demografia: Demografia = {
    codigo_ine: '28027',
    nombre: 'Buitrago',
    poblacion_inicial_10a: null,
    poblacion_actual: 100,
    variacion_10a_pct: null,
    cobertura_fibra_pct: null,
    distancia_urgencias_km: null,
    num_ayudas_abiertas: null,
    serie_anual: [],
  };

  const params = convertToParamMap({ codigo_ine: '28027' });
  let paramMap: BehaviorSubject<typeof params>;
  let http: HttpTestingController;

  beforeEach(() => {
    paramMap = new BehaviorSubject(params);
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { paramMap, snapshot: { paramMap: params } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('renders the detail and demographics as their responses arrive', async () => {
    const fixture = TestBed.createComponent(MunicipioDetailComponent);
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;
    expect(page.textContent).toContain('Obteniendo datos oficiales');
    expect(page.querySelector('[role="status"]')?.textContent).toContain(
      'Obteniendo datos oficiales',
    );

    http.expectOne((req) => req.url === '/api/municipios/28027').flush(municipio);
    await fixture.whenStable();
    expect(page.textContent).not.toContain('Obteniendo datos oficiales');
    expect(page.querySelector('[role="status"]')).toBeNull();
    expect(page.querySelector('h1')?.textContent).toContain('Buitrago');

    http.expectOne('/api/municipios/28027/demografia').flush(demografia);
    await fixture.whenStable();
    expect(page.textContent).toContain('Actual: 100');
  });

  it('muestra la etiqueta legible del estado de viabilidad', async () => {
    const fixture = TestBed.createComponent(MunicipioDetailComponent);
    await fixture.whenStable();
    http.expectOne((req) => req.url === '/api/municipios/28027').flush({
      ...municipio,
      wlc: {
        semaforo: 'ROJO',
        indice_wlc: 20,
        etiqueta_viabilidad: 'Vulnerabilidad crítica',
        score_acceso_carretera: 20,
        score_proximidad_sanitaria: 20,
        score_conectividad_digital: 20,
        score_acceso_hidrico: 20,
        score_inercia_demografica: 20,
        pesos_aplicados: {},
      },
    });
    http.expectOne('/api/municipios/28027/demografia').flush(demografia);
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;
    expect(page.textContent).toContain('Peligro');
    expect(page.textContent).not.toContain('ROJO');
  });

  it('renders detail errors and resets the view when the route changes', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const fixture = TestBed.createComponent(MunicipioDetailComponent);
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;
    http.expectOne((req) => req.url === '/api/municipios/28027').flush('error', {
      status: 500,
      statusText: 'Server Error',
    });
    await fixture.whenStable();
    expect(page.textContent).not.toContain('Obteniendo datos oficiales');
    expect(page.textContent).toContain('No se pudo cargar el municipio.');

    paramMap.next(convertToParamMap({ codigo_ine: '28028' }));
    await fixture.whenStable();
    expect(page.textContent).toContain('Obteniendo datos oficiales');
    expect(page.textContent).not.toContain('No se pudo cargar el municipio.');
    http.expectOne((req) => req.url === '/api/municipios/28028').flush('error', {
      status: 500,
      statusText: 'Server Error',
    });
    await fixture.whenStable();
    expect(page.textContent).toContain('No se pudo cargar el municipio.');
    vi.restoreAllMocks();
  });

  it('renders refresh and demographics errors without leaving loading visible', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const fixture = TestBed.createComponent(MunicipioDetailComponent);
    await fixture.whenStable();
    const page = fixture.nativeElement as HTMLElement;
    http.expectOne((req) => req.url === '/api/municipios/28027').flush(municipio);
    http.expectOne('/api/municipios/28027/demografia').flush(demografia);
    await fixture.whenStable();

    fixture.componentInstance.refresh();
    await fixture.whenStable();
    expect(page.textContent).toContain('Obteniendo datos oficiales');
    http.expectOne('/api/municipios/28027/ingest').flush(municipio);
    http.expectOne('/api/municipios/28027/demografia').flush('error', {
      status: 500,
      statusText: 'Server Error',
    });
    await fixture.whenStable();
    expect(page.textContent).not.toContain('Obteniendo datos oficiales');
    expect(page.textContent).toContain('No se pudo cargar la serie demográfica.');

    fixture.componentInstance.refresh();
    http.expectOne('/api/municipios/28027/ingest').flush('error', {
      status: 500,
      statusText: 'Server Error',
    });
    await fixture.whenStable();
    expect(page.textContent).not.toContain('Obteniendo datos oficiales');
    expect(page.textContent).toContain('No se pudieron actualizar los datos.');
    vi.restoreAllMocks();
  });
});
