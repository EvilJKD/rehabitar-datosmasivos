import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { MunicipioService } from './municipio.service';
import { mockApiInterceptor } from '../mocks/mock-api';

describe('MunicipioService', () => {
  let service: MunicipioService;
  let http: HttpTestingController;

  beforeEach(() => {
    sessionStorage.removeItem('rehabitar-mock');
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(MunicipioService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('envía filtros con valores cero y false sin descartarlos', () => {
    service.getMunicipios({ min_wlc: 0, w_carretera: 0, requiere_fibra: false, con_ayuda_abierta: false }).subscribe();
    const req = http.expectOne(r => r.url === '/api/municipios');
    expect(req.request.params.get('min_wlc')).toBe('0');
    expect(req.request.params.get('w_carretera')).toBe('0');
    expect(req.request.params.get('requiere_fibra')).toBe('false');
    expect(req.request.params.get('con_ayuda_abierta')).toBe('false');
    req.flush([]);
  });

  it('utiliza los parámetros del backend para convocatorias y centros', () => {
    service.getConvocatorias({ codigo_ine: '28027', categoria: 'Vivienda', solo_abiertas: false }).subscribe();
    const grants = http.expectOne(r => r.url === '/api/convocatorias');
    expect(grants.request.params.get('codigo_ine')).toBe('28027');
    expect(grants.request.params.get('solo_abiertas')).toBe('false');
    grants.flush([]);
    service.getCentrosSanitarios({ solo_urgencias: true, municipio_nombre: 'Buitrago' }).subscribe();
    const centers = http.expectOne(r => r.url === '/api/centros-sanitarios');
    expect(centers.request.params.get('solo_urgencias')).toBe('true');
    expect(centers.request.params.get('municipio_nombre')).toBe('Buitrago');
    centers.flush([]);
  });

  it('consulta la ficha, demografía e ingesta con sus métodos correspondientes', () => {
    service.getMunicipioDetail('28027', true, { w_demografia: 0 }).subscribe();
    const detail = http.expectOne(r => r.url === '/api/municipios/28027');
    expect(detail.request.params.get('force_refresh')).toBe('true');
    expect(detail.request.params.get('w_demografia')).toBe('0');
    detail.flush({});
    service.getDemografia('28027').subscribe();
    http.expectOne('/api/municipios/28027/demografia').flush({});
    service.triggerMunicipioIngestion('28027').subscribe();
    const ingest = http.expectOne('/api/municipios/28027/ingest');
    expect(ingest.request.method).toBe('POST');
    ingest.flush({});
    service.healthCheck().subscribe();
    http.expectOne('/api/health').flush({});
  });
});

describe('API mock', () => {
  beforeEach(() => {
    sessionStorage.setItem('rehabitar-mock', '1');
    TestBed.configureTestingModule({ providers: [provideHttpClient(withInterceptors([mockApiInterceptor])), provideHttpClientTesting()] });
  });
  afterEach(() => sessionStorage.removeItem('rehabitar-mock'));

  it('incluye municipios pendientes y filtra convocatorias abiertas o todas', () => {
    const service = TestBed.inject(MunicipioService);
    service.getMunicipios().subscribe(items => expect(items.some(m => m.wlc === null)).toBe(true));
    service.getConvocatorias({ codigo_ine: '28027' }).subscribe(items => {
      expect(items.length).toBe(1);
      expect(items[0].regla_asignacion).toBe('region_completa');
    });
    service.getConvocatorias({ solo_abiertas: false }).subscribe(items => expect(items.length).toBe(2));
  });

  it('devuelve 404 para municipios desconocidos', () => {
    const service = TestBed.inject(MunicipioService);
    service.getMunicipioDetail('desconocido').subscribe({
      next: () => { throw new Error('Se esperaba un error'); },
      error: err => expect(err.status).toBe(404)
    });
  });
});
