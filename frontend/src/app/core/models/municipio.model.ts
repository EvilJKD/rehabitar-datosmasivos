export interface Municipio {
  codigo_ine: string;
  nombre: string;
  provincia: string;
  comarca: string;
  latitud: number;
  longitud: number;
  hidratado: boolean;
  poblacion_actual: number;
  variacion_10a_pct: number;
  cobertura_fibra_pct: number;
  num_ayudas_abiertas: number;
  wlc: WLCBreakdown;
}

export interface WLCBreakdown {
  indice_wlc: number;
  semaforo: 'VERDE' | 'AMBAR' | 'ROJO' | 'PENDIENTE';
  etiqueta_viabilidad: string;
  score_acceso_carretera: number;
  score_proximidad_sanitaria: number;
  score_conectividad_digital: number;
  score_acceso_hidrico: number;
  score_inercia_demografica: number;
  pesos_aplicados: Record<string, number>;
}

export interface Convocatoria {
  codigo_bdns: string;
  descripcion: string;
  organo_nivel1: string;
  organo_nivel2?: string;
  organo_nivel3?: string;
  organo_convocante: string;
  fecha_recepcion: string;
  inicio_solicitud?: string;
  fin_solicitud?: string;
  abierta: boolean;
  presupuesto_total: number;
  tipo_beneficiario?: string;
  url_bases?: string;
  regla_asignacion?: 'organo_local' | 'umbral_poblacion' | 'region_completa';
}

export interface DemografiaPunto {
  anio: number;
  poblacion: number;
  poblacion_mayor_65?: number;
  poblacion_menor_15?: number;
  tasa_envejecimiento?: number;
}

export interface KPISummary {
  total_analizados: number;
  riesgo_alto: number;
  riesgo_medio: number;
  favorable: number;
  pendientes: number;
}
