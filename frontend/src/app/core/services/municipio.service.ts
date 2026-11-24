import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CentroSanitario, Convocatoria, Demografia, Health, Municipio, MunicipioDetail, Semaforo } from '../models/municipio.model';

export interface Pesos {
  w_carretera?: number;
  w_sanidad?: number;
  w_conectividad?: number;
  w_hidrico?: number;
  w_demografia?: number;
  w_demo?: number;
  w_health?: number;
  w_infra?: number;
}

export interface FiltrosMunicipios extends Pesos {
  semaforo?: Semaforo;
  min_wlc?: number;
  requiere_fibra?: boolean;
  min_fibra_pct?: number;
  con_ayuda_abierta?: boolean;
}

function queryParams(filters: object): HttpParams {
  let params = new HttpParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') {
      params = params.set(key, String(value));
    }
  }
  return params;
}

@Injectable({ providedIn: 'root' })
export class MunicipioService {
  private readonly apiUrl = '/api';

  constructor(private http: HttpClient) {}

  getMunicipios(filters: FiltrosMunicipios = {}): Observable<Municipio[]> {
    return this.http.get<Municipio[]>(`${this.apiUrl}/municipios`, { params: queryParams(filters) });
  }

  getMunicipioDetail(codigoIne: string, forceRefresh = false, pesos: Pesos = {}): Observable<MunicipioDetail> {
    return this.http.get<MunicipioDetail>(`${this.apiUrl}/municipios/${encodeURIComponent(codigoIne)}`, {
      params: queryParams({ ...pesos, force_refresh: forceRefresh })
    });
  }

  triggerMunicipioIngestion(codigoIne: string): Observable<MunicipioDetail> {
    return this.http.post<MunicipioDetail>(`${this.apiUrl}/municipios/${encodeURIComponent(codigoIne)}/ingest`, {});
  }

  getDemografia(codigoIne: string): Observable<Demografia> {
    return this.http.get<Demografia>(`${this.apiUrl}/municipios/${encodeURIComponent(codigoIne)}/demografia`);
  }

  getConvocatorias(filters: { codigo_ine?: string; categoria?: string; solo_abiertas?: boolean; abierta?: boolean } = {}): Observable<Convocatoria[]> {
    return this.http.get<Convocatoria[]>(`${this.apiUrl}/convocatorias`, { params: queryParams(filters) });
  }

  getCentrosSanitarios(filters: { solo_urgencias?: boolean; municipio_nombre?: string; force_refresh?: boolean } = {}): Observable<CentroSanitario[]> {
    return this.http.get<CentroSanitario[]>(`${this.apiUrl}/centros-sanitarios`, { params: queryParams(filters) });
  }

  healthCheck(): Observable<Health> {
    return this.http.get<Health>(`${this.apiUrl}/health`);
  }
}
