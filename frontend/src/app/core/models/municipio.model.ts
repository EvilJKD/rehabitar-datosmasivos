export type Semaforo = 'VERDE' | 'AMBAR' | 'ROJO' | 'PENDIENTE';

export interface WLCBreakdown {
  indice_wlc: number;
  semaforo: Semaforo;
  etiqueta_viabilidad: string;
  score_acceso_carretera: number;
  score_proximidad_sanitaria: number;
  score_conectividad_digital: number;
  score_acceso_hidrico: number;
  score_inercia_demografica: number;
  pesos_aplicados: Record<string, number>;
}

export interface Municipio {
  codigo_ine: string;
  nombre: string;
  provincia: string;
  comarca: string;
  latitud: number;
  longitud: number;
  hidratado: boolean;
  poblacion_actual: number | null;
  variacion_10a_pct: number | null;
  cobertura_fibra_pct: number | null;
  num_ayudas_abiertas: number;
  wlc: WLCBreakdown | null;
}

export interface Infraestructura {
  distancia_carretera_km: number;
  distancia_recurso_hidrico_km: number;
  cobertura_fibra_pct: number;
  cobertura_movil_pct: number;
  fecha_actualizacion: string;
}

export interface CentroSanitario {
  id_centro: string;
  nombre: string;
  tipo: string;
  tiene_urgencias: boolean;
  municipio_nombre: string | null;
  direccion: string | null;
  horario: string | null;
  telefono: string | null;
  latitud: number;
  longitud: number;
  distancia_euclidea_km: number | null;
}

export interface RutaSanitaria extends CentroSanitario {
  distancia_euclidea_km: number;
  distancia_carretera_km: number | null;
  tiempo_estimado_min: number | null;
  fuente_ruta: string | null;
  geometria_ruta: number[][];
}

export interface MunicipioDetail {
  codigo_ine: string;
  nombre: string;
  provincia: string;
  comarca: string;
  latitud: number;
  longitud: number;
  hidratado: boolean;
  origen_datos: string;
  poblacion_inicial_10a: number | null;
  poblacion_actual: number | null;
  variacion_10a_pct: number | null;
  preserva_masa_critica: boolean;
  inercia_demografica: string;
  infraestructura: Infraestructura | null;
  wlc: WLCBreakdown | null;
  urgencias_mas_cercana: RutaSanitaria | null;
  convocatorias: Convocatoria[];
}

export interface Convocatoria {
  codigo_bdns: string;
  descripcion: string;
  organo_nivel1: string;
  organo_nivel2: string | null;
  organo_nivel3: string | null;
  organo_convocante: string;
  fecha_recepcion: string;
  inicio_solicitud: string | null;
  fin_solicitud: string | null;
  abierta: boolean;
  presupuesto_total: number;
  tipo_beneficiario: string | null;
  finalidad: string | null;
  poblacion_max_objetivo: number | null;
  url_bases: string | null;
  regla_asignacion: string | null;
}

export interface DemografiaPunto {
  anio: number;
  poblacion: number;
  poblacion_mayor_65: number | null;
  poblacion_menor_15: number | null;
  tasa_envejecimiento: number | null;
}

export interface Demografia {
  codigo_ine: string;
  nombre: string;
  poblacion_inicial_10a: number | null;
  poblacion_actual: number;
  variacion_10a_pct: number | null;
  cobertura_fibra_pct: number | null;
  distancia_urgencias_km: number | null;
  num_ayudas_abiertas: number | null;
  serie_anual: DemografiaPunto[];
}

export interface Health {
  status: string;
  database: string;
  total_municipios: number;
  municipios_hidratados: number;
}

export interface KPISummary {
  total_analizados: number;
  riesgo_alto: number;
  riesgo_medio: number;
  favorable: number;
  pendientes: number;
}
