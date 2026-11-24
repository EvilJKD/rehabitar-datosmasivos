import { HttpErrorResponse, HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { of, throwError } from 'rxjs';
import { CentroSanitario, Convocatoria, Demografia, Municipio, MunicipioDetail, WLCBreakdown } from '../models/municipio.model';

const wlc: WLCBreakdown = {
  indice_wlc: 78, semaforo: 'VERDE', etiqueta_viabilidad: 'Viabilidad favorable',
  score_acceso_carretera: 80, score_proximidad_sanitaria: 70,
  score_conectividad_digital: 90, score_acceso_hidrico: 75,
  score_inercia_demografica: 72,
  pesos_aplicados: { carretera: 0.25, sanidad: 0.2, conectividad: 0.2, hidrico: 0.15, demografia: 0.2 }
};

const municipios: Municipio[] = [
  { codigo_ine: '28027', nombre: 'Buitrago del Lozoya', provincia: 'Madrid', comarca: 'Sierra Norte', latitud: 40.9909, longitud: -3.6336, hidratado: true, poblacion_actual: 2000, variacion_10a_pct: 4.2, cobertura_fibra_pct: 85, num_ayudas_abiertas: 1, wlc },
  { codigo_ine: '28080', nombre: 'Madarcos', provincia: 'Madrid', comarca: 'Sierra Norte', latitud: 41.046, longitud: -3.579, hidratado: false, poblacion_actual: null, variacion_10a_pct: null, cobertura_fibra_pct: null, num_ayudas_abiertas: 0, wlc: null }
];

const centro: CentroSanitario = {
  id_centro: 'CS-28027', nombre: 'Centro de salud de ejemplo', tipo: 'Centro de Salud',
  tiene_urgencias: true, municipio_nombre: 'Buitrago del Lozoya', direccion: 'Dirección de ejemplo',
  horario: '24 horas', telefono: '900 000 000', latitud: 40.991, longitud: -3.63,
  distancia_euclidea_km: null
};

const convocatorias: Convocatoria[] = [
  { codigo_bdns: 'MOCK-1', descripcion: 'Ayuda de ejemplo para vivienda', finalidad: 'Vivienda', organo_nivel1: 'AUTONOMICA', organo_nivel2: null, organo_nivel3: null, organo_convocante: 'Comunidad de Madrid (ejemplo)', fecha_recepcion: '2025-01-01', inicio_solicitud: '2025-01-01', fin_solicitud: null, abierta: true, presupuesto_total: 50000, tipo_beneficiario: 'Municipios', poblacion_max_objetivo: null, url_bases: null, regla_asignacion: null },
  { codigo_bdns: 'MOCK-2', descripcion: 'Ayuda de ejemplo cerrada', finalidad: 'Infraestructuras', organo_nivel1: 'AUTONOMICA', organo_nivel2: null, organo_nivel3: null, organo_convocante: 'Comunidad de Madrid (ejemplo)', fecha_recepcion: '2024-01-01', inicio_solicitud: '2024-01-01', fin_solicitud: '2024-12-31', abierta: false, presupuesto_total: 10000, tipo_beneficiario: null, poblacion_max_objetivo: null, url_bases: null, regla_asignacion: null }
];

const mode = new URLSearchParams(window.location.search).get('mock');
if (mode === '1' || mode === '0') sessionStorage.setItem('rehabitar-mock', mode);

function detail(municipio: Municipio, refreshed: boolean): MunicipioDetail {
  return {
    codigo_ine: municipio.codigo_ine, nombre: municipio.nombre, provincia: municipio.provincia,
    comarca: municipio.comarca, latitud: municipio.latitud, longitud: municipio.longitud,
    hidratado: true, origen_datos: refreshed ? 'INGESTA_EN_VIVO_GUARDADA_EN_BD' : 'CACHE_POSTGRESQL',
    poblacion_inicial_10a: 1900, poblacion_actual: 2000, variacion_10a_pct: 5.3,
    preserva_masa_critica: true, inercia_demografica: 'ESTABLE',
    infraestructura: { distancia_carretera_km: 2, distancia_recurso_hidrico_km: 3, cobertura_fibra_pct: 85, cobertura_movil_pct: 95, fecha_actualizacion: '2025-01-01' },
    wlc, urgencias_mas_cercana: { ...centro, distancia_euclidea_km: 2, distancia_carretera_km: 3, tiempo_estimado_min: 5, fuente_ruta: 'Ejemplo', geometria_ruta: [[municipio.latitud, municipio.longitud], [centro.latitud, centro.longitud]] },
    convocatorias: [{ ...convocatorias[0], regla_asignacion: 'region_completa' }]
  };
}

export const mockApiInterceptor: HttpInterceptorFn = (req, next) => {
  if (sessionStorage.getItem('rehabitar-mock') !== '1' || !req.url.startsWith('/api/')) return next(req);
  console.log('[MOCK]', req.method, req.url);

  const path = req.url.slice('/api/'.length);
  let body: unknown;
  if (req.method === 'GET' && path === 'health') {
    body = { status: 'ok', database: 'mock', total_municipios: 2, municipios_hidratados: 1 };
  } else if (req.method === 'GET' && path === 'municipios') {
    body = municipios.filter(m =>
      (!req.params.has('semaforo') || (m.wlc?.semaforo ?? 'PENDIENTE') === req.params.get('semaforo')) &&
      (!req.params.has('min_wlc') || (m.wlc !== null && m.wlc.indice_wlc >= Number(req.params.get('min_wlc')))) &&
      (req.params.get('requiere_fibra') !== 'true' || (m.cobertura_fibra_pct !== null && m.cobertura_fibra_pct >= Number(req.params.get('min_fibra_pct') ?? 50))) &&
      (!req.params.has('con_ayuda_abierta') || (m.num_ayudas_abiertas > 0) === (req.params.get('con_ayuda_abierta') === 'true')));
  } else if (req.method === 'GET' && path === 'convocatorias') {
    body = convocatorias.filter(c =>
      ((req.params.get('abierta') ?? req.params.get('solo_abiertas')) === 'false' || c.abierta) &&
      (!req.params.get('categoria') || c.finalidad?.toLowerCase().includes(req.params.get('categoria')!.toLowerCase())))
      .map(c => ({ ...c, regla_asignacion: req.params.has('codigo_ine') ? 'region_completa' : null }));
  } else if (req.method === 'GET' && path === 'centros-sanitarios') {
    body = [centro].filter(c => (!req.params.get('municipio_nombre') || c.municipio_nombre === req.params.get('municipio_nombre')) && (req.params.get('solo_urgencias') !== 'true' || c.tiene_urgencias));
  } else {
    const match = /^municipios\/([^/]+)(?:\/(ingest|demografia))?$/.exec(path);
    const municipio = match && municipios.find(m => m.codigo_ine === decodeURIComponent(match[1]));
    if (!match || !municipio || (match[2] === 'ingest' ? req.method !== 'POST' : req.method !== 'GET')) {
      return throwError(() => new HttpErrorResponse({ status: 404, statusText: 'Mock no encontrado', url: req.url }));
    }
    if (match[2] === 'demografia') {
      const demografia: Demografia = { codigo_ine: municipio.codigo_ine, nombre: municipio.nombre, poblacion_inicial_10a: 1900, poblacion_actual: 2000, variacion_10a_pct: 5.3, cobertura_fibra_pct: 85, distancia_urgencias_km: 3, num_ayudas_abiertas: 1, serie_anual: [2015, 2020, 2025].map((anio, i) => ({ anio, poblacion: 1900 + i * 50, poblacion_mayor_65: null, poblacion_menor_15: null, tasa_envejecimiento: null })) };
      body = demografia;
    } else {
      body = detail(municipio, match[2] === 'ingest' || req.params.get('force_refresh') === 'true');
    }
  }
  return of(new HttpResponse({ status: 200, body }));
};
